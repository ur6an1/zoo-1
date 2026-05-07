"""Tests for bot.handlers.analysis — AI medical analysis handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.analysis import (
    analysis_not_photo,
    analysis_pet_chosen,
    analysis_start,
    cb_analysis_start,
    _no_ai_message,
    _ai_limit_message,
    _pet_info_str,
)

PET = {"id": 1, "name": "Rex", "species": "собака", "breed": "Лабрадор",
       "birth_date": None, "weight": 5.0, "age_str": "2 года",
       "species_emoji": "🐶"}


def _msg(text: str = "/start") -> MagicMock:
    m = MagicMock()
    m.text = text
    m.from_user = MagicMock(id=1)
    m.answer = AsyncMock()
    return m


def _cb(data: str = "analysis:start") -> MagicMock:
    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock(id=1)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _state(data: dict | None = None) -> MagicMock:
    s = MagicMock()
    s.clear = AsyncMock()
    s.set_state = AsyncMock()
    s.update_data = AsyncMock()
    s.get_data = AsyncMock(return_value=data or {})
    return s


# ── helper functions ──


def test_no_ai_message():
    assert "недоступны" in _no_ai_message()


def test_ai_limit_message():
    assert "лимит" in _ai_limit_message()


def test_pet_info_str_basic():
    result = _pet_info_str({"species": "собака", "name": "Rex"})
    assert "собака" in result
    assert "Rex" in result


def test_pet_info_str_with_breed():
    result = _pet_info_str({"species": "кот", "name": "Tom", "breed": "Сиамский", "weight": 4.0})
    assert "Сиамский" in result
    assert "4.0" in result


# ── analysis_start ──


@pytest.mark.asyncio
@patch("bot.handlers.analysis.api_client")
async def test_analysis_start_ai_not_ok(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    msg = _msg(text="🔬 Анализы")
    state = _state()
    await analysis_start(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.analysis.api_client")
async def test_analysis_start_no_pets(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[])
    msg = _msg(text="🔬 Анализы")
    state = _state()
    await analysis_start(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.analysis.api_client")
async def test_analysis_start_with_pets(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[PET])
    msg = _msg(text="🔬 Анализы")
    state = _state()
    await analysis_start(msg, state)
    state.set_state.assert_awaited_once()
    msg.answer.assert_awaited_once()


# ── cb_analysis_start ──


@pytest.mark.asyncio
@patch("bot.handlers.analysis.api_client")
async def test_cb_analysis_start_ai_not_ok(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    cb = _cb()
    state = _state()
    await cb_analysis_start(cb, state)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.analysis.api_client")
async def test_cb_analysis_start_no_pets(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    state = _state()
    await cb_analysis_start(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.analysis.api_client")
async def test_cb_analysis_start_with_pets(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb()
    state = _state()
    await cb_analysis_start(cb, state)
    state.set_state.assert_awaited_once()


# ── analysis_pet_chosen ──


@pytest.mark.asyncio
@patch("bot.handlers.analysis.api_client")
async def test_analysis_pet_chosen_invalid_id(mock_api: MagicMock):
    cb = _cb(data="pet:select_analysis:bad")
    state = _state()
    await analysis_pet_chosen(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.analysis.api_client")
async def test_analysis_pet_chosen_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="pet:select_analysis:1")
    state = _state()
    await analysis_pet_chosen(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.analysis.api_client")
async def test_analysis_pet_chosen_ok(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="pet:select_analysis:1")
    state = _state()
    await analysis_pet_chosen(cb, state)
    state.set_state.assert_awaited_once()
    state.update_data.assert_awaited_once()
    cb.message.edit_text.assert_awaited_once()


# ── analysis_not_photo ──


@pytest.mark.asyncio
async def test_analysis_not_photo():
    msg = _msg(text="hello")
    await analysis_not_photo(msg)
    msg.answer.assert_awaited_once()
