import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('AIOGRAM_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_IDS = [int(x) for x in os.getenv('AIOGRAM_ADMIN_IDS', '123456789').split(',') if x.strip()]
PAYMENT_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN', '')
DB_PATH = os.getenv('AIOGRAM_DB_PATH', 'bot_aiogram/shop.db')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')