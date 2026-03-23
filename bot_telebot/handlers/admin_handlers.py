import logging
from telebot import types

from bot_telebot.database import (
    get_all_products, get_product, add_product, remove_product,
    get_all_orders, get_all_feedback, get_order, update_order_status
)
from bot_telebot.keyboards.reply_keyboards import admin_menu_keyboard, main_menu_keyboard, cancel_keyboard
from bot_telebot.keyboards.inline_keyboards import remove_product_keyboard, admin_orders_keyboard

logger = logging.getLogger(__name__)

# Temporary storage for admin add-item FSM
admin_states = {}


def register_admin_handlers(bot, admin_ids):

    def is_admin(user_id):
        return user_id in admin_ids

    def require_admin(message):
        if not is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "⛔ Доступ заборонено.")
            return False
        return True

    def is_cancel(message):
        return message.text and message.text.strip() == '❌ Скасувати'

    @bot.message_handler(commands=['admin'])
    def handle_admin(message):
        if not require_admin(message):
            return
        logger.info(f"Admin panel accessed by {message.from_user.id}")
        bot.send_message(
            message.chat.id,
            "🔐 <b>Панель адміністратора</b>\n\nВиберіть дію:",
            parse_mode='HTML',
            reply_markup=admin_menu_keyboard()
        )

    @bot.message_handler(func=lambda m: m.text == '➕ Додати товар')
    def handle_add_item_btn(message):
        if not require_admin(message):
            return
        admin_states[message.from_user.id] = {}
        msg = bot.send_message(
            message.chat.id,
            "➕ <b>Додавання нового товару</b>\n\nВведіть назву товару:",
            parse_mode='HTML',
            reply_markup=cancel_keyboard()
        )
        bot.register_next_step_handler(msg, handle_add_item_name)

    def handle_add_item_name(message):
        if not is_admin(message.from_user.id):
            return
        if is_cancel(message):
            admin_states.pop(message.from_user.id, None)
            bot.send_message(message.chat.id, "❌ Скасовано.", reply_markup=admin_menu_keyboard())
            return

        name = message.text.strip()
        if len(name) < 2:
            msg = bot.send_message(message.chat.id, "❗ Назва занадто коротка. Введіть ще раз:")
            bot.register_next_step_handler(msg, handle_add_item_name)
            return

        admin_states[message.from_user.id]['name'] = name
        msg = bot.send_message(
            message.chat.id,
            f"Назва: <b>{name}</b>\n\nВведіть опис товару:",
            parse_mode='HTML',
            reply_markup=cancel_keyboard()
        )
        bot.register_next_step_handler(msg, handle_add_item_desc)

    def handle_add_item_desc(message):
        if not is_admin(message.from_user.id):
            return
        if is_cancel(message):
            admin_states.pop(message.from_user.id, None)
            bot.send_message(message.chat.id, "❌ Скасовано.", reply_markup=admin_menu_keyboard())
            return

        description = message.text.strip()
        admin_states[message.from_user.id]['description'] = description
        msg = bot.send_message(
            message.chat.id,
            "Введіть ціну товару (числом, наприклад: 599.99):",
            reply_markup=cancel_keyboard()
        )
        bot.register_next_step_handler(msg, handle_add_item_price)

    def handle_add_item_price(message):
        if not is_admin(message.from_user.id):
            return
        if is_cancel(message):
            admin_states.pop(message.from_user.id, None)
            bot.send_message(message.chat.id, "❌ Скасовано.", reply_markup=admin_menu_keyboard())
            return

        try:
            price = float(message.text.strip().replace(',', '.'))
            if price <= 0:
                raise ValueError("Price must be positive")
        except ValueError:
            msg = bot.send_message(
                message.chat.id,
                "❗ Невірна ціна. Введіть число (наприклад: 599.99):"
            )
            bot.register_next_step_handler(msg, handle_add_item_price)
            return

        admin_states[message.from_user.id]['price'] = price
        msg = bot.send_message(
            message.chat.id,
            "Введіть категорію товару (наприклад: T-Shirts, Jeans, Dresses, Jackets, Shoes, Sweaters, Pants, Shirts):",
            reply_markup=cancel_keyboard()
        )
        bot.register_next_step_handler(msg, handle_add_item_category)

    def handle_add_item_category(message):
        if not is_admin(message.from_user.id):
            return
        if is_cancel(message):
            admin_states.pop(message.from_user.id, None)
            bot.send_message(message.chat.id, "❌ Скасовано.", reply_markup=admin_menu_keyboard())
            return

        category = message.text.strip()
        state = admin_states.pop(message.from_user.id, {})
        state['category'] = category

        product_id = add_product(
            state.get('name', ''),
            state.get('description', ''),
            state.get('price', 0),
            category
        )

        bot.send_message(
            message.chat.id,
            f"✅ <b>Товар додано успішно!</b>\n\n"
            f"ID: {product_id}\n"
            f"Назва: {state.get('name')}\n"
            f"Ціна: {state.get('price'):.2f} UAH\n"
            f"Категорія: {category}",
            parse_mode='HTML',
            reply_markup=admin_menu_keyboard()
        )
        logger.info(f"Product added by admin {message.from_user.id}: {state.get('name')} id={product_id}")

    @bot.message_handler(func=lambda m: m.text == '❌ Видалити товар')
    def handle_remove_item_btn(message):
        if not require_admin(message):
            return
        products = get_all_products()
        if not products:
            bot.send_message(message.chat.id, "Каталог порожній.", reply_markup=admin_menu_keyboard())
            return
        bot.send_message(
            message.chat.id,
            "❌ <b>Виберіть товар для видалення:</b>",
            parse_mode='HTML',
            reply_markup=remove_product_keyboard(products)
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('remove_product_'))
    def handle_remove_item_callback(call):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔ Доступ заборонено.")
            return

        product_id = int(call.data.split('_')[2])
        product = get_product(product_id)
        if not product:
            bot.answer_callback_query(call.id, "Товар не знайдено.")
            return

        success = remove_product(product_id)
        if success:
            bot.answer_callback_query(call.id, f"✅ Товар '{product['name']}' видалено.")
            bot.edit_message_text(
                f"✅ Товар <b>{product['name']}</b> видалено з каталогу.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML'
            )
            logger.info(f"Product {product_id} removed by admin {call.from_user.id}")
        else:
            bot.answer_callback_query(call.id, "❗ Помилка при видаленні.")

    @bot.callback_query_handler(func=lambda call: call.data == 'back_admin')
    def handle_back_admin(call):
        if not is_admin(call.from_user.id):
            return
        bot.edit_message_text(
            "Повернення до адмін-панелі.",
            call.message.chat.id,
            call.message.message_id
        )

    @bot.message_handler(func=lambda m: m.text == '📋 Замовлення')
    def handle_orders_btn(message):
        if not require_admin(message):
            return
        orders = get_all_orders()
        if not orders:
            bot.send_message(message.chat.id, "Замовлень поки немає.", reply_markup=admin_menu_keyboard())
            return

        lines = ["📋 <b>Всі замовлення:</b>\n"]
        for o in orders[:10]:
            lines.append(
                f"• #{o['id']} | @{o['username'] or o['user_id']} | {o['total']:.2f} UAH | {o['status']} | {o['created_at'][:10]}"
            )
        if len(orders) > 10:
            lines.append(f"\n...та ще {len(orders) - 10} замовлень.")

        bot.send_message(message.chat.id, "\n".join(lines), parse_mode='HTML', reply_markup=admin_menu_keyboard())
        logger.info(f"Orders list viewed by admin {message.from_user.id}")

    @bot.message_handler(func=lambda m: m.text == '📊 Відгуки')
    def handle_reviews_btn(message):
        if not require_admin(message):
            return
        feedbacks = get_all_feedback()
        if not feedbacks:
            bot.send_message(message.chat.id, "Відгуків поки немає.", reply_markup=admin_menu_keyboard())
            return

        lines = ["📊 <b>Відгуки клієнтів:</b>\n"]
        for f in feedbacks[:10]:
            lines.append(f"• @{f['username'] or f['user_id']} ({f['created_at'][:10]}):\n  {f['text'][:100]}\n")
        if len(feedbacks) > 10:
            lines.append(f"...та ще {len(feedbacks) - 10} відгуків.")

        bot.send_message(message.chat.id, "\n".join(lines), parse_mode='HTML', reply_markup=admin_menu_keyboard())
        logger.info(f"Feedback list viewed by admin {message.from_user.id}")

    @bot.message_handler(func=lambda m: m.text == '🔙 Головне меню')
    def handle_main_menu_btn(message):
        bot.send_message(
            message.chat.id,
            "🏠 Головне меню",
            reply_markup=main_menu_keyboard()
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('process_order_'))
    def handle_process_order(call):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔ Доступ заборонено.")
            return
        order_id = int(call.data.split('_')[2])
        update_order_status(order_id, 'processing')
        order = get_order(order_id)
        bot.answer_callback_query(call.id, f"✅ Замовлення #{order_id} оброблено.")
        bot.edit_message_text(
            f"✅ Замовлення #{order_id} позначено як оброблене.",
            call.message.chat.id,
            call.message.message_id
        )
        if order:
            try:
                bot.send_message(
                    order['user_id'],
                    f"🔄 <b>Ваше замовлення #{order_id} обробляється!</b>\n\n"
                    f"Менеджер прийняв замовлення і готує його до відправки.\n"
                    f"Очікуйте повідомлення про відправку.",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Could not notify user about order {order_id}: {e}")
        logger.info(f"Order {order_id} processed by admin {call.from_user.id}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_admin_order_'))
    def handle_cancel_admin_order(call):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔ Доступ заборонено.")
            return
        order_id = int(call.data.split('_')[3])
        update_order_status(order_id, 'cancelled')
        order = get_order(order_id)
        bot.answer_callback_query(call.id, f"❌ Замовлення #{order_id} скасовано.")
        bot.edit_message_text(
            f"❌ Замовлення #{order_id} скасовано адміністратором.",
            call.message.chat.id,
            call.message.message_id
        )
        if order:
            try:
                bot.send_message(
                    order['user_id'],
                    f"❌ <b>Замовлення #{order_id} скасовано.</b>\n\n"
                    f"На жаль, ваше замовлення було скасовано адміністратором.\n"
                    f"Якщо це помилка — зверніться до підтримки.",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Could not notify user about order {order_id}: {e}")
        logger.info(f"Order {order_id} cancelled by admin {call.from_user.id}")