"""Tests for worker.bot_sender — Bot singleton."""

import os

import pytest

os.environ["BOT_TOKEN"] = "123456789:ABCDefGhIJKlmnoPQRstuvWXYZ012345678"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")

from zoo_shared.config import get_settings

# Clear cached settings so new BOT_TOKEN is picked up
get_settings.cache_clear()

import worker.bot_sender as bot_sender  # noqa: E402


class TestGetBot:
    def test_returns_bot_instance(self):
        bot_sender._bot = None
        bot = bot_sender.get_bot()
        assert bot is not None
        bot_sender._bot = None

    def test_singleton(self):
        bot_sender._bot = None
        b1 = bot_sender.get_bot()
        b2 = bot_sender.get_bot()
        assert b1 is b2
        bot_sender._bot = None


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_send_message_failure(self):
        from unittest.mock import AsyncMock, MagicMock

        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(side_effect=Exception("Connection error"))
        bot_sender._bot = mock_bot
        result = await bot_sender.send_message(123, "test")
        assert result is False
        bot_sender._bot = None

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        from unittest.mock import AsyncMock, MagicMock

        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(return_value=True)
        bot_sender._bot = mock_bot
        result = await bot_sender.send_message(123, "test")
        assert result is True
        bot_sender._bot = None


class TestCloseBot:
    @pytest.mark.asyncio
    async def test_close_bot_when_none(self):
        bot_sender._bot = None
        await bot_sender.close_bot()
        assert bot_sender._bot is None

    @pytest.mark.asyncio
    async def test_close_bot_with_bot(self):
        from unittest.mock import AsyncMock, MagicMock

        mock_bot = MagicMock()
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        mock_bot.session = mock_session
        bot_sender._bot = mock_bot
        await bot_sender.close_bot()
        assert bot_sender._bot is None
        mock_session.close.assert_called_once()
