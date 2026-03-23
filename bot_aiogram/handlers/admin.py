import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot_aiogram.config import ADMIN_IDS
from bot_aiogram.database import (
    get_all_products, get_product, add_product, remove_product,
    get_all_orders, get_all_feedback, update_order_status, save_feedback
)
from bot_aiogram.keyboards.reply import admin_menu, main_menu, cancel_keyboard
from bot_aiogram.keyboards.inline import remove_product_keyboard, admin_order_keyboard
from bot_aiogram.states.states import AdminAddItem, AdminRemoveItem

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command('admin'))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас немає прав адміністратора.")
        return
    await state.clear()
    logger.info(f"Admin panel opened by {message.from_user.id}")
    await message.answer(
        "🔐 <b>Панель адміністратора FashionAI Shop</b>\n\nВиберіть дію:",
        reply_markup=admin_menu()
    )


@router.message(F.text == '🔙 Головне меню')
async def btn_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Головне меню", reply_markup=main_menu())


# ─── Add Product ────────────────────────────────────────────────────────────

@router.message(F.text == '➕ Додати товар')
async def btn_add_item(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ заборонено.")
        return
    await state.set_state(AdminAddItem.waiting_name)
    await message.answer(
        "➕ <b>Додавання нового товару</b>\n\nВведіть назву товару:",
        reply_markup=cancel_keyboard()
    )


@router.message(AdminAddItem.waiting_name)
async def admin_add_name(message: Message, state: FSMContext):
    if message.text == '❌ Скасувати':
        await state.clear()
        await message.answer("❌ Скасовано.", reply_markup=admin_menu())
        return

    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❗ Назва занадто коротка. Введіть ще раз:")
        return

    await state.update_data(item_name=name)
    await state.set_state(AdminAddItem.waiting_description)
    await message.answer(f"Назва: <b>{name}</b>\n\nВведіть опис товару:")


@router.message(AdminAddItem.waiting_description)
async def admin_add_description(message: Message, state: FSMContext):
    if message.text == '❌ Скасувати':
        await state.clear()
        await message.answer("❌ Скасовано.", reply_markup=admin_menu())
        return

    description = message.text.strip()
    await state.update_data(item_description=description)
    await state.set_state(AdminAddItem.waiting_price)
    await message.answer("Введіть ціну товару (числом, наприклад: 599.99):")


@router.message(AdminAddItem.waiting_price)
async def admin_add_price(message: Message, state: FSMContext):
    if message.text == '❌ Скасувати':
        await state.clear()
        await message.answer("❌ Скасовано.", reply_markup=admin_menu())
        return

    try:
        price = float(message.text.strip().replace(',', '.'))
        if price <= 0:
            raise ValueError("Price must be positive")
    except ValueError:
        await message.answer("❗ Невірна ціна. Введіть число більше 0 (наприклад: 599.99):")
        return

    await state.update_data(item_price=price)
    await state.set_state(AdminAddItem.waiting_category)
    await message.answer(
        "Введіть категорію товару:\n"
        "(T-Shirts, Jeans, Dresses, Jackets, Shoes, Sweaters, Pants, Shirts)"
    )


@router.message(AdminAddItem.waiting_category)
async def admin_add_category(message: Message, state: FSMContext):
    if message.text == '❌ Скасувати':
        await state.clear()
        await message.answer("❌ Скасовано.", reply_markup=admin_menu())
        return

    category = message.text.strip()
    data = await state.get_data()
    await state.clear()

    product_id = await add_product(
        data.get('item_name', ''),
        data.get('item_description', ''),
        data.get('item_price', 0.0),
        category
    )

    await message.answer(
        f"✅ <b>Товар успішно додано!</b>\n\n"
        f"ID: {product_id}\n"
        f"Назва: {data.get('item_name')}\n"
        f"Опис: {data.get('item_description')}\n"
        f"Ціна: {data.get('item_price'):.2f} UAH\n"
        f"Категорія: {category}",
        reply_markup=admin_menu()
    )
    logger.info(f"Product added by admin {message.from_user.id}: id={product_id}")


# ─── Remove Product ─────────────────────────────────────────────────────────

@router.message(F.text == '❌ Видалити товар')
async def btn_remove_item(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ заборонено.")
        return
    products = await get_all_products()
    if not products:
        await message.answer("Каталог порожній.", reply_markup=admin_menu())
        return
    await message.answer(
        "❌ <b>Виберіть товар для видалення:</b>",
        reply_markup=remove_product_keyboard(products)
    )


@router.callback_query(F.data.startswith('admin_remove_'))
async def admin_remove_product(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    product_id = int(callback.data.split('_')[2])
    product = await get_product(product_id)
    if not product:
        await callback.answer("Товар не знайдено.", show_alert=True)
        return

    success = await remove_product(product_id)
    if success:
        await callback.answer(f"✅ '{product['name']}' видалено.")
        await callback.message.edit_text(
            f"✅ Товар <b>{product['name']}</b> видалено з каталогу."
        )
        logger.info(f"Product {product_id} removed by admin {callback.from_user.id}")
    else:
        await callback.answer("❗ Помилка при видаленні.", show_alert=True)


@router.callback_query(F.data == 'admin_back')
async def admin_back(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()


# ─── Orders ─────────────────────────────────────────────────────────────────

@router.message(Command('orders'))
async def cmd_all_orders(message: Message):
    if not is_admin(message.from_user.id):
        return  # non-admin /orders is handled in user.py
    await _show_all_orders(message)


@router.message(F.text == '📋 Замовлення')
async def btn_orders(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ заборонено.")
        return
    await _show_all_orders(message)


async def _show_all_orders(message: Message):
    orders = await get_all_orders()
    if not orders:
        await message.answer("Замовлень поки немає.", reply_markup=admin_menu())
        return

    lines = ["📋 <b>Всі замовлення:</b>\n"]
    for o in orders[:10]:
        status_emoji = {
            'pending': '⏳', 'processing': '🔄',
            'completed': '✅', 'cancelled': '❌'
        }.get(o['status'], '❓')
        lines.append(
            f"{status_emoji} #{o['id']} | @{o['username'] or o['user_id']} | "
            f"{o['total']:.2f} UAH | {o['created_at'][:10]}"
        )

    if len(orders) > 10:
        lines.append(f"\n...та ще {len(orders) - 10} замовлень.")

    # Show the most recent order with action buttons
    if orders:
        latest = orders[0]
        await message.answer(
            "\n".join(lines),
            reply_markup=admin_order_keyboard(latest['id'])
        )
    else:
        await message.answer("\n".join(lines), reply_markup=admin_menu())

    logger.info(f"Orders viewed by admin {message.from_user.id}")


@router.callback_query(F.data.startswith('approve_order_'))
async def approve_order(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return
    order_id = int(callback.data.split('_')[2])
    await update_order_status(order_id, 'processing')
    await callback.answer(f"✅ Замовлення #{order_id} підтверджено.")
    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ Замовлення #{order_id} підтверджено адміністратором."
    )
    logger.info(f"Order #{order_id} approved by admin {callback.from_user.id}")


@router.callback_query(F.data.startswith('reject_order_'))
async def reject_order(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return
    order_id = int(callback.data.split('_')[2])
    await update_order_status(order_id, 'cancelled')
    await callback.answer(f"❌ Замовлення #{order_id} відхилено.")
    await callback.message.edit_text(
        callback.message.text + f"\n\n❌ Замовлення #{order_id} відхилено адміністратором."
    )
    logger.info(f"Order #{order_id} rejected by admin {callback.from_user.id}")


# ─── Feedback ───────────────────────────────────────────────────────────────

@router.message(F.text == '📊 Відгуки')
async def btn_feedback_list(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ заборонено.")
        return

    feedbacks = await get_all_feedback()
    if not feedbacks:
        await message.answer("Відгуків поки немає.", reply_markup=admin_menu())
        return

    lines = ["📊 <b>Відгуки клієнтів:</b>\n"]
    for f in feedbacks[:10]:
        lines.append(
            f"• @{f['username'] or f['user_id']} ({f['created_at'][:10]}):\n"
            f"  {f['text'][:120]}{'...' if len(f['text']) > 120 else ''}\n"
        )
    if len(feedbacks) > 10:
        lines.append(f"...та ще {len(feedbacks) - 10} відгуків.")

    await message.answer("\n".join(lines), reply_markup=admin_menu())
    logger.info(f"Feedback list viewed by admin {message.from_user.id}")