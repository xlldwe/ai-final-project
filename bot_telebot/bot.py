import telebot
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot_telebot.config import BOT_TOKEN, ADMIN_IDS
from bot_telebot.database import init_db
from bot_telebot.handlers.user_handlers import register_user_handlers
from bot_telebot.handlers.admin_handlers import register_admin_handlers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_telebot/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
init_db()

register_admin_handlers(bot, ADMIN_IDS)
register_user_handlers(bot, ADMIN_IDS)

if __name__ == '__main__':
    logger.info("Starting FashionAI TelebotAPI bot...")
    bot.infinity_polling(logger_level=logging.INFO)