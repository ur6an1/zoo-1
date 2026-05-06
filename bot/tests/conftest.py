"""Bot test fixtures."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("BACKEND_URL", "http://testserver")

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage


@pytest.fixture
def mock_user():
    """Telegram User mock."""
    user = MagicMock()
    user.id = 12345
    user.first_name = "Тестовый"
    user.last_name = "Пользователь"
    user.username = "testuser"
    return user


@pytest.fixture
def mock_message(mock_user):
    """Telegram Message mock."""
    msg = AsyncMock()
    msg.from_user = mock_user
    msg.text = ""
    msg.answer = AsyncMock()
    msg.reply = AsyncMock()
    msg.chat = MagicMock()
    msg.chat.id = 12345
    return msg


@pytest.fixture
def mock_callback(mock_user):
    """Telegram CallbackQuery mock."""
    cb = AsyncMock()
    cb.from_user = mock_user
    cb.data = ""
    cb.answer = AsyncMock()
    cb.message = AsyncMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.message.chat = MagicMock()
    cb.message.chat.id = 12345
    return cb


@pytest.fixture
def fsm_context():
    """Real FSM context with in-memory storage for state testing."""
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=12345, user_id=12345)
    return FSMContext(storage=storage, key=key)
