import json
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, LabeledPrice
from aiogram.fsm.context import FSMContext

from bot_aiogram.config import PAYMENT_TOKEN, ADMIN_IDS
from bot_aiogram.database import get_product, create_order
from bot_aiogram.keyboards.inline import catalog_keyboard, cart_actions_keyboard, cart_items_keyboard, order_confirm_keyboard, admin_order_keyboard
from bot_aiogram.keyboards.reply import main_menu, cancel_keyboard, delivery_type_keyboard, confirm_keyboard
from bot_aiogram.states.states import OrderStates

logger = logging.getLogger(__name__)
router = Router()


def get_cart(data: dict) -> dict:
    """Get cart from FSM data, returns dict keyed by str(product_id)."""
    return data.get('cart', {})


def set_cart(data: dict, cart: dict) -> dict:
    data['cart'] = cart
    return data


@router.message(Command('cart'))
async def cmd_cart(message: Message, state: FSMContext):
    await _show_cart(message, state)


@router.message(F.text == '🛒 Кошик')
async def btn_cart(message: Message, state: FSMContext):
    await _show_cart(message, state)


async def _show_cart(message: Message, state: FSMContext):
    data = await state.get_data()
    cart = get_cart(data)

    if not cart:
        await message.answer(
            "🛒 Ваш кошик порожній.\n\nПерегляньте наш каталог та додайте товари!"
        )
        return

    lines = ["🛒 <b>Ваш кошик:</b>\n"]
    total = 0.0
    for pid, item in cart.items():
        subtotal = item['price'] * item['quantity']
        total += subtotal
        lines.append(f"• {item['name']} x{item['quantity']} = {subtotal:.2f} UAH")
    lines.append(f"\n💰 <b>Разом: {total:.2f} UAH</b>")

    await message.answer("\n".join(lines), reply_markup=cart_items_keyboard(cart))
    logger.info(f"Cart viewed by user {message.from_user.id}, total={total:.2f}")


@router.callback_query(F.data.startswith('add_cart_'))
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split('_')[2])
    product = await get_product(product_id)
    if not product:
        await callback.answer("Товар не знайдено.", show_alert=True)
        return

    data = await state.get_data()
    cart = get_cart(data)
    pid_str = str(product_id)

    if pid_str in cart:
        cart[pid_str]['quantity'] += 1
    else:
        cart[pid_str] = {
            'product_id': product_id,
            'name': product['name'],
            'price': product['price'],
            'quantity': 1
        }

    await state.update_data(cart=cart)
    total_items = sum(item['quantity'] for item in cart.values())
    await callback.answer(
        f"✅ {product['name']} додано до кошика! (Всього товарів: {total_items})",
        show_alert=False
    )
    logger.info(f"Product {product_id} added to cart by user {callback.from_user.id}")


@router.callback_query(F.data.startswith('buy_now_'))
async def buy_now(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split('_')[2])
    product = await get_product(product_id)
    if not product:
        await callback.answer("Товар не знайдено.", show_alert=True)
        return

    # Add to cart and start checkout
    data = await state.get_data()
    cart = get_cart(data)
    pid_str = str(product_id)

    if pid_str not in cart:
        cart[pid_str] = {
            'product_id': product_id,
            'name': product['name'],
            'price': product['price'],
            'quantity': 1
        }
        await state.update_data(cart=cart)

    await callback.answer()
    await state.set_state(OrderStates.waiting_name)
    await callback.message.answer(
        "🛒 Оформлення замовлення\n\nВведіть ваше ім'я:",
        reply_markup=cancel_keyboard()
    )


@router.callback_query(F.data == 'start_checkout')
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = get_cart(data)
    if not cart:
        await callback.answer("Кошик порожній.", show_alert=True)
        return

    await callback.answer()
    await state.set_state(OrderStates.waiting_name)
    await callback.message.answer(
        "🛒 Оформлення замовлення\n\nВведіть ваше ім'я:",
        reply_markup=cancel_keyboard()
    )


@router.message(OrderStates.waiting_name)
async def process_order_name(message: Message, state: FSMContext):
    if message.text == '❌ Скасувати':
        await state.set_state(None)
        await message.answer("❌ Замовлення скасовано.", reply_markup=main_menu())
        return

    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❗ Ім'я занадто коротке. Введіть ще раз:")
        return

    await state.update_data(order_name=name)
    await state.set_state(OrderStates.waiting_phone)
    await message.answer(f"Ім'я: <b>{name}</b>\n\nВведіть ваш номер телефону:")


@router.message(OrderStates.waiting_phone)
async def process_order_phone(message: Message, state: FSMContext):
    if message.text == '❌ Скасувати':
        await state.set_state(None)
        await message.answer("❌ Замовлення скасовано.", reply_markup=main_menu())
        return

    phone = message.text.strip()
    # Basic phone validation
    digits = ''.join(filter(str.isdigit, phone))
    if len(digits) < 9:
        await message.answer("❗ Невірний номер телефону. Введіть ще раз (наприклад: +380501234567):")
        return

    await state.update_data(order_phone=phone)
    await state.set_state(OrderStates.waiting_address)
    await message.answer(f"Телефон: <b>{phone}</b>\n\nВведіть адресу доставки:")


@router.message(OrderStates.waiting_address)
async def process_order_address(message: Message, state: FSMContext):
    if message.text == '❌ Скасувати':
        await state.set_state(None)
        await message.answer("❌ Замовлення скасовано.", reply_markup=main_menu())
        return

    address = message.text.strip()
    if len(address) < 10:
        await message.answer("❗ Адреса занадто коротка. Введіть повну адресу (місто, вулиця, будинок):")
        return

    await state.update_data(order_address=address)
    await state.set_state(OrderStates.waiting_delivery_type)
    await message.answer(
        "Оберіть тип доставки:",
        reply_markup=delivery_type_keyboard()
    )


@router.message(OrderStates.waiting_delivery_type)
async def process_delivery_type(message: Message, state: FSMContext):
    if message.text == '❌ Скасувати':
        await state.set_state(None)
        await message.answer("❌ Замовлення скасовано.", reply_markup=main_menu())
        return

    if message.text == '🚚 Стандартна доставка':
        delivery = 'standard'
        delivery_label = 'Стандартна (2-5 днів)'
    elif message.text == '⚡ Експрес доставка':
        delivery = 'express'
        delivery_label = 'Експрес (1-2 дні)'
    else:
        await message.answer("Оберіть тип доставки за допомогою кнопок:")
        return

    data = await state.get_data()
    cart = get_cart(data)
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    if delivery == 'express':
        total += 150  # Express surcharge

    await state.update_data(order_delivery=delivery, order_total=total)

    # Build order summary
    lines = ["📋 <b>Підтвердіть замовлення:</b>\n"]
    for item in cart.values():
        lines.append(f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']:.2f} UAH")
    lines.append(f"\n👤 Ім'я: {data.get('order_name', '')}")
    lines.append(f"📱 Телефон: {data.get('order_phone', '')}")
    lines.append(f"📍 Адреса: {data.get('order_address', '')}")
    lines.append(f"🚚 Доставка: {delivery_label}")
    if delivery == 'express':
        lines.append("   (+150 UAH за експрес)")
    lines.append(f"\n💰 <b>Разом: {total:.2f} UAH</b>")

    await state.set_state(OrderStates.confirming_order)
    await message.answer(
        "\n".join(lines),
        reply_markup=confirm_keyboard()
    )


@router.message(OrderStates.confirming_order)
async def process_order_confirm(message: Message, state: FSMContext, bot: Bot):
    if message.text == '❌ Скасувати':
        await state.set_state(None)
        await message.answer("❌ Замовлення скасовано.", reply_markup=main_menu())
        return

    if message.text != '✅ Підтвердити':
        await message.answer("Натисніть '✅ Підтвердити' або '❌ Скасувати':")
        return

    data = await state.get_data()
    cart = get_cart(data)
    total = data.get('order_total', sum(i['price'] * i['quantity'] for i in cart.values()))

    items_description = ", ".join(
        f"{item['name']} x{item['quantity']}" for item in cart.values()
    )

    delivery = data.get('order_delivery', 'standard')
    address = data.get('order_address', '')
    user = message.from_user

    items = [
        {'product_id': item.get('product_id'), 'name': item['name'],
         'price': item['price'], 'quantity': item['quantity']}
        for item in cart.values()
    ]
    items_text = "\n".join(f"  • {i['name']} x{i['quantity']} — {i['price']*i['quantity']:.2f} UAH" for i in items)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    pay_kb = InlineKeyboardBuilder()
    pay_kb.button(text=f'💳 Оплатити {total:.2f} UAH', callback_data='pay_confirm')
    pay_kb.button(text='❌ Скасувати', callback_data='pay_cancel')
    pay_kb.adjust(1)

    await state.update_data(pending_items=items, pending_total=total, pending_address=address, pending_delivery=delivery)
    await message.answer(
        f"🧾 <b>Рахунок до оплати:</b>\n\n"
        f"{items_text}\n\n"
        f"📍 Адреса: {address}\n"
        f"🚚 Доставка: {'Експрес (+150 UAH)' if delivery == 'express' else 'Стандартна'}\n"
        f"💰 <b>До сплати: {total:.2f} UAH</b>",
        reply_markup=pay_kb.as_markup()
    )
    logger.info(f"Payment screen shown to user {user.id}, total={total:.2f}")


@router.callback_query(F.data == 'pay_confirm')
async def handle_pay_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    items = data.get('pending_items', [])
    total = data.get('pending_total', 0)
    address = data.get('pending_address', '')
    delivery = data.get('pending_delivery', 'standard')
    user = callback.from_user

    items_text = "\n".join(f"  • {i['name']} x{i['quantity']} — {i['price']*i['quantity']:.2f} UAH" for i in items)
    order_id = await create_order(user.id, user.username or '', items, total, address, delivery)
    await state.clear()

    await callback.answer("✅ Оплата прийнята!")
    await callback.message.edit_text(
        f"✅ <b>Оплата успішна! Замовлення #{order_id}</b>\n\n"
        f"{items_text}\n\n"
        f"💰 Сплачено: {total:.2f} UAH\n"
        f"📍 Адреса: {address}\n\n"
        "Дякуємо за покупку! Очікуйте підтвердження."
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"💰 <b>Нове оплачене замовлення #{order_id}</b>\n\n"
                f"Користувач: @{user.username or user.id}\n"
                f"{items_text}\n\n"
                f"💰 Сума: {total:.2f} UAH\n📍 Адреса: {address}",
                reply_markup=admin_order_keyboard(order_id)
            )
        except Exception as e:
            logger.warning(f"Could not notify admin: {e}")
    logger.info(f"Demo payment confirmed for order #{order_id}, user {user.id}")


@router.callback_query(F.data == 'pay_cancel')
async def handle_pay_cancel(callback: CallbackQuery, state: FSMContext):
    await state.update_data(pending_items=None, pending_total=None)
    await callback.answer("❌ Оплату скасовано.")
    await callback.message.edit_text("❌ Оплату скасовано. Ваш кошик збережено.")


@router.callback_query(F.data == 'clear_cart')
async def clear_cart(callback: CallbackQuery, state: FSMContext):
    await state.update_data(cart={})
    await callback.answer("🗑️ Кошик очищено.")
    await callback.message.edit_text("🗑️ Кошик очищено.")
    logger.info(f"Cart cleared by user {callback.from_user.id}")


@router.callback_query(F.data.startswith('remove_item_'))
async def remove_item_from_cart(callback: CallbackQuery, state: FSMContext):
    pid = callback.data.split('_')[2]
    data = await state.get_data()
    cart = get_cart(data)

    if pid not in cart:
        await callback.answer("Товар вже видалено.", show_alert=True)
        return

    removed_name = cart[pid]['name']
    del cart[pid]
    await state.update_data(cart=cart)

    if not cart:
        await callback.answer(f"❌ {removed_name} видалено. Кошик порожній.")
        await callback.message.edit_text("🛒 Ваш кошик порожній.")
        return

    lines = ["🛒 <b>Ваш кошик:</b>\n"]
    total = 0.0
    for item in cart.values():
        subtotal = item['price'] * item['quantity']
        total += subtotal
        lines.append(f"• {item['name']} x{item['quantity']} = {subtotal:.2f} UAH")
    lines.append(f"\n💰 <b>Разом: {total:.2f} UAH</b>")

    await callback.answer(f"❌ {removed_name} видалено.")
    await callback.message.edit_text("\n".join(lines), reply_markup=cart_items_keyboard(cart))