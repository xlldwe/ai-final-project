import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('TELEBOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_IDS = [int(x) for x in os.getenv('TELEBOT_ADMIN_IDS', '123456789').split(',') if x.strip()]
PAYMENT_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN', '')
DB_PATH = os.getenv('TELEBOT_DB_PATH', 'bot_telebot/shop.db')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')