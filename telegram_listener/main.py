import os
import json
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_INTERNAL_SECRET = os.getenv("TELEGRAM_INTERNAL_SECRET")
WEBSITE_URL = os.getenv("WEBSITE_URL", "").rstrip("/")

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    logger.info(f"User {user.first_name} ({chat_id}) started the bot.")
    
    # Create a button for sharing contact
    contact_button = KeyboardButton(text="📱 Share Contact Details", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
    
    welcome_text = (
        f"Hi <b>{user.first_name}</b>, welcome to <b>PropRMS Reminders</b>!\n\n"
        "To receive rent reminders here, we need to link your Telegram account to our system.\n"
        "Please click the button below to share your contact details."
    )
    
    await update.message.reply_html(welcome_text, reply_markup=reply_markup)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles shared contacts."""
    contact = update.message.contact
    chat_id = update.effective_chat.id
    
    if not contact:
        return

    # User shared their contact
    phone_number = contact.phone_number
    logger.info(f"Received contact from chat_id {chat_id}: {phone_number}")

    # Synchronize with main Django app
    registration_url = f"{WEBSITE_URL}/cron-jobs/telegram/register/"
    payload = {
        "chat_id": str(chat_id),
        "phone_number": phone_number,
        "secret": TELEGRAM_INTERNAL_SECRET
    }

    try:
        response = requests.post(registration_url, json=payload, timeout=15)
        response_data = response.json()
        
        if response.status_code == 200:
            # Registration successful - Django side likely already sent a confirmation
            logger.info(f"Successfully registered user {phone_number}")
        elif response.status_code == 404:
            await update.message.reply_text(
                "I'm sorry, I couldn't find a tenant record with that phone number in our system. "
                "Please contact your property manager to ensure your phone number is correct."
            )
        else:
            logger.error(f"Failed to register user. Status: {response.status_code}, Body: {response.text}")
            await update.message.reply_text("An error occurred during registration. Please try again later.")
            
    except Exception as e:
        logger.error(f"Error communicating with Django app: {str(e)}")
        await update.message.reply_text("Could not connect to the registration server. Please try again later.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles any other messages."""
    await update.message.reply_text(
        "I'm currently only configured to handle registration. "
        "If you want to register for rent reminders, please use the /start command."
    )

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_INTERNAL_SECRET or not WEBSITE_URL:
        logger.error("Missing environment variables. Check your .env file.")
        exit(1)

    # Build the application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), unknown))
    
    logger.info("Bot listener started...")
    application.run_polling()
