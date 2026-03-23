import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            user = event.from_user
            username = f"@{user.username}" if user.username else str(user.id)
            text = event.text or event.content_type
            logger.info(
                f"[MSG] user_id={user.id} {username} | chat={event.chat.id} | text={text!r}"
            )
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            username = f"@{user.username}" if user.username else str(user.id)
            logger.info(
                f"[CALLBACK] user_id={user.id} {username} | data={event.data!r}"
            )

        result = await handler(event, data)

        if isinstance(event, Message):
            logger.debug(
                f"[MSG DONE] user_id={event.from_user.id} | handler completed"
            )
        elif isinstance(event, CallbackQuery):
            logger.debug(
                f"[CALLBACK DONE] user_id={event.from_user.id} | data={event.data!r}"
            )

        return result