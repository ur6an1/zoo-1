"""Tests for bot.handlers.calendar_view — calendar event handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.handlers.calendar_view import calendar_menu, cb_calendar_view


def _msg(text: str = "📅 Календарь") -> MagicMock:
    m = MagicMock()
    m.text = text
    m.from_user = MagicMock(id=1)
    m.answer = AsyncMock()
    return m


def _cb(data: str = "calendar:view") -> MagicMock:
    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock(id=1)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


# ── calendar_menu ──


@pytest.mark.asyncio
@patch("bot.handlers.calendar_view.api_client")
async def test_calendar_menu_no_pets(mock_api: MagicMock):
    mock_api.get_medical_calendar = AsyncMock(return_value={"pets": []})
    msg = _msg()
    await calendar_menu(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.calendar_view.api_client")
async def test_calendar_menu_with_events(mock_api: MagicMock):
    mock_api.get_medical_calendar = AsyncMock(return_value={
        "pets": [{"id": 1, "name": "Rex"}],
        "reminders": [
            {"remind_at": "2026-06-01T10:00:00", "title": "Feed",
             "pet_name": "Rex", "category_emoji": "🔔", "repeat_text": "daily"},
        ],
        "vaccinations": [],
        "vet_visits": [],
    })
    msg = _msg()
    await calendar_menu(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.calendar_view.api_client")
async def test_calendar_menu_error(mock_api: MagicMock):
    mock_api.get_medical_calendar = AsyncMock(side_effect=RuntimeError("fail"))
    msg = _msg()
    await calendar_menu(msg)
    msg.answer.assert_awaited_once()


# ── cb_calendar_view ──


@pytest.mark.asyncio
@patch("bot.handlers.calendar_view.api_client")
async def test_cb_calendar_view_no_pets(mock_api: MagicMock):
    mock_api.get_medical_calendar = AsyncMock(return_value={"pets": []})
    cb = _cb()
    await cb_calendar_view(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.calendar_view.api_client")
async def test_cb_calendar_view_error(mock_api: MagicMock):
    mock_api.get_medical_calendar = AsyncMock(side_effect=RuntimeError("fail"))
    cb = _cb()
    await cb_calendar_view(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.calendar_view.api_client")
async def test_cb_calendar_view_empty_events(mock_api: MagicMock):
    mock_api.get_medical_calendar = AsyncMock(return_value={
        "pets": [{"id": 1, "name": "Rex"}],
        "reminders": [],
        "vaccinations": [],
        "vet_visits": [],
    })
    cb = _cb()
    await cb_calendar_view(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.calendar_view.api_client")
async def test_cb_calendar_view_with_vaccinations(mock_api: MagicMock):
    mock_api.get_medical_calendar = AsyncMock(return_value={
        "pets": [{"id": 1, "name": "Rex"}],
        "reminders": [],
        "vaccinations": [
            {"name": "Rabies", "next_date": "2026-12-01T00:00:00", "pet_name": "Rex"},
        ],
        "vet_visits": [
            {"visit_date": "2026-06-01T00:00:00", "pet_name": "Rex", "diagnosis": "OK"},
        ],
    })
    cb = _cb()
    await cb_calendar_view(cb)
    cb.message.edit_text.assert_awaited_once()
