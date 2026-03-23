import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot_aiogram.database import register_user, save_feedback, get_user_orders
from bot_aiogram.keyboards.reply import main_menu, cancel_keyboard
from bot_aiogram.states.states import FeedbackStates

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await register_user(user.id, user.username, user.first_name, user.last_name)
    logger.info(f"User started bot: {user.id} @{user.username}")
    await message.answer(
        f"👋 Вітаємо у <b>FashionAI Shop</b>, {user.first_name}!\n\n"
        "Ми — сучасний онлайн-магазин одягу з AI-підтримкою.\n\n"
        "Оберіть розділ у меню нижче:",
        reply_markup=main_menu()
    )


@router.message(Command('help'))
async def cmd_help(message: Message):
    logger.info(f"User /help: {message.from_user.id}")
    await message.answer(
        "📚 <b>Доступні команди:</b>\n\n"
        "/start — Головне меню\n"
        "/catalog — Каталог товарів\n"
        "/cart — Мій кошик\n"
        "/orders — Мої замовлення\n"
        "/help — Допомога\n"
        "/info — Про магазин\n"
        "/admin — Адмін панель (тільки для адміністраторів)\n\n"
        "Або використовуйте кнопки меню."
    )


@router.message(Command('info'))
async def cmd_info(message: Message):
    await _send_info(message)


@router.message(F.text == 'ℹ️ Про нас')
async def btn_info(message: Message):
    await _send_info(message)


async def _send_info(message: Message):
    await message.answer(
        "🏪 <b>FashionAI Shop</b>\n\n"
        "Ми — сучасний онлайн-магазин одягу з AI-підтримкою.\n\n"
        "📦 <b>Доставка:</b>\n"
        "• Стандартна: 2-5 робочих днів\n"
        "• Експрес: 1-2 робочих дні\n\n"
        "🚚 Безкоштовна доставка від 1000 UAH\n"
        "↩️ Повернення протягом 30 днів\n"
        "💳 Оплата: картка, PayPal, Telegram Payments\n"
        "📧 Підтримка: support@fashionai.shop\n"
        "🌐 Сайт: fashionai.shop"
    )


@router.message(F.text == '❓ Допомога')
async def btn_help(message: Message):
    await cmd_help(message)


@router.message(Command('orders'))
async def cmd_orders(message: Message):
    await _show_user_orders(message)


@router.message(F.text == '📋 Мої замовлення')
async def btn_orders(message: Message):
    await _show_user_orders(message)


async def _show_user_orders(message: Message):
    orders = await get_user_orders(message.from_user.id)
    if not orders:
        await message.answer("У вас поки немає замовлень. Перегляньте наш каталог!")
        return

    lines = ["📋 <b>Ваші замовлення:</b>\n"]
    for o in orders[:10]:
        status_emoji = {'pending': '⏳', 'processing': '🔄', 'shipped': '🚚', 'completed': '✅', 'cancelled': '❌'}.get(o['status'], '❓')
        lines.append(
            f"{status_emoji} Замовлення #{o['id']}\n"
            f"   Сума: {o['total']:.2f} UAH | {o['status']}\n"
            f"   Дата: {o['created_at'][:10]}\n"
        )
    await message.answer("\n".join(lines))


@router.message(F.text == '📝 Відгук')
async def btn_feedback(message: Message, state: FSMContext):
    await state.set_state(FeedbackStates.waiting_feedback)
    await message.answer(
        "💬 Напишіть свій відгук про наш магазин:",
        reply_markup=cancel_keyboard()
    )


@router.message(FeedbackStates.waiting_feedback)
async def process_feedback(message: Message, state: FSMContext):
    if message.text == '❌ Скасувати':
        await state.clear()
        await message.answer("Відгук скасовано.", reply_markup=main_menu())
        return

    text = message.text.strip()
    if len(text) < 5:
        await message.answer("❗ Відгук занадто короткий. Будь ласка, напишіть детальніше:")
        return

    user = message.from_user
    await save_feedback(user.id, user.username or '', text)
    await state.clear()
    await message.answer(
        "✅ Дякуємо за ваш відгук! Ми цінуємо вашу думку.",
        reply_markup=main_menu()
    )
    logger.info(f"Feedback saved from user {user.id}")