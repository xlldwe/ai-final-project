import asyncio
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from bot_aiogram.config import BOT_TOKEN
from bot_aiogram.database import init_db
from bot_aiogram.middlewares.logging_middleware import LoggingMiddleware
from bot_aiogram.handlers import user, catalog, cart, payment, admin, photo


async def main():
    os.makedirs('bot_aiogram', exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot_aiogram/bot.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    await init_db()

    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    # Admin router must be first so admin-specific handlers take priority
    dp.include_router(admin.router)
    dp.include_router(user.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(payment.router)
    dp.include_router(photo.router)

    logger.info("Starting FashionAI Aiogram bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())