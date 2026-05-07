"""Tests for bot/bot/handlers/common.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.handlers.common import (
    ai_hub,
    back_to_menu_text,
    cb_cancel,
    cb_main_menu,
    cmd_cancel,
    cmd_help,
    cmd_start,
    health_hub,
    pets_hub,
    settings_hub,
)


def _make_message(user_id: int = 1, first_name: str = "Test", text: str = "") -> MagicMock:
    msg = AsyncMock()
    msg.from_user = MagicMock(id=user_id, first_name=first_name)
    msg.text = text
    msg.answer = AsyncMock()
    return msg


def _make_callback(user_id: int = 1, data: str = "") -> MagicMock:
    cb = AsyncMock()
    cb.from_user = MagicMock(id=user_id)
    cb.data = data
    cb.message = AsyncMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _make_state() -> AsyncMock:
    state = AsyncMock()
    state.clear = AsyncMock()
    state.get_state = AsyncMock(return_value=None)
    return state


@pytest.mark.asyncio
@patch("bot.handlers.common.api_client")
async def test_cmd_start(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.track_event = AsyncMock()
    msg = _make_message(first_name="Alice")
    state = _make_state()

    await cmd_start(msg, state)

    state.clear.assert_awaited_once()
    mock_api.track_user_activity.assert_awaited_once_with(1, source="start")
    mock_api.track_event.assert_awaited_once_with(1, "start", source="command")
    assert msg.answer.await_count == 2


@pytest.mark.asyncio
async def test_cmd_help():
    msg = _make_message()
    await cmd_help(msg)
    msg.answer.assert_awaited_once()
    call_kwargs = msg.answer.call_args
    assert "Помощь" in call_kwargs[0][0] or "Помощь" in call_kwargs.kwargs.get("text", call_kwargs[0][0])


@pytest.mark.asyncio
async def test_cmd_cancel_no_state():
    msg = _make_message()
    state = _make_state()
    state.get_state.return_value = None

    await cmd_cancel(msg, state)

    msg.answer.assert_awaited_once()
    args = msg.answer.call_args[0][0]
    assert "Нечего отменять" in args


@pytest.mark.asyncio
async def test_cmd_cancel_with_state():
    msg = _make_message()
    state = _make_state()
    state.get_state.return_value = "SomeState:step"

    await cmd_cancel(msg, state)

    state.clear.assert_awaited_once()
    args = msg.answer.call_args[0][0]
    assert "отменено" in args


@pytest.mark.asyncio
async def test_cb_cancel():
    cb = _make_callback(data="cancel")
    state = _make_state()

    await cb_cancel(cb, state)

    state.clear.assert_awaited_once()
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_main_menu():
    cb = _make_callback(data="menu:main")
    state = _make_state()

    await cb_main_menu(cb, state)

    state.clear.assert_awaited_once()
    cb.message.answer.assert_awaited_once()
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_back_to_menu_text():
    msg = _make_message(text="◀️ Назад в меню")
    state = _make_state()

    await back_to_menu_text(msg, state)

    state.clear.assert_awaited_once()
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_pets_hub_handler():
    msg = _make_message(text="🐾 Питомцы")
    await pets_hub(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_hub_handler():
    msg = _make_message(text="🩺 Здоровье")
    await health_hub(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_ai_hub_handler():
    msg = _make_message(text="🤖 AI-сервисы")
    await ai_hub(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_settings_hub_handler():
    msg = _make_message(text="⚙️ Настройки")
    await settings_hub(msg)
    msg.answer.assert_awaited_once()
