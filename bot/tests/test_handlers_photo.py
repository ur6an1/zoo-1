"""Tests for bot.handlers.photo — photo recognition, nutrition, symptoms handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.photo import (
    cb_nutrition_start,
    cb_photo_food,
    cb_photo_menu,
    cb_photo_pet,
    cb_symptoms_start,
    nutrition_not_photo,
    nutrition_pet_chosen,
    nutrition_start,
    photo_menu,
    symptoms_not_text,
    symptoms_pet_chosen,
    symptoms_start,
    _pet_info_str,
)

PET = {"id": 1, "name": "Rex", "species": "собака", "breed": "Лабрадор",
       "birth_date": None, "weight": 5.0, "age_str": "2 года",
       "species_emoji": "🐶"}


def _msg(text: str = "📷 Распознать фото") -> MagicMock:
    m = MagicMock()
    m.text = text
    m.from_user = MagicMock(id=1)
    m.answer = AsyncMock()
    return m


def _cb(data: str = "photo:menu") -> MagicMock:
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


# ── helper ──


def test_pet_info_str():
    result = _pet_info_str(PET)
    assert "собака" in result
    assert "Rex" in result


# ── photo_menu ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_photo_menu_ai_not_ok(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    msg = _msg()
    state = _state()
    await photo_menu(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_photo_menu_ok(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    msg = _msg()
    state = _state()
    await photo_menu(msg, state)
    msg.answer.assert_awaited_once()


# ── cb_photo_menu ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_cb_photo_menu_ai_not_ok(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    cb = _cb()
    state = _state()
    await cb_photo_menu(cb, state)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_cb_photo_menu_ok(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    cb = _cb()
    state = _state()
    await cb_photo_menu(cb, state)
    cb.message.edit_text.assert_awaited_once()


# ── cb_photo_pet ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_cb_photo_pet_ai_not_ok(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    cb = _cb(data="photo:pet")
    state = _state()
    await cb_photo_pet(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_cb_photo_pet_ok(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    cb = _cb(data="photo:pet")
    state = _state()
    await cb_photo_pet(cb, state)
    state.update_data.assert_awaited_once()


# ── cb_photo_food ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_cb_photo_food_ai_not_ok(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    cb = _cb(data="photo:food")
    state = _state()
    await cb_photo_food(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_cb_photo_food_ok(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    cb = _cb(data="photo:food")
    state = _state()
    await cb_photo_food(cb, state)
    state.update_data.assert_awaited_once()


# ── nutrition_start ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_nutrition_start_ai_not_ok(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    msg = _msg(text="🥗 Подбор питания")
    state = _state()
    await nutrition_start(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_nutrition_start_no_pets(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[])
    msg = _msg(text="🥗 Подбор питания")
    state = _state()
    await nutrition_start(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_nutrition_start_with_pets(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[PET])
    msg = _msg(text="🥗 Подбор питания")
    state = _state()
    await nutrition_start(msg, state)
    state.set_state.assert_awaited_once()


# ── cb_nutrition_start ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_cb_nutrition_start_ai_not_ok(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    cb = _cb(data="ai:nutrition")
    state = _state()
    await cb_nutrition_start(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_cb_nutrition_start_no_pets(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb(data="ai:nutrition")
    state = _state()
    await cb_nutrition_start(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_cb_nutrition_start_with_pets(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb(data="ai:nutrition")
    state = _state()
    await cb_nutrition_start(cb, state)
    state.set_state.assert_awaited_once()


# ── nutrition_pet_chosen ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_nutrition_pet_chosen_invalid(mock_api: MagicMock):
    cb = _cb(data="pet:select_nutrition:bad")
    state = _state()
    await nutrition_pet_chosen(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_nutrition_pet_chosen_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="pet:select_nutrition:1")
    state = _state()
    await nutrition_pet_chosen(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_nutrition_pet_chosen_ok(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="pet:select_nutrition:1")
    state = _state()
    await nutrition_pet_chosen(cb, state)
    state.set_state.assert_awaited_once()
    state.update_data.assert_awaited_once()


# ── nutrition_not_photo ──


@pytest.mark.asyncio
async def test_nutrition_not_photo():
    msg = _msg(text="text not photo")
    await nutrition_not_photo(msg)
    msg.answer.assert_awaited_once()


# ── symptoms_start ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_symptoms_start_ai_not_ok(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    msg = _msg(text="🩺 AI-консультант")
    state = _state()
    await symptoms_start(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_symptoms_start_no_pets(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[])
    msg = _msg(text="🩺 AI-консультант")
    state = _state()
    await symptoms_start(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_symptoms_start_with_pets(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[PET])
    msg = _msg(text="🩺 AI-консультант")
    state = _state()
    await symptoms_start(msg, state)
    state.set_state.assert_awaited_once()


# ── cb_symptoms_start ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_cb_symptoms_start_ai_not_ok(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    cb = _cb(data="ai:symptoms")
    state = _state()
    await cb_symptoms_start(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_cb_symptoms_start_no_pets(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb(data="ai:symptoms")
    state = _state()
    await cb_symptoms_start(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_cb_symptoms_start_with_pets(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb(data="ai:symptoms")
    state = _state()
    await cb_symptoms_start(cb, state)
    state.set_state.assert_awaited_once()


# ── symptoms_pet_chosen ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_symptoms_pet_chosen_invalid(mock_api: MagicMock):
    cb = _cb(data="pet:select_symptoms:bad")
    state = _state()
    await symptoms_pet_chosen(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_symptoms_pet_chosen_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="pet:select_symptoms:1")
    state = _state()
    await symptoms_pet_chosen(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_symptoms_pet_chosen_ok(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="pet:select_symptoms:1")
    state = _state()
    await symptoms_pet_chosen(cb, state)
    state.set_state.assert_awaited_once()
    state.update_data.assert_awaited_once()


# ── symptoms_not_text ──


@pytest.mark.asyncio
async def test_symptoms_not_text():
    msg = _msg()
    await symptoms_not_text(msg)
    msg.answer.assert_awaited_once()
