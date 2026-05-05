"""Middleware: throttle для callback и rate limit для AI-запросов."""

import logging
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)


class ThrottleMiddleware(BaseMiddleware):
    """Защита от двойных нажатий на inline-кнопки (Баг #17).

    Игнорирует повторные callback от одного пользователя
    с тем же callback_data в течение cooldown секунд.
    """

    def __init__(self, cooldown: float = 1.0):
        self.cooldown = cooldown
        self._cache: dict[tuple[int, str], float] = {}
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id
        cb_data = event.data or ""
        key = (user_id, cb_data)

        now = time.monotonic()
        last = self._cache.get(key, 0)

        if now - last < self.cooldown:
            await event.answer()
            return  # Игнорируем дубль

        self._cache[key] = now

        # Чистка кэша (каждые 100 записей)
        if len(self._cache) > 500:
            cutoff = now - self.cooldown * 10
            self._cache = {k: v for k, v in self._cache.items() if v > cutoff}

        return await handler(event, data)


class RateLimitMiddleware:
    """Rate limiting для AI-запросов (Баг #23).

    Ограничивает количество AI-запросов на пользователя.
    Используется как утилитарный класс, не как middleware.
    """

    def __init__(self, max_requests: int = 20, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window = window_seconds
        self._user_requests: dict[int, list[float]] = defaultdict(list)

    def check_rate_limit(self, user_id: int) -> bool:
        """Проверяет, не превышен ли лимит. True = можно, False = лимит."""
        now = time.monotonic()
        requests = self._user_requests[user_id]

        # Убираем старые записи
        self._user_requests[user_id] = [t for t in requests if now - t < self.window]

        if len(self._user_requests[user_id]) >= self.max_requests:
            return False

        self._user_requests[user_id].append(now)
        return True

    def get_remaining(self, user_id: int) -> int:
        """Возвращает оставшееся количество запросов."""
        now = time.monotonic()
        requests = [t for t in self._user_requests[user_id] if now - t < self.window]
        return max(0, self.max_requests - len(requests))


# Глобальный экземпляр rate limiter
ai_rate_limiter = RateLimitMiddleware(max_requests=20, window_seconds=3600)
