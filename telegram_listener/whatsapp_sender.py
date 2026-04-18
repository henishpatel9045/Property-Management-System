import os
import json
import time
import requests
import argparse
import qrcode
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()

WEBSITE_URL = os.getenv("WEBSITE_URL", "").rstrip("/")
SECRET = os.getenv("TELEGRAM_INTERNAL_SECRET")
SESSION_FILE = "whatsapp_session.json"

def display_qr(data):
    """Prints a QR code to the terminal."""
    qr = qrcode.QRCode(version=1, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    # Print to console using ASCII
    qr.print_ascii(invert=True)

def fetch_reminders():
    """Gets pending WhatsApp reminders from the Django backend."""
    url = f"{WEBSITE_URL}/cron-jobs/whatsapp/pending/"
    payload = {"secret": SECRET}
    
    try:
        print(f"[*] Fetching reminders from {url}...")
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get('status') == 'success':
            return data.get('reminders', [])
        else:
            print(f"[!] Server returned error: {data.get('error')}")
            return []
    except Exception as e:
        print(f"[!] Failed to fetch reminders: {str(e)}")
        return []

def run_sender(login_only=False):
    with sync_playwright() as p:
        # We need a Persistent Context to save the session
        # Ensure the 'auth' directory exists
        auth_dir = "whatsapp_auth"
        if not os.path.exists(auth_dir):
            os.makedirs(auth_dir)

        print("[*] Launching headless browser with stealth settings...")
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        
        browser = p.chromium.launch_persistent_context(
            user_data_dir=auth_dir,
            headless=True,
            user_agent=user_agent,
            viewport={'width': 1280, 'height': 800},
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu'
            ],
            ignore_https_errors=True
        )
        
        page = browser.pages[0]
        
        # Increase default timeout
        page.set_default_timeout(90000)
        
        print("[*] Navigating to WhatsApp Web...")
        try:
            page.goto("https://web.whatsapp.com", wait_until="networkidle")
        except Exception as e:
            print(f"[!] Initial navigation failed: {str(e)}")

        print(f"[*] Page Title: {page.title()}")
        print(f"[*] Current URL: {page.url}")
        print("[*] Waiting for WhatsApp Web elements to load...")
        
        try:
            # We look for search (#side) or QR code logic
            selector = 'canvas, div[data-ref], #side'
            page.wait_for_selector(selector, timeout=90000)
            
            if page.query_selector('#side'):
                print("[+] Already logged in!")
            else:
                print("[!] Login required. Extracting QR code...")
                last_qr = ""
                while True:
                    try:
                        qr_elem = page.wait_for_selector('div[data-ref]', timeout=100000)
                        qr_data = qr_elem.get_attribute('data-ref')
                        
                        if qr_data and qr_data != last_qr:
                            print("\n" + "="*40)
                            print("SCAN THIS QR CODE WITH WHATSAPP:")
                            print("="*40 + "\n")
                            display_qr(qr_data)
                            last_qr = qr_data
                    except:
                        pass
                    
                    if page.query_selector('#side'):
                        print("\n[+] Login successful!")
                        break
                    
                    time.sleep(2)
        except Exception as e:
            print(f"[!] Error during login check: {str(e)}")
            # Take a screenshot for debugging
            try:
                page.screenshot(path="error_login.png")
                print("[*] Screenshot saved to error_login.png")
            except:
                pass
            browser.close()
            return

        if login_only:
            print("[*] Login complete. Exiting...")
            browser.close()
            return

        # Fetch Reminders
        reminders = fetch_reminders()
        if not reminders:
            print("[*] No reminders to send. Exiting.")
            browser.close()
            return

        print(f"[*] Found {len(reminders)} reminders to send.")

        for rem in reminders:
            # Reformat phone for URL (remove +)
            phone = rem['phone'].replace('+', '').strip()
            message = rem['message']
            
            print(f"[*] Sending message to {phone}...")
            
            from urllib.parse import quote
            send_url = f"https://web.whatsapp.com/send?phone={phone}&text={quote(message)}"
            page.goto(send_url, wait_until="networkidle")
            
            try:
                print(f"[*] Navigated to {phone}. Waiting for population...")
                
                # Wait for the main app to be loaded generally, but don't over-rely on specific elements
                time.sleep(7) 
                
                # Press Enter to send
                page.keyboard.press("Enter")
                print(f"[+] Pressed Enter for {phone}")
                
                # Wait for the message to actually go through before closing/navigating
                time.sleep(5)
                
            except Exception as e:
                print(f"[!] Failed to send to {phone}: {str(e)}")
                try:
                    page.screenshot(path=f"error_send_{phone}.png")
                except:
                    pass

        print("[*] All tasks finished.")
        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WhatsApp Reminder Sender (Headless)")
    parser.add_argument("--login", action="store_true", help="Just perform login and exit")
    parser.add_argument("--trigger", action="store_true", help="Fetch and send reminders")
    
    args = parser.parse_args()
    
    if args.login:
        run_sender(login_only=True)
    elif args.trigger:
        run_sender(login_only=False)
    else:
        parser.print_help()
