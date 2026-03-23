import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot_aiogram.database import get_all_products, get_product
from bot_aiogram.keyboards.inline import catalog_keyboard, product_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command('catalog'))
async def cmd_catalog(message: Message):
    await _show_catalog(message)


@router.message(F.text == '🛍️ Каталог')
async def btn_catalog(message: Message):
    await _show_catalog(message)


async def _show_catalog(message: Message):
    products = await get_all_products()
    if not products:
        await message.answer("На жаль, каталог порожній.")
        return
    logger.info(f"Catalog viewed by user {message.from_user.id}")
    await message.answer(
        "🛍️ <b>Наш каталог товарів:</b>\n\nОберіть товар для перегляду:",
        reply_markup=catalog_keyboard(products)
    )


@router.callback_query(F.data.startswith('product_'))
async def show_product(callback: CallbackQuery):
    product_id = int(callback.data.split('_')[1])
    product = await get_product(product_id)
    if not product:
        await callback.answer("Товар не знайдено.", show_alert=True)
        return

    text = (
        f"🏷️ <b>{product['name']}</b>\n\n"
        f"📂 Категорія: {product['category']}\n"
        f"📝 {product['description']}\n\n"
        f"💰 Ціна: <b>{product['price']:.2f} UAH</b>\n"
        f"📦 Наявність: {product['stock']} шт."
    )

    await callback.message.edit_text(
        text,
        reply_markup=product_keyboard(product_id)
    )
    await callback.answer()
    logger.info(f"Product {product_id} viewed by user {callback.from_user.id}")


@router.callback_query(F.data == 'back_catalog')
async def back_to_catalog(callback: CallbackQuery):
    products = await get_all_products()
    if not products:
        await callback.answer("Каталог порожній.", show_alert=True)
        return
    await callback.message.edit_text(
        "🛍️ <b>Наш каталог товарів:</b>\n\nОберіть товар для перегляду:",
        reply_markup=catalog_keyboard(products)
    )
    await callback.answer()