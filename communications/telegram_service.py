import requests
import logging
from django.conf import settings
from django.utils import timezone
import datetime

logger = logging.getLogger(__name__)

def send_telegram_message(chat_id, text):
    """
    Sends a styled HTML message to a Telegram chat ID.
    """
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        logger.warning(f"Skipping Telegram send: Token or Chat ID missing. (ChatID: {chat_id})")
        return False

    url = f"{settings.TELEGRAM_API_URL}sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram API Error: {str(e)}")
        return False

def format_styled_telegram_message(title, body, footer=None):
    """
    Formats a message for Telegram with consistent PropRMS styling.
    Uses HTML tags and emojis to simulate the 'styled' look of emails.
    """
    company_name = getattr(settings, 'COMPANY_NAME', 'PropRMS')
    today = timezone.localtime().strftime('%b %d, %Y')
    
    msg = f"🏢 <b>{company_name} | {title}</b>\n"
    msg += f"📅 <i>{today}</i>\n"
    msg += "─" * 20 + "\n\n"
    msg += body + "\n\n"
    msg += "─" * 20 + "\n"
    
    if footer:
        msg += f"<i>{footer}</i>\n"
    else:
        msg += f"<i>Regards,\n{company_name} Management</i>"
        
    return msg

def get_telegram_updates(offset=None):
    """
    Fetches updates (messages) sent to the bot.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return []

    url = f"{settings.TELEGRAM_API_URL}getUpdates"
    params = {'timeout': 30}
    if offset:
        params['offset'] = offset

    try:
        response = requests.get(url, params=params, timeout=35)
        response.raise_for_status()
        return response.json().get('result', [])
    except Exception as e:
        logger.error(f"Error fetching Telegram updates: {str(e)}")
        return []
