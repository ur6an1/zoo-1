"""Tests for bot.handlers.voice — voice notes handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.handlers.voice import (
    cb_voice_add,
    cb_voice_list,
    cb_voice_menu,
    cb_voice_pet,
    voice_menu,
    voice_not_voice,
)

PET = {"id": 1, "name": "Rex", "species": "собака"}


def _msg(text: str = "🎙 Голосовые") -> MagicMock:
    m = MagicMock()
    m.text = text
    m.from_user = MagicMock(id=1)
    m.answer = AsyncMock()
    return m


def _cb(data: str = "voice:menu") -> MagicMock:
    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock(id=1)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _state(data: dict | None = None) -> MagicMock:
    s = MagicMock()
    s.clear = AsyncMock()
    s.set_state = AsyncMock()
    s.update_data = AsyncMock()
    s.get_data = AsyncMock(return_value=data or {})
    return s


# ── voice_menu ──


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_voice_menu_no_permission(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.check_feature_permission = AsyncMock(return_value=False)
    msg = _msg()
    state = _state()
    await voice_menu(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_voice_menu_ok(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.check_feature_permission = AsyncMock(return_value=True)
    mock_api.track_event = AsyncMock()
    msg = _msg()
    state = _state()
    await voice_menu(msg, state)
    msg.answer.assert_awaited_once()


# ── cb_voice_menu ──


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_cb_voice_menu_no_permission(mock_api: MagicMock):
    mock_api.check_feature_permission = AsyncMock(return_value=False)
    cb = _cb()
    state = _state()
    await cb_voice_menu(cb, state)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_cb_voice_menu_ok(mock_api: MagicMock):
    mock_api.check_feature_permission = AsyncMock(return_value=True)
    mock_api.track_event = AsyncMock()
    cb = _cb()
    state = _state()
    await cb_voice_menu(cb, state)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


# ── cb_voice_add ──


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_cb_voice_add_no_permission(mock_api: MagicMock):
    mock_api.check_feature_permission = AsyncMock(return_value=False)
    cb = _cb(data="voice:add")
    state = _state()
    await cb_voice_add(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_cb_voice_add_no_pets(mock_api: MagicMock):
    mock_api.check_feature_permission = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb(data="voice:add")
    state = _state()
    await cb_voice_add(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_cb_voice_add_with_pets(mock_api: MagicMock):
    mock_api.check_feature_permission = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb(data="voice:add")
    state = _state()
    await cb_voice_add(cb, state)
    state.set_state.assert_awaited_once()


# ── cb_voice_pet ──


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_cb_voice_pet_invalid(mock_api: MagicMock):
    cb = _cb(data="pet:select_voice:bad")
    state = _state()
    await cb_voice_pet(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_cb_voice_pet_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="pet:select_voice:1")
    state = _state()
    await cb_voice_pet(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_cb_voice_pet_ok(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="pet:select_voice:1")
    state = _state()
    await cb_voice_pet(cb, state)
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()


# ── voice_not_voice ──


@pytest.mark.asyncio
async def test_voice_not_voice():
    msg = _msg(text="text not voice")
    await voice_not_voice(msg)
    msg.answer.assert_awaited_once()


# ── cb_voice_list ──


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_cb_voice_list_no_permission(mock_api: MagicMock):
    mock_api.check_feature_permission = AsyncMock(return_value=False)
    cb = _cb(data="voice:list")
    await cb_voice_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_cb_voice_list_empty(mock_api: MagicMock):
    mock_api.check_feature_permission = AsyncMock(return_value=True)
    mock_api.list_voice_notes = AsyncMock(return_value=[])
    cb = _cb(data="voice:list")
    await cb_voice_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_cb_voice_list_with_notes(mock_api: MagicMock):
    mock_api.check_feature_permission = AsyncMock(return_value=True)
    mock_api.list_voice_notes = AsyncMock(return_value=[
        {"pet_label": "Rex", "created_at_str": "01.01.2026", "transcription": "Test note"},
    ])
    cb = _cb(data="voice:list")
    await cb_voice_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.voice.api_client")
async def test_cb_voice_list_error(mock_api: MagicMock):
    mock_api.check_feature_permission = AsyncMock(return_value=True)
    mock_api.list_voice_notes = AsyncMock(side_effect=RuntimeError("fail"))
    cb = _cb(data="voice:list")
    await cb_voice_list(cb)
    cb.message.edit_text.assert_awaited_once()
