import json
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def catalog_keyboard(products) -> InlineKeyboardMarkup:
    """One button per product."""
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=f"{product['name']} — {product['price']:.2f} UAH",
            callback_data=f"product_{product['id']}"
        )
    builder.adjust(1)
    return builder.as_markup()


def product_keyboard(product_id) -> InlineKeyboardMarkup:
    """Order button + Back button."""
    builder = InlineKeyboardBuilder()
    builder.button(text='🛒 Додати до кошика', callback_data=f"add_cart_{product_id}")
    builder.button(text='💳 Купити зараз', callback_data=f"buy_now_{product_id}")
    builder.button(text='⬅️ Каталог', callback_data='back_catalog')
    builder.adjust(2, 1)
    return builder.as_markup()


def order_confirm_keyboard(cart_json) -> InlineKeyboardMarkup:
    """Confirm and Cancel buttons for order."""
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Підтвердити замовлення', callback_data='confirm_checkout')
    builder.button(text='❌ Скасувати', callback_data='cancel_checkout')
    builder.adjust(1)
    return builder.as_markup()


def payment_keyboard(amount) -> InlineKeyboardMarkup:
    """Pay button."""
    builder = InlineKeyboardBuilder()
    builder.button(text=f'💳 Оплатити {amount:.2f} UAH', callback_data=f'pay_{int(amount * 100)}')
    builder.adjust(1)
    return builder.as_markup()


def admin_order_keyboard(order_id) -> InlineKeyboardMarkup:
    """Approve and Reject buttons for admin."""
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Підтвердити', callback_data=f'approve_order_{order_id}')
    builder.button(text='❌ Відхилити', callback_data=f'reject_order_{order_id}')
    builder.adjust(2)
    return builder.as_markup()


def remove_product_keyboard(products) -> InlineKeyboardMarkup:
    """List products for removal."""
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=f"❌ {product['name']}",
            callback_data=f"admin_remove_{product['id']}"
        )
    builder.button(text='🔙 Назад', callback_data='admin_back')
    builder.adjust(1)
    return builder.as_markup()


def cart_actions_keyboard() -> InlineKeyboardMarkup:
    """Cart management buttons."""
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Оформити замовлення', callback_data='start_checkout')
    builder.button(text='🗑️ Очистити кошик', callback_data='clear_cart')
    builder.adjust(1)
    return builder.as_markup()


def cart_items_keyboard(cart: dict) -> InlineKeyboardMarkup:
    """Cart with individual remove buttons per item."""
    builder = InlineKeyboardBuilder()
    for pid, item in cart.items():
        builder.button(
            text=f"❌ {item['name']} x{item['quantity']}",
            callback_data=f"remove_item_{pid}"
        )
    builder.button(text='✅ Оформити замовлення', callback_data='start_checkout')
    builder.button(text='🗑️ Очистити кошик', callback_data='clear_cart')
    builder.adjust(1)
    return builder.as_markup()