import json
import logging
import requests
import io
from telebot import types

from bot_telebot.config import BACKEND_URL
from bot_telebot.database import (
    get_all_products, get_product, create_order,
    save_feedback, register_user, get_user_orders
)
from bot_telebot.keyboards.reply_keyboards import main_menu_keyboard, cancel_keyboard, confirm_keyboard
from bot_telebot.keyboards.inline_keyboards import (
    catalog_keyboard, product_keyboard, order_confirm_keyboard,
    cart_keyboard, cart_items_keyboard, admin_orders_keyboard, payment_keyboard
)
from bot_telebot.config import PAYMENT_TOKEN

logger = logging.getLogger(__name__)

# In-memory cart and session storage keyed by user_id
carts = {}
pending_orders = {}


def register_user_handlers(bot, admin_ids):

    def is_cancel(message):
        return message.text and message.text.strip() == '❌ Скасувати'

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        user = message.from_user
        register_user(user.id, user.username, user.first_name, user.last_name)
        logger.info(f"User /start: {user.id} @{user.username}")
        welcome = (
            f"👋 Вітаємо у <b>FashionAI Shop</b>, {user.first_name}!\n\n"
            "Ми пропонуємо найкращий одяг за доступними цінами.\n\n"
            "Оберіть розділ у меню нижче:"
        )
        bot.send_message(
            message.chat.id,
            welcome,
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )

    @bot.message_handler(commands=['help'])
    def handle_help(message):
        logger.info(f"User /help: {message.from_user.id}")
        text = (
            "📚 <b>Доступні команди:</b>\n\n"
            "/start — Головне меню\n"
            "/catalog — Переглянути каталог товарів\n"
            "/cart — Мій кошик\n"
            "/orders — Мої замовлення\n"
            "/help — Допомога\n"
            "/info — Інформація про магазин\n\n"
            "Або використовуйте кнопки меню нижче."
        )
        bot.send_message(message.chat.id, text, parse_mode='HTML')

    @bot.message_handler(commands=['info'])
    def handle_info_cmd(message):
        _send_info(message.chat.id)

    @bot.message_handler(func=lambda m: m.text == 'ℹ️ Про нас')
    def handle_info_btn(message):
        _send_info(message.chat.id)

    def _send_info(chat_id):
        text = (
            "🏪 <b>FashionAI Shop</b>\n\n"
            "Ми — сучасний онлайн-магазин одягу з AI-підтримкою.\n\n"
            "📦 <b>Доставка:</b> 2-5 робочих днів\n"
            "🚚 <b>Безкоштовна доставка</b> від 1000 UAH\n"
            "↩️ <b>Повернення:</b> 30 днів\n"
            "💳 <b>Оплата:</b> картка, PayPal, Telegram Pay\n"
            "📧 <b>Підтримка:</b> support@fashionai.shop\n"
            "🌐 <b>Сайт:</b> fashionai.shop"
        )
        from telebot import types as t
        # Use global bot instance via closure
        bot.send_message(chat_id, text, parse_mode='HTML')

    @bot.message_handler(commands=['catalog'])
    def cmd_catalog(message):
        _show_catalog(message.chat.id)

    @bot.message_handler(func=lambda m: m.text == '🛍️ Каталог')
    def handle_catalog_btn(message):
        _show_catalog(message.chat.id)

    def _show_catalog(chat_id):
        products = get_all_products()
        if not products:
            bot.send_message(chat_id, "На жаль, каталог порожній.")
            return
        bot.send_message(
            chat_id,
            "🛍️ <b>Наш каталог товарів:</b>\nОберіть товар для перегляду:",
            parse_mode='HTML',
            reply_markup=catalog_keyboard(products)
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('product_'))
    def handle_product_callback(call):
        product_id = int(call.data.split('_')[1])
        product = get_product(product_id)
        if not product:
            bot.answer_callback_query(call.id, "Товар не знайдено.")
            return
        text = (
            f"🏷️ <b>{product['name']}</b>\n\n"
            f"📂 Категорія: {product['category']}\n"
            f"📝 {product['description']}\n\n"
            f"💰 Ціна: <b>{product['price']:.2f} UAH</b>\n"
            f"📦 Залишок: {product['stock']} шт."
        )
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=product_keyboard(product_id)
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'back_catalog')
    def handle_back_catalog(call):
        products = get_all_products()
        if not products:
            bot.answer_callback_query(call.id, "Каталог порожній.")
            return
        bot.edit_message_text(
            "🛍️ <b>Наш каталог товарів:</b>\nОберіть товар для перегляду:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=catalog_keyboard(products)
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('add_to_cart_'))
    def handle_add_to_cart(call):
        product_id = int(call.data.split('_')[3])
        product = get_product(product_id)
        if not product:
            bot.answer_callback_query(call.id, "Товар не знайдено.")
            return

        user_id = call.from_user.id
        if user_id not in carts:
            carts[user_id] = {}

        pid_key = str(product_id)
        if pid_key in carts[user_id]:
            carts[user_id][pid_key]['quantity'] += 1
        else:
            carts[user_id][pid_key] = {
                'name': product['name'],
                'price': product['price'],
                'quantity': 1
            }

        qty = carts[user_id][pid_key]['quantity']
        bot.answer_callback_query(call.id, f"✅ {product['name']} додано до кошика (x{qty})")
        logger.info(f"User {user_id} added product {product_id} to cart")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('remove_cart_'))
    def handle_remove_from_cart(call):
        user_id = call.from_user.id
        pid = call.data.split('_')[2]
        cart = carts.get(user_id, {})

        if pid not in cart:
            bot.answer_callback_query(call.id, "Товар вже видалено.")
            return

        removed_name = cart[pid]['name']
        del cart[pid]

        if not cart:
            carts.pop(user_id, None)
            bot.answer_callback_query(call.id, f"❌ {removed_name} видалено.")
            bot.edit_message_text("🛒 Ваш кошик порожній.", call.message.chat.id, call.message.message_id)
            return

        lines = ["🛒 <b>Ваш кошик:</b>\n"]
        total = 0.0
        for p, item in cart.items():
            subtotal = item['price'] * item['quantity']
            total += subtotal
            lines.append(f"• {item['name']} x{item['quantity']} = {subtotal:.2f} UAH")
        lines.append(f"\n💰 <b>Разом: {total:.2f} UAH</b>")
        lines.append("\n<i>Натисніть ❌ біля товару щоб видалити його</i>")

        bot.answer_callback_query(call.id, f"❌ {removed_name} видалено.")
        bot.edit_message_text(
            "\n".join(lines),
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=cart_items_keyboard(cart)
        )

    @bot.callback_query_handler(func=lambda call: call.data == 'cancel_order')
    def handle_cancel_order(call):
        user_id = call.from_user.id
        pending_orders.pop(user_id, None)
        bot.answer_callback_query(call.id, "❌ Замовлення скасовано.")
        bot.edit_message_text(
            "❌ Замовлення скасовано.",
            call.message.chat.id,
            call.message.message_id
        )

    @bot.message_handler(func=lambda m: m.text == '📝 Відгук')
    def handle_feedback_btn(message):
        msg = bot.send_message(
            message.chat.id,
            "💬 Напишіть свій відгук про наш магазин:",
            reply_markup=cancel_keyboard()
        )
        bot.register_next_step_handler(msg, handle_feedback_text)

    def handle_feedback_text(message):
        if is_cancel(message):
            bot.send_message(message.chat.id, "Відгук скасовано.", reply_markup=main_menu_keyboard())
            return

        text = message.text.strip()
        if len(text) < 5:
            msg = bot.send_message(message.chat.id, "❗ Відгук занадто короткий. Напишіть детальніше:")
            bot.register_next_step_handler(msg, handle_feedback_text)
            return

        user = message.from_user
        save_feedback(user.id, user.username or '', text)
        bot.send_message(
            message.chat.id,
            "✅ Дякуємо за ваш відгук! Ми цінуємо вашу думку.",
            reply_markup=main_menu_keyboard()
        )

        # Notify admins
        for admin_id in admin_ids:
            try:
                bot.send_message(
                    admin_id,
                    f"💬 <b>Новий відгук від @{user.username or user.id}:</b>\n\n{text}",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Could not notify admin {admin_id}: {e}")

        logger.info(f"Feedback saved from user {user.id}")

    @bot.message_handler(commands=['cart'])
    def cmd_cart(message):
        _show_cart(message.chat.id, message.from_user.id)

    @bot.message_handler(func=lambda m: m.text == '🛒 Кошик')
    def handle_cart_btn(message):
        _show_cart(message.chat.id, message.from_user.id)

    def _show_cart(chat_id, user_id):
        cart = carts.get(user_id, {})
        if not cart:
            bot.send_message(
                chat_id,
                "🛒 Ваш кошик порожній.\n\nДодайте товари з каталогу!",
                reply_markup=main_menu_keyboard()
            )
            return

        lines = ["🛒 <b>Ваш кошик:</b>\n"]
        total = 0.0
        for pid, item in cart.items():
            subtotal = item['price'] * item['quantity']
            total += subtotal
            lines.append(f"• {item['name']} x{item['quantity']} = {subtotal:.2f} UAH")
        lines.append(f"\n💰 <b>Разом: {total:.2f} UAH</b>")
        lines.append("\n<i>Натисніть ❌ біля товару щоб видалити його</i>")

        bot.send_message(
            chat_id,
            "\n".join(lines),
            parse_mode='HTML',
            reply_markup=cart_items_keyboard(cart)
        )

    @bot.callback_query_handler(func=lambda call: call.data == 'checkout')
    def handle_checkout(call):
        user_id = call.from_user.id
        cart = carts.get(user_id, {})
        if not cart:
            bot.answer_callback_query(call.id, "Кошик порожній.")
            return

        total = sum(item['price'] * item['quantity'] for item in cart.values())
        pending_orders[user_id] = {
            'cart': dict(cart),
            'total': total,
            'is_cart': True
        }

        bot.answer_callback_query(call.id)
        msg = bot.send_message(
            call.message.chat.id,
            f"💰 Сума: {total:.2f} UAH\n\nВведіть адресу доставки:",
            reply_markup=cancel_keyboard()
        )
        bot.register_next_step_handler(msg, handle_cart_address, user_id)

    def handle_cart_address(message, user_id):
        if is_cancel(message):
            pending_orders.pop(user_id, None)
            bot.send_message(message.chat.id, "❌ Замовлення скасовано.", reply_markup=main_menu_keyboard())
            return

        address = message.text.strip()
        if len(address) < 5:
            msg = bot.send_message(message.chat.id, "❗ Адреса занадто коротка. Введіть повну адресу:")
            bot.register_next_step_handler(msg, handle_cart_address, user_id)
            return

        order_info = pending_orders.get(user_id, {})
        cart = order_info.get('cart', {})
        total = order_info.get('total', 0)
        order_info['address'] = address

        items_list = [
            {'product_id': int(pid), 'name': item['name'], 'price': item['price'], 'quantity': item['quantity']}
            for pid, item in cart.items()
        ]
        items_text = "\n".join(f"  • {i['name']} x{i['quantity']} — {i['price']*i['quantity']:.2f} UAH" for i in items_list)

        bot.send_message(
            message.chat.id,
            f"🧾 <b>Рахунок до оплати:</b>\n\n"
            f"{items_text}\n\n"
            f"📍 Адреса: {address}\n"
            f"💰 <b>До сплати: {total:.2f} UAH</b>\n\n"
            f"Оберіть спосіб оплати:",
            parse_mode='HTML',
            reply_markup=payment_keyboard(total)
        )
        logger.info(f"Payment screen shown to user {user_id}, total={total:.2f}")

    @bot.callback_query_handler(func=lambda call: call.data == 'pay_now')
    def handle_pay_now(call):
        user_id = call.from_user.id
        order_info = pending_orders.pop(user_id, {})
        cart = order_info.get('cart', carts.get(user_id, {}))
        total = order_info.get('total', 0)
        address = order_info.get('address', '')

        items_list = [
            {'product_id': int(pid), 'name': item['name'], 'price': item['price'], 'quantity': item['quantity']}
            for pid, item in cart.items()
        ]
        items_text = "\n".join(f"  • {i['name']} x{i['quantity']} — {i['price']*i['quantity']:.2f} UAH" for i in items_list)
        items_json = json.dumps(items_list)

        order_id = create_order(user_id, call.from_user.username or '', items_json, total, address)
        carts.pop(user_id, None)

        bot.answer_callback_query(call.id, "✅ Оплата прийнята!")
        bot.edit_message_text(
            f"✅ <b>Оплата успішна! Замовлення #{order_id}</b>\n\n"
            f"{items_text}\n\n"
            f"💰 Сплачено: {total:.2f} UAH\n"
            f"📍 Адреса: {address}\n\n"
            "Дякуємо за покупку! Очікуйте підтвердження.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )

        for admin_id in admin_ids:
            try:
                bot.send_message(
                    admin_id,
                    f"💰 <b>Нове оплачене замовлення #{order_id}</b>\n\n"
                    f"Користувач: @{call.from_user.username or user_id}\n"
                    f"{items_text}\n\n"
                    f"💰 Сума: {total:.2f} UAH\n"
                    f"📍 Адреса: {address}",
                    parse_mode='HTML',
                    reply_markup=admin_orders_keyboard(order_id)
                )
            except Exception as e:
                logger.warning(f"Could not notify admin: {e}")
        logger.info(f"Demo payment confirmed for order #{order_id}, user {user_id}")

    @bot.callback_query_handler(func=lambda call: call.data == 'pay_cancel')
    def handle_pay_cancel(call):
        user_id = call.from_user.id
        pending_orders.pop(user_id, None)
        bot.answer_callback_query(call.id, "❌ Оплату скасовано.")
        bot.edit_message_text(
            "❌ Оплату скасовано. Ваш кошик збережено.",
            call.message.chat.id,
            call.message.message_id
        )

    @bot.pre_checkout_query_handler(func=lambda q: True)
    def handle_pre_checkout(query):
        bot.answer_pre_checkout_query(query.id, ok=True)
        logger.info(f"Pre-checkout OK for user {query.from_user.id}")

    @bot.message_handler(content_types=['successful_payment'])
    def handle_successful_payment(message):
        user_id = message.from_user.id
        payment = message.successful_payment
        amount = payment.total_amount / 100

        order_info = pending_orders.pop(user_id, {})
        cart = order_info.get('cart', carts.get(user_id, {}))
        address = order_info.get('address', '')

        if payment.order_info and payment.order_info.shipping_address:
            addr = payment.order_info.shipping_address
            address = f"{addr.city}, {addr.street_line1}"

        items_list = [
            {'product_id': int(pid), 'name': item['name'], 'price': item['price'], 'quantity': item['quantity']}
            for pid, item in cart.items()
        ] if cart else [{'name': 'Telegram Payment', 'price': amount, 'quantity': 1}]

        items_json = json.dumps(items_list)
        order_id = create_order(user_id, message.from_user.username or '', items_json, amount, address)
        carts.pop(user_id, None)

        items_text = "\n".join(f"  • {i['name']} x{i['quantity']} — {i['price']*i['quantity']:.2f} UAH" for i in items_list)

        bot.send_message(
            message.chat.id,
            f"✅ <b>Оплата успішна! Замовлення #{order_id}</b>\n\n"
            f"{items_text}\n\n"
            f"💰 Сума: {amount:.2f} UAH\n"
            f"🔖 ID транзакції: <code>{payment.telegram_payment_charge_id}</code>\n\n"
            "Дякуємо за покупку!",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )

        for admin_id in admin_ids:
            try:
                bot.send_message(
                    admin_id,
                    f"💰 <b>Нове оплачене замовлення #{order_id}</b>\n\n"
                    f"Користувач: @{message.from_user.username or user_id}\n"
                    f"{items_text}\n\n"
                    f"💰 Сума: {amount:.2f} UAH\n"
                    f"📍 Адреса: {address}",
                    parse_mode='HTML',
                    reply_markup=admin_orders_keyboard(order_id)
                )
            except Exception as e:
                logger.warning(f"Could not notify admin {admin_id}: {e}")

        logger.info(f"Payment confirmed for order #{order_id}, user {user_id}, amount={amount:.2f}")

    @bot.callback_query_handler(func=lambda call: call.data == 'clear_cart')
    def handle_clear_cart(call):
        user_id = call.from_user.id
        carts.pop(user_id, None)
        bot.answer_callback_query(call.id, "🗑️ Кошик очищено.")
        bot.edit_message_text(
            "🗑️ Кошик очищено.",
            call.message.chat.id,
            call.message.message_id
        )

    @bot.message_handler(commands=['orders'])
    def cmd_orders(message):
        orders = get_user_orders(message.from_user.id)
        if not orders:
            bot.send_message(message.chat.id, "У вас ще немає замовлень.")
            return
        lines = ["📋 <b>Ваші замовлення:</b>\n"]
        for o in orders[:5]:
            lines.append(f"• Замовлення #{o['id']} — {o['total']:.2f} UAH — {o['status']} — {o['created_at'][:10]}")
        bot.send_message(message.chat.id, "\n".join(lines), parse_mode='HTML')

    @bot.message_handler(func=lambda m: m.text == '❓ Допомога')
    def handle_help_btn(message):
        handle_help(message)

    @bot.message_handler(func=lambda m: m.text and m.text.lower() in ['hello', 'hi', 'привіт', 'вітаю', 'хелоу'])
    def handle_hello(message):
        bot.send_message(
            message.chat.id,
            f"👋 Привіт, {message.from_user.first_name}! Чим можу допомогти?\n\nВикористовуйте меню нижче.",
            reply_markup=main_menu_keyboard()
        )

    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        bot.send_chat_action(message.chat.id, 'typing')
        try:
            # Download highest resolution photo
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded = bot.download_file(file_info.file_path)

            response = requests.post(
                f"{BACKEND_URL}/api/predict",
                files={'image': ('photo.jpg', io.BytesIO(downloaded), 'image/jpeg')},
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                top3_lines = "\n".join(
                    f"  {i+1}. {r['class_ua']} ({r['class']}) — {r['confidence_pct']}"
                    for i, r in enumerate(result['top3'])
                )
                text = (
                    f"🧠 <b>Результат класифікації CNN:</b>\n\n"
                    f"👗 Клас: <b>{result['class_ua']}</b> ({result['class']})\n"
                    f"📊 Впевненість: <b>{result['confidence_pct']}</b>\n"
                    f"⚡ Час: {result['inference_time_ms']} мс\n\n"
                    f"<b>Топ-3 варіанти:</b>\n{top3_lines}\n\n"
                    f"🛍️ Хочеш переглянути схожі товари? → /catalog"
                )
            elif response.status_code == 503:
                text = "⚠️ Нейронна мережа ще не натренована. Зверніться до адміністратора."
            else:
                text = "❌ Не вдалося класифікувати зображення. Спробуйте інше фото."

        except requests.exceptions.ConnectionError:
            text = "⚠️ Сервер недоступний. Спробуйте пізніше."
        except Exception as e:
            logger.error(f"Photo classification error: {e}")
            text = "❌ Помилка обробки фото. Надішліть чіткіше зображення одягу."

        bot.send_message(message.chat.id, text, parse_mode='HTML')

    @bot.message_handler(func=lambda m: True)
    def handle_unknown(message):
        if message.text and message.text.startswith('/'):
            bot.send_message(
                message.chat.id,
                "❓ Невідома команда. Використайте /help для списку команд.",
                reply_markup=main_menu_keyboard()
            )
        else:
            bot.send_message(
                message.chat.id,
                "Я не розумію цей запит. Скористайтесь кнопками меню або /help.",
                reply_markup=main_menu_keyboard()
            )