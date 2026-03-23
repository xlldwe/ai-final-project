import logging
import io
import aiohttp
from aiogram import Router, F, Bot
from aiogram.types import Message

from bot_aiogram.config import BACKEND_URL

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    await message.answer("🔍 Аналізую зображення...")

    try:
        # Download highest resolution photo
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        image_bytes = await bot.download_file(file.file_path)

        # POST to backend predict API
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field(
                'image',
                image_bytes.read() if hasattr(image_bytes, 'read') else image_bytes,
                filename='photo.jpg',
                content_type='image/jpeg'
            )
            async with session.post(
                f"{BACKEND_URL}/api/predict",
                data=form,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
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
                        f"🛍️ Переглянути схожі товари → /catalog"
                    )
                elif resp.status == 503:
                    text = "⚠️ Нейронна мережа ще не натренована. Зверніться до адміністратора."
                else:
                    text = "❌ Не вдалося класифікувати зображення. Спробуйте інше фото."

    except aiohttp.ClientConnectorError:
        text = "⚠️ Сервер недоступний. Спробуйте пізніше."
    except Exception as e:
        logger.error(f"Photo classification error: {e}")
        text = "❌ Помилка обробки фото. Надішліть чіткіше зображення одягу."

    await message.answer(text)