"""Tests for bot/bot/handlers/reminders.py."""

from __future__ import annotations

from datetime import datetime as _dt
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.handlers.reminders import (
    cb_reminder_add,
    cb_reminder_cancel,
    cb_reminder_delete,
    cb_reminder_list,
    cb_reminder_pause,
    cb_reminder_pet,
    cb_reminder_resume,
    cb_reminder_view,
    cb_reminders_menu,
    reminder_category,
    reminder_date,
    reminder_description,
    reminder_repeat,
    reminder_time,
    reminder_title,
    reminders_menu,
)


def _msg(user_id: int = 1, text: str = "") -> MagicMock:
    m = AsyncMock()
    m.from_user = MagicMock(id=user_id)
    m.text = text
    m.answer = AsyncMock()
    return m


def _cb(user_id: int = 1, data: str = "") -> MagicMock:
    c = AsyncMock()
    c.from_user = MagicMock(id=user_id)
    c.data = data
    c.message = AsyncMock()
    c.message.edit_text = AsyncMock()
    c.message.answer = AsyncMock()
    c.answer = AsyncMock()
    return c


def _state(data: dict | None = None) -> AsyncMock:
    s = AsyncMock()
    s.clear = AsyncMock()
    s.set_state = AsyncMock()
    s.update_data = AsyncMock()
    s.get_data = AsyncMock(return_value=data or {})
    return s


SAMPLE_REMINDER = {
    "id": 1, "title": "Feed Rex", "pet_name": "Rex",
    "category_emoji": "🍽", "remind_at": _dt(2026, 1, 15, 9, 0, 0),
    "repeat": "daily", "repeat_text": "ежедневно",
    "description": "Morning meal", "is_active": True,
}


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_reminders_menu(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    msg = _msg()
    await reminders_menu(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_reminders_menu():
    cb = _cb(data="reminder:menu")
    await cb_reminders_menu(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_add_no_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb(data="reminder:add")
    state = _state()
    await cb_reminder_add(cb, state)
    cb.message.edit_text.assert_awaited_once()
    assert "добавьте" in cb.message.edit_text.call_args[0][0].lower()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_add_with_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Rex", "species_emoji": "🐶"}])
    cb = _cb(data="reminder:add")
    state = _state()
    await cb_reminder_add(cb, state)
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_pet_valid(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value={"id": 1, "name": "Rex"})
    cb = _cb(data="pet:select_reminder:1")
    state = _state()
    await cb_reminder_pet(cb, state)
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_pet_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="pet:select_reminder:1")
    state = _state()
    await cb_reminder_pet(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_reminder_category_handler():
    cb = _cb(data="rem_cat:feeding")
    state = _state()
    await reminder_category(cb, state)
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_reminder_title_valid():
    msg = _msg(text="Feed Rex")
    state = _state()
    await reminder_title(msg, state)
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_reminder_title_too_long():
    msg = _msg(text="T" * 201)
    state = _state()
    await reminder_title(msg, state)
    msg.answer.assert_awaited_once()
    assert "200" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_reminder_description_text():
    msg = _msg(text="Morning meal")
    state = _state()
    await reminder_description(msg, state)
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_reminder_description_skip():
    msg = _msg(text="-")
    state = _state()
    await reminder_description(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_reminder_date_valid():
    msg = _msg(text="15.03.2026")
    state = _state()
    await reminder_date(msg, state)
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_reminder_date_invalid():
    msg = _msg(text="bad_date")
    state = _state()
    await reminder_date(msg, state)
    msg.answer.assert_awaited_once()
    assert "формат" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_reminder_time_valid():
    msg = _msg(text="09:00")
    state = _state()
    await reminder_time(msg, state)
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_reminder_time_invalid():
    msg = _msg(text="25:99")
    state = _state()
    await reminder_time(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_reminder_repeat_handler(mock_api: MagicMock):
    mock_api.create_reminder = AsyncMock(return_value={"id": 1})
    mock_api.get_pet = AsyncMock(return_value={"name": "Rex"})
    cb = _cb(data="repeat:daily")
    state = _state(data={
        "pet_id": 1, "title": "Feed", "description": "Morning",
        "category": "feeding", "date": "2026-03-15", "hour": 9, "minute": 0,
    })
    await reminder_repeat(cb, state)
    state.clear.assert_awaited_once()
    mock_api.create_reminder.assert_awaited_once()
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_list_empty(mock_api: MagicMock):
    mock_api.list_reminders = AsyncMock(return_value=[])
    cb = _cb(data="reminder:list")
    await cb_reminder_list(cb)
    cb.message.edit_text.assert_awaited_once()
    assert "нет напоминаний" in cb.message.edit_text.call_args[0][0].lower()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_list_with_items(mock_api: MagicMock):
    mock_api.list_reminders = AsyncMock(return_value=[
        SAMPLE_REMINDER,
        {**SAMPLE_REMINDER, "id": 2, "is_active": False},
    ])
    cb = _cb(data="reminder:list")
    await cb_reminder_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_view(mock_api: MagicMock):
    mock_api.get_reminder = AsyncMock(return_value=SAMPLE_REMINDER)
    cb = _cb(data="reminder:view:1")
    await cb_reminder_view(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_view_not_found(mock_api: MagicMock):
    mock_api.get_reminder = AsyncMock(return_value=None)
    cb = _cb(data="reminder:view:1")
    await cb_reminder_view(cb)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_pause(mock_api: MagicMock):
    mock_api.pause_reminder = AsyncMock(return_value={"title": "Feed Rex"})
    cb = _cb(data="reminder:pause:1")
    await cb_reminder_pause(cb)
    cb.message.edit_text.assert_awaited_once()
    assert "приостановлено" in cb.message.edit_text.call_args[0][0].lower()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_pause_not_found(mock_api: MagicMock):
    mock_api.pause_reminder = AsyncMock(return_value=None)
    cb = _cb(data="reminder:pause:1")
    await cb_reminder_pause(cb)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_resume(mock_api: MagicMock):
    mock_api.resume_reminder = AsyncMock(return_value={"title": "Feed Rex"})
    cb = _cb(data="reminder:resume:1")
    await cb_reminder_resume(cb)
    cb.message.edit_text.assert_awaited_once()
    assert "возобновлено" in cb.message.edit_text.call_args[0][0].lower()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_resume_not_found(mock_api: MagicMock):
    mock_api.resume_reminder = AsyncMock(return_value=None)
    cb = _cb(data="reminder:resume:1")
    await cb_reminder_resume(cb)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_delete_success(mock_api: MagicMock):
    mock_api.delete_reminder = AsyncMock(return_value=True)
    cb = _cb(data="reminder:delete:1")
    await cb_reminder_delete(cb)
    cb.message.edit_text.assert_awaited_once()
    assert "удалено" in cb.message.edit_text.call_args[0][0].lower()


@pytest.mark.asyncio
@patch("bot.handlers.reminders.api_client")
async def test_cb_reminder_delete_not_found(mock_api: MagicMock):
    mock_api.delete_reminder = AsyncMock(return_value=False)
    cb = _cb(data="reminder:delete:1")
    await cb_reminder_delete(cb)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_reminder_cancel():
    cb = _cb(data="reminder:cancel")
    state = _state()
    await cb_reminder_cancel(cb, state)
    state.clear.assert_awaited_once()
    cb.message.edit_text.assert_awaited_once()
