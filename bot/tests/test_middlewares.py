"""Tests for bot/bot/middlewares/error_guard.py and throttle.py."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from bot.middlewares.error_guard import ErrorGuardMiddleware
from bot.middlewares.throttle import RateLimitMiddleware, ThrottleMiddleware, ai_rate_limiter

# ── ErrorGuardMiddleware ──


class TestErrorGuardMiddleware:
    @pytest.fixture
    def middleware(self):
        return ErrorGuardMiddleware()

    @pytest.mark.asyncio
    async def test_passes_through_on_success(self, middleware: ErrorGuardMiddleware):
        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        data: dict = {}

        result = await middleware(handler, event, data)

        assert result == "ok"
        handler.assert_awaited_once_with(event, data)

    @pytest.mark.asyncio
    async def test_catches_value_error(self, middleware: ErrorGuardMiddleware):
        handler = AsyncMock(side_effect=ValueError("bad input"))
        event = AsyncMock(spec=["answer"])
        event.answer = AsyncMock()
        data: dict = {}

        result = await middleware(handler, event, data)

        assert result is None

    @pytest.mark.asyncio
    async def test_catches_key_error(self, middleware: ErrorGuardMiddleware):
        handler = AsyncMock(side_effect=KeyError("missing"))
        event = AsyncMock(spec=["answer"])
        event.answer = AsyncMock()
        data: dict = {}

        result = await middleware(handler, event, data)

        assert result is None

    @pytest.mark.asyncio
    async def test_catches_generic_exception(self, middleware: ErrorGuardMiddleware):
        handler = AsyncMock(side_effect=RuntimeError("unexpected"))
        event = AsyncMock(spec=["answer"])
        event.answer = AsyncMock()
        data: dict = {}

        result = await middleware(handler, event, data)

        assert result is None

    @pytest.mark.asyncio
    async def test_re_raises_cancelled_error(self, middleware: ErrorGuardMiddleware):
        handler = AsyncMock(side_effect=asyncio.CancelledError())
        event = MagicMock()
        data: dict = {}

        with pytest.raises(asyncio.CancelledError):
            await middleware(handler, event, data)

    @pytest.mark.asyncio
    async def test_notify_user_callback_query(self, middleware: ErrorGuardMiddleware):
        from aiogram.types import CallbackQuery

        handler = AsyncMock(side_effect=ValueError("test"))
        event = MagicMock(spec=CallbackQuery)
        event.answer = AsyncMock()
        data: dict = {}

        await middleware(handler, event, data)

        event.answer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_notify_user_message(self, middleware: ErrorGuardMiddleware):
        from aiogram.types import Message

        handler = AsyncMock(side_effect=RuntimeError("test"))
        event = MagicMock(spec=Message)
        event.answer = AsyncMock()
        data: dict = {}

        await middleware(handler, event, data)

        event.answer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_notify_user_handles_send_failure(self, middleware: ErrorGuardMiddleware):
        from aiogram.types import Message

        handler = AsyncMock(side_effect=RuntimeError("test"))
        event = MagicMock(spec=Message)
        event.answer = AsyncMock(side_effect=Exception("send failed"))
        data: dict = {}

        result = await middleware(handler, event, data)

        assert result is None


# ── ThrottleMiddleware ──


class TestThrottleMiddleware:
    @pytest.fixture
    def middleware(self):
        return ThrottleMiddleware(cooldown=0.5)

    @pytest.mark.asyncio
    async def test_passes_first_call(self, middleware: ThrottleMiddleware):
        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        event.from_user = MagicMock(id=1)
        event.data = "test:action"
        event.answer = AsyncMock()

        result = await middleware(handler, event, {})

        assert result == "ok"
        handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_throttles_duplicate(self, middleware: ThrottleMiddleware):
        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        event.from_user = MagicMock(id=1)
        event.data = "test:action"
        event.answer = AsyncMock()

        await middleware(handler, event, {})
        result = await middleware(handler, event, {})

        assert result is None
        assert handler.await_count == 1
        event.answer.assert_awaited()

    @pytest.mark.asyncio
    async def test_allows_after_cooldown(self, middleware: ThrottleMiddleware):
        middleware.cooldown = 0.01
        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        event.from_user = MagicMock(id=1)
        event.data = "test:action"
        event.answer = AsyncMock()

        await middleware(handler, event, {})
        await asyncio.sleep(0.02)
        result = await middleware(handler, event, {})

        assert result == "ok"
        assert handler.await_count == 2

    @pytest.mark.asyncio
    async def test_different_users_not_throttled(self, middleware: ThrottleMiddleware):
        handler = AsyncMock(return_value="ok")
        event1 = MagicMock()
        event1.from_user = MagicMock(id=1)
        event1.data = "test:action"
        event1.answer = AsyncMock()

        event2 = MagicMock()
        event2.from_user = MagicMock(id=2)
        event2.data = "test:action"
        event2.answer = AsyncMock()

        await middleware(handler, event1, {})
        result = await middleware(handler, event2, {})

        assert result == "ok"
        assert handler.await_count == 2

    @pytest.mark.asyncio
    async def test_different_data_not_throttled(self, middleware: ThrottleMiddleware):
        handler = AsyncMock(return_value="ok")
        event1 = MagicMock()
        event1.from_user = MagicMock(id=1)
        event1.data = "action:a"
        event1.answer = AsyncMock()

        event2 = MagicMock()
        event2.from_user = MagicMock(id=1)
        event2.data = "action:b"
        event2.answer = AsyncMock()

        await middleware(handler, event1, {})
        result = await middleware(handler, event2, {})

        assert result == "ok"
        assert handler.await_count == 2

    @pytest.mark.asyncio
    async def test_cache_cleanup(self):
        mw = ThrottleMiddleware(cooldown=0.01)
        handler = AsyncMock(return_value="ok")

        for i in range(600):
            event = MagicMock()
            event.from_user = MagicMock(id=i)
            event.data = f"action:{i}"
            event.answer = AsyncMock()
            await mw(handler, event, {})

        assert len(mw._cache) < 600


# ── RateLimitMiddleware ──


class TestRateLimitMiddleware:
    def test_allows_within_limit(self):
        rl = RateLimitMiddleware(max_requests=3, window_seconds=3600)
        assert rl.check_rate_limit(1) is True
        assert rl.check_rate_limit(1) is True
        assert rl.check_rate_limit(1) is True

    def test_blocks_over_limit(self):
        rl = RateLimitMiddleware(max_requests=2, window_seconds=3600)
        rl.check_rate_limit(1)
        rl.check_rate_limit(1)
        assert rl.check_rate_limit(1) is False

    def test_different_users_independent(self):
        rl = RateLimitMiddleware(max_requests=1, window_seconds=3600)
        assert rl.check_rate_limit(1) is True
        assert rl.check_rate_limit(2) is True
        assert rl.check_rate_limit(1) is False

    def test_get_remaining(self):
        rl = RateLimitMiddleware(max_requests=5, window_seconds=3600)
        assert rl.get_remaining(1) == 5
        rl.check_rate_limit(1)
        assert rl.get_remaining(1) == 4

    def test_global_instance_exists(self):
        assert isinstance(ai_rate_limiter, RateLimitMiddleware)
        assert ai_rate_limiter.max_requests == 20
