"""Глобальная защита от необработанных ошибок в update-пайплайне."""

import asyncio
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)


class ErrorGuardMiddleware(BaseMiddleware):
    """Перехватывает ошибки, чтобы не ронять сценарий пользователю."""

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except asyncio.CancelledError:
            raise
        except (ValueError, IndexError, KeyError) as e:
            logger.warning("Некорректные входные данные в update: %s", e)
            await self._safe_notify_user(event, invalid_data=True)
            return None
        except Exception as e:
            logger.exception("Необработанная ошибка в update: %s", e)
            await self._safe_notify_user(event, invalid_data=False)
            return None

    @staticmethod
    async def _safe_notify_user(event: Any, *, invalid_data: bool) -> None:
        text = (
            "Некорректные данные. Попробуйте открыть раздел заново."
            if invalid_data
            else "Произошла ошибка. Повторите действие через несколько секунд."
        )
        try:
            if isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=invalid_data)
                return
            if isinstance(event, Message):
                await event.answer(text)
        except Exception:
            # Нельзя допустить вторичное падение в middleware.
            logger.debug("Не удалось отправить fallback-уведомление пользователю")
