from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🛍️ Каталог'), KeyboardButton(text='🛒 Кошик')],
            [KeyboardButton(text='ℹ️ Про нас'), KeyboardButton(text='❓ Допомога')],
            [KeyboardButton(text='📝 Відгук'), KeyboardButton(text='📋 Мої замовлення')],
        ],
        resize_keyboard=True
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='➕ Додати товар'), KeyboardButton(text='❌ Видалити товар')],
            [KeyboardButton(text='📋 Замовлення'), KeyboardButton(text='📊 Відгуки')],
            [KeyboardButton(text='🔙 Головне меню')],
        ],
        resize_keyboard=True
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='❌ Скасувати')]],
        resize_keyboard=True
    )


def delivery_type_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🚚 Стандартна доставка'), KeyboardButton(text='⚡ Експрес доставка')],
            [KeyboardButton(text='❌ Скасувати')],
        ],
        resize_keyboard=True
    )


def confirm_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='✅ Підтвердити'), KeyboardButton(text='❌ Скасувати')],
        ],
        resize_keyboard=True
    )