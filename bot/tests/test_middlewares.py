"""Tests for bot.middlewares — throttle, rate limit, error guard."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.middlewares.error_guard import ErrorGuardMiddleware
from bot.middlewares.throttle import RateLimitMiddleware, ThrottleMiddleware


# ══════════════ ThrottleMiddleware ══════════════


class TestThrottleMiddleware:
    def _make_event(self, user_id: int = 1, data: str = "action"):
        event = AsyncMock()
        event.from_user = MagicMock()
        event.from_user.id = user_id
        event.data = data
        return event

    async def test_first_call_passes(self):
        mw = ThrottleMiddleware(cooldown=1.0)
        handler = AsyncMock(return_value="ok")
        event = self._make_event()
        result = await mw(handler, event, {})
        assert result == "ok"
        handler.assert_awaited_once()

    async def test_duplicate_within_cooldown_blocked(self):
        mw = ThrottleMiddleware(cooldown=1.0)
        handler = AsyncMock(return_value="ok")
        event = self._make_event()

        await mw(handler, event, {})
        result = await mw(handler, event, {})
        assert result is None
        assert handler.await_count == 1
        event.answer.assert_awaited()

    async def test_different_users_not_blocked(self):
        mw = ThrottleMiddleware(cooldown=1.0)
        handler = AsyncMock(return_value="ok")

        event1 = self._make_event(user_id=1)
        event2 = self._make_event(user_id=2)

        await mw(handler, event1, {})
        await mw(handler, event2, {})
        assert handler.await_count == 2

    async def test_different_data_not_blocked(self):
        mw = ThrottleMiddleware(cooldown=1.0)
        handler = AsyncMock(return_value="ok")

        event1 = self._make_event(data="action1")
        event2 = self._make_event(data="action2")

        await mw(handler, event1, {})
        await mw(handler, event2, {})
        assert handler.await_count == 2

    async def test_after_cooldown_passes(self):
        mw = ThrottleMiddleware(cooldown=0.01)
        handler = AsyncMock(return_value="ok")
        event = self._make_event()

        await mw(handler, event, {})
        await asyncio.sleep(0.02)
        result = await mw(handler, event, {})
        assert result == "ok"
        assert handler.await_count == 2

    async def test_cache_cleanup_on_overflow(self):
        mw = ThrottleMiddleware(cooldown=0.001)
        handler = AsyncMock(return_value="ok")

        for i in range(510):
            event = self._make_event(user_id=i, data=f"data_{i}")
            mw._cache[(i, f"data_{i}")] = time.monotonic() - 100

        event = self._make_event(user_id=999)
        await mw(handler, event, {})
        assert len(mw._cache) < 510

    async def test_none_data_handled(self):
        mw = ThrottleMiddleware(cooldown=1.0)
        handler = AsyncMock(return_value="ok")
        event = self._make_event(data=None)
        event.data = None
        result = await mw(handler, event, {})
        assert result == "ok"


# ══════════════ RateLimitMiddleware ══════════════


class TestRateLimitMiddleware:
    def test_within_limit(self):
        rl = RateLimitMiddleware(max_requests=3, window_seconds=3600)
        assert rl.check_rate_limit(1) is True
        assert rl.check_rate_limit(1) is True
        assert rl.check_rate_limit(1) is True

    def test_exceeds_limit(self):
        rl = RateLimitMiddleware(max_requests=2, window_seconds=3600)
        assert rl.check_rate_limit(1) is True
        assert rl.check_rate_limit(1) is True
        assert rl.check_rate_limit(1) is False

    def test_different_users_independent(self):
        rl = RateLimitMiddleware(max_requests=1, window_seconds=3600)
        assert rl.check_rate_limit(1) is True
        assert rl.check_rate_limit(2) is True
        assert rl.check_rate_limit(1) is False
        assert rl.check_rate_limit(2) is False

    def test_get_remaining(self):
        rl = RateLimitMiddleware(max_requests=5, window_seconds=3600)
        assert rl.get_remaining(1) == 5
        rl.check_rate_limit(1)
        rl.check_rate_limit(1)
        assert rl.get_remaining(1) == 3

    def test_get_remaining_at_limit(self):
        rl = RateLimitMiddleware(max_requests=1, window_seconds=3600)
        rl.check_rate_limit(1)
        assert rl.get_remaining(1) == 0

    def test_expired_requests_cleared(self):
        rl = RateLimitMiddleware(max_requests=1, window_seconds=1)
        rl._user_requests[1] = [time.monotonic() - 10]
        assert rl.check_rate_limit(1) is True


# ══════════════ ErrorGuardMiddleware ══════════════


class TestErrorGuardMiddleware:
    async def test_normal_pass_through(self):
        mw = ErrorGuardMiddleware()
        handler = AsyncMock(return_value="result")
        event = MagicMock()
        result = await mw(handler, event, {})
        assert result == "result"

    async def test_value_error_caught(self):
        mw = ErrorGuardMiddleware()
        handler = AsyncMock(side_effect=ValueError("bad"))
        event = AsyncMock(spec=["answer", "from_user"])
        result = await mw(handler, event, {})
        assert result is None

    async def test_key_error_caught(self):
        mw = ErrorGuardMiddleware()
        handler = AsyncMock(side_effect=KeyError("missing"))
        event = AsyncMock(spec=["answer", "from_user"])
        result = await mw(handler, event, {})
        assert result is None

    async def test_generic_exception_caught(self):
        mw = ErrorGuardMiddleware()
        handler = AsyncMock(side_effect=RuntimeError("boom"))
        event = AsyncMock(spec=["answer", "from_user"])
        result = await mw(handler, event, {})
        assert result is None

    async def test_cancelled_error_reraised(self):
        mw = ErrorGuardMiddleware()
        handler = AsyncMock(side_effect=asyncio.CancelledError())
        event = MagicMock()
        with pytest.raises(asyncio.CancelledError):
            await mw(handler, event, {})

    async def test_callback_query_notified_on_value_error(self):
        from aiogram.types import CallbackQuery
        mw = ErrorGuardMiddleware()
        handler = AsyncMock(side_effect=ValueError("bad"))
        event = AsyncMock(spec=CallbackQuery)
        event.answer = AsyncMock()
        await mw(handler, event, {})
        event.answer.assert_awaited_once()
        call_args = event.answer.call_args
        assert call_args[1].get("show_alert") is True

    async def test_message_notified_on_generic_error(self):
        from aiogram.types import Message
        mw = ErrorGuardMiddleware()
        handler = AsyncMock(side_effect=RuntimeError("boom"))
        event = AsyncMock(spec=Message)
        event.answer = AsyncMock()
        await mw(handler, event, {})
        event.answer.assert_awaited_once()

    async def test_notification_failure_swallowed(self):
        from aiogram.types import Message
        mw = ErrorGuardMiddleware()
        handler = AsyncMock(side_effect=ValueError("bad"))
        event = AsyncMock(spec=Message)
        event.answer = AsyncMock(side_effect=Exception("telegram down"))
        result = await mw(handler, event, {})
        assert result is None
