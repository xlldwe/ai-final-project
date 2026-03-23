from telebot import types


def catalog_keyboard(products):
    """Creates inline keyboard with all products as buttons."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for product in products:
        btn = types.InlineKeyboardButton(
            text=f"{product['name']} - {product['price']:.2f} UAH",
            callback_data=f"product_{product['id']}"
        )
        markup.add(btn)
    return markup


def product_keyboard(product_id):
    """Add to cart + Back to catalog buttons."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(
            text='➕ До кошика',
            callback_data=f"add_to_cart_{product_id}"
        ),
        types.InlineKeyboardButton(
            text='⬅️ Каталог',
            callback_data='back_catalog'
        )
    )
    return markup


def order_confirm_keyboard(product_id):
    """Confirm Order and Cancel buttons."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(
            text='✅ Підтвердити',
            callback_data=f"confirm_order_{product_id}"
        ),
        types.InlineKeyboardButton(
            text='❌ Скасувати',
            callback_data='cancel_order'
        )
    )
    return markup


def payment_keyboard(total):
    """Pay Now button."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            text=f'💳 Оплатити {total:.2f} UAH',
            callback_data='pay_now'
        ),
        types.InlineKeyboardButton(
            text='❌ Скасувати',
            callback_data='pay_cancel'
        )
    )
    return markup


def admin_orders_keyboard(order_id):
    """Process and Cancel Order buttons for admin."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(
            text='✅ Обробити',
            callback_data=f"process_order_{order_id}"
        ),
        types.InlineKeyboardButton(
            text='❌ Скасувати',
            callback_data=f"cancel_admin_order_{order_id}"
        )
    )
    return markup


def remove_product_keyboard(products):
    """Inline keyboard listing products for removal."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for product in products:
        btn = types.InlineKeyboardButton(
            text=f"❌ {product['name']}",
            callback_data=f"remove_product_{product['id']}"
        )
        markup.add(btn)
    markup.add(
        types.InlineKeyboardButton(text='🔙 Назад', callback_data='back_admin')
    )
    return markup


def cart_keyboard():
    """Cart actions keyboard."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(text='✅ Оформити замовлення', callback_data='checkout'),
        types.InlineKeyboardButton(text='🗑️ Очистити кошик', callback_data='clear_cart')
    )
    return markup


def cart_items_keyboard(cart):
    """Cart with individual remove buttons per item."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for pid, item in cart.items():
        markup.add(types.InlineKeyboardButton(
            text=f"❌ {item['name']} x{item['quantity']}",
            callback_data=f"remove_cart_{pid}"
        ))
    markup.add(
        types.InlineKeyboardButton(text='✅ Оформити замовлення', callback_data='checkout'),
        types.InlineKeyboardButton(text='🗑️ Очистити кошик', callback_data='clear_cart')
    )
    return markup