"""Tests for bot.handlers.analysis — AI medical analysis handlers."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.handlers.analysis import (
    _ai_limit_message,
    _no_ai_message,
    _pet_info_str,
    analysis_not_photo,
    analysis_pet_chosen,
    analysis_photo_received,
    analysis_start,
    cb_analysis_start,
)

PET = {"id": 1, "name": "Rex", "species": "собака", "breed": "Лабрадор",
       "birth_date": None, "weight": 5.0, "age_str": "2 года",
       "species_emoji": "🐶"}


def _msg(text: str = "/start") -> MagicMock:
    m = MagicMock()
    m.text = text
    m.from_user = MagicMock(id=1)
    m.chat = MagicMock(id=1)
    m.answer = AsyncMock()
    photo_obj = MagicMock()
    photo_obj.file_id = "file123"
    m.photo = [photo_obj]
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


def _bot() -> MagicMock:
    bot = MagicMock()
    bot.send_chat_action = AsyncMock()
    file_mock = MagicMock()
    file_mock.file_path = "photos/file.jpg"
    bot.get_file = AsyncMock(return_value=file_mock)
    bot.download_file = AsyncMock(return_value=io.BytesIO(b"fakeimage"))
    return bot


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


# ── analysis_photo_received ──


@pytest.mark.asyncio
@patch("bot.handlers.analysis.analyze_medical_test", new_callable=AsyncMock, return_value="Normal results")
@patch("bot.handlers.analysis.api_client")
async def test_analysis_photo_received_ok(mock_api, mock_analyze):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state(data={"analysis_pet_info": "собака Rex"})
    await analysis_photo_received(msg, state, bot)
    processing.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.analysis.api_client")
async def test_analysis_photo_received_ai_not_ok(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    msg = _msg()
    state = _state()
    bot = _bot()
    await analysis_photo_received(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.analysis.api_client")
async def test_analysis_photo_received_limit(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(False, 0))
    msg = _msg()
    state = _state()
    bot = _bot()
    await analysis_photo_received(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.analysis.api_client")
async def test_analysis_photo_received_download_error(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    bot.get_file = AsyncMock(side_effect=RuntimeError("err"))
    state = _state()
    await analysis_photo_received(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.analysis.analyze_medical_test", new_callable=AsyncMock, return_value=None)
@patch("bot.handlers.analysis.api_client")
async def test_analysis_photo_received_no_result(mock_api, mock_analyze):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state()
    await analysis_photo_received(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.analysis.analyze_medical_test", new_callable=AsyncMock, side_effect=RuntimeError("err"))
@patch("bot.handlers.analysis.api_client")
async def test_analysis_photo_received_exception(mock_api, mock_analyze):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state()
    await analysis_photo_received(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.analysis.analyze_medical_test", new_callable=AsyncMock, return_value="x" * 5000)
@patch("bot.handlers.analysis.api_client")
async def test_analysis_photo_received_long_result(mock_api, mock_analyze):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state(data={"analysis_pet_info": "собака Rex"})
    await analysis_photo_received(msg, state, bot)
    processing.edit_text.assert_awaited_once()
