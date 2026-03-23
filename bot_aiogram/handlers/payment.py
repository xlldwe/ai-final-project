import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice
from aiogram.fsm.context import FSMContext

from bot_aiogram.config import PAYMENT_TOKEN, ADMIN_IDS
from bot_aiogram.database import create_order
from bot_aiogram.keyboards.inline import admin_order_keyboard

logger = logging.getLogger(__name__)
router = Router()


async def send_invoice(bot: Bot, chat_id: int, product_name: str, description: str, amount_uah: float):
    """
    Send a Telegram payment invoice.
    amount_uah is in UAH; Telegram requires the amount in minimum currency units (kopecks for UAH).
    """
    if not PAYMENT_TOKEN:
        logger.warning("PAYMENT_TOKEN is not set; cannot send invoice.")
        return False

    amount_kopecks = int(amount_uah * 100)

    prices = [LabeledPrice(label=product_name, amount=amount_kopecks)]

    await bot.send_invoice(
        chat_id=chat_id,
        title=f"Замовлення: {product_name}",
        description=description,
        payload=f"order_{chat_id}_{amount_kopecks}",
        provider_token=PAYMENT_TOKEN,
        currency="UAH",
        prices=prices,
        start_parameter="fashionai-payment",
        need_name=True,
        need_phone_number=True,
        need_shipping_address=True,
        is_flexible=False
    )
    logger.info(f"Invoice sent to {chat_id} for {product_name} ({amount_uah:.2f} UAH)")
    return True


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    """
    Telegram calls this before confirming payment.
    We must answer within 10 seconds.
    """
    logger.info(f"Pre-checkout query from user {query.from_user.id}: {query.invoice_payload}")
    # In a real scenario, verify stock availability here
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def payment_success(message: Message, state: FSMContext, bot: Bot):
    """Handle successful payment confirmation from Telegram."""
    payment = message.successful_payment
    user = message.from_user
    amount = payment.total_amount / 100

    logger.info(
        f"Successful payment from user {user.id}: "
        f"amount={amount:.2f} UAH, payload={payment.invoice_payload}"
    )

    # Get cart and order data from FSM
    data = await state.get_data()
    cart = data.get('cart', {})
    address = data.get('order_address', '')
    delivery = data.get('order_delivery', 'standard')

    # Extract shipping info from payment if available
    if payment.order_info:
        if payment.order_info.shipping_address:
            addr = payment.order_info.shipping_address
            address = f"{addr.city}, {addr.street_line1}"
        if payment.order_info.name:
            address = f"{payment.order_info.name}, {address}"

    items = [
        {'product_id': item.get('product_id'), 'name': item['name'],
         'price': item['price'], 'quantity': item['quantity']}
        for item in cart.values()
    ] if cart else [{'name': 'Telegram Payment Order', 'price': amount, 'quantity': 1}]

    items_text = "\n".join(
        f"  • {i['name']} x{i['quantity']} — {i['price'] * i['quantity']:.2f} UAH"
        for i in items
    )

    order_id = await create_order(
        user_id=user.id,
        username=user.username or '',
        items=items,
        total=amount,
        address=address,
        delivery_type=delivery
    )

    await state.clear()

    await message.answer(
        f"✅ <b>Оплата успішна! Замовлення #{order_id}</b>\n\n"
        f"{items_text}\n\n"
        f"💰 Сума: {amount:.2f} UAH\n"
        f"📍 Адреса: {address}\n"
        f"🔖 ID транзакції: <code>{payment.telegram_payment_charge_id}</code>\n\n"
        "Дякуємо за покупку! Очікуйте підтвердження."
    )

    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"💰 <b>Нове оплачене замовлення #{order_id}</b>\n\n"
                f"Користувач: @{user.username or user.id}\n"
                f"{items_text}\n\n"
                f"💰 Сума: {amount:.2f} UAH\n"
                f"📍 Адреса: {address}",
                reply_markup=admin_order_keyboard(order_id)
            )
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")