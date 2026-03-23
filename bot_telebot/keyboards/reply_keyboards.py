import telebot
from telebot import types


def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('🛍️ Каталог'),
        types.KeyboardButton('ℹ️ Про нас'),
        types.KeyboardButton('❓ Допомога'),
        types.KeyboardButton('📝 Відгук'),
        types.KeyboardButton('🛒 Кошик'),
    )
    return markup


def admin_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('➕ Додати товар'),
        types.KeyboardButton('❌ Видалити товар'),
        types.KeyboardButton('📋 Замовлення'),
        types.KeyboardButton('📊 Відгуки'),
        types.KeyboardButton('🔙 Головне меню'),
    )
    return markup


def cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton('❌ Скасувати'))
    return markup


def confirm_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('✅ Підтвердити'),
        types.KeyboardButton('❌ Скасувати'),
    )
    return markup
