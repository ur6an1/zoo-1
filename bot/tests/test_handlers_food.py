"""Tests for bot/bot/handlers/food.py."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.food import (
    food_menu,
    cb_food_menu,
    cb_food_meal,
    cb_food_water,
    cb_food_allergies,
    cb_food_analytics,
    cb_meal_add,
    cb_meal_pet,
    meal_name,
    meal_portion,
    meal_notes,
    cb_meal_list,
    cb_water_add,
    cb_water_pet,
    water_amount,
    cb_water_list,
    cb_allergy_add,
    cb_allergy_pet,
    allergy_allergen,
    allergy_reaction,
    allergy_notes,
    cb_allergy_list,
    cb_allergy_delete,
    cb_meal_clear_confirm,
    cb_meal_clear,
    cb_water_clear_confirm,
    cb_water_clear,
    cb_food_today,
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
    c.message.answer_photo = AsyncMock()
    c.answer = AsyncMock()
    return c


def _state(data: dict | None = None) -> AsyncMock:
    s = AsyncMock()
    s.clear = AsyncMock()
    s.set_state = AsyncMock()
    s.update_data = AsyncMock()
    s.get_data = AsyncMock(return_value=data or {})
    return s


PET = {"id": 1, "name": "Rex", "species_emoji": "🐶"}


# ── menu ──


@pytest.mark.asyncio
async def test_food_menu():
    msg = _msg()
    await food_menu(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_food_menu():
    cb = _cb()
    await cb_food_menu(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_food_meal():
    cb = _cb()
    await cb_food_meal(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_food_water():
    cb = _cb()
    await cb_food_water(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_food_allergies():
    cb = _cb()
    await cb_food_allergies(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_food_analytics():
    cb = _cb()
    await cb_food_analytics(cb)
    cb.message.edit_text.assert_awaited_once()


# ── meals ──


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_meal_add_no_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    state = _state()
    await cb_meal_add(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_meal_add_with_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb()
    state = _state()
    await cb_meal_add(cb, state)
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_meal_pet(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="pet:select_food:1")
    state = _state()
    await cb_meal_pet(cb, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_meal_pet_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="pet:select_food:1")
    state = _state()
    await cb_meal_pet(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_meal_name_valid():
    msg = _msg(text="Chicken")
    state = _state()
    await meal_name(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_meal_name_too_long():
    msg = _msg(text="X" * 201)
    state = _state()
    await meal_name(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_meal_portion_text():
    msg = _msg(text="100 г")
    state = _state()
    await meal_portion(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_meal_portion_skip():
    msg = _msg(text="-")
    state = _state()
    await meal_portion(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_meal_notes_handler(mock_api: MagicMock):
    from datetime import datetime as _dt
    mock_api.create_food_entry = AsyncMock(return_value={"meal_time": _dt(2026, 1, 1, 12, 0)})
    msg = _msg(text="tasty")
    state = _state(data={"pet_id": 1, "food_name": "Chicken", "portion": "100g"})
    await meal_notes(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_meal_list_no_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    await cb_meal_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_meal_list_empty(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.list_food_entries = AsyncMock(return_value=[])
    cb = _cb()
    await cb_meal_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_meal_list_with_entries(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.list_food_entries = AsyncMock(return_value=[
        {"food_name": "Chicken", "pet_id": 1, "portion": "100g", "meal_time": __import__('datetime').datetime(2026, 1, 1, 12, 0)},
    ])
    cb = _cb()
    await cb_meal_list(cb)
    cb.message.edit_text.assert_awaited_once()


# ── water ──


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_water_add_no_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    state = _state()
    await cb_water_add(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_water_add_with_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb()
    state = _state()
    await cb_water_add(cb, state)
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_water_pet(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="pet:select_water:1")
    state = _state()
    await cb_water_pet(cb, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_water_amount_valid(mock_api: MagicMock):
    from datetime import datetime as _dt
    mock_api.create_water_entry = AsyncMock(return_value={"recorded_at": _dt(2026, 1, 1, 12, 0)})
    msg = _msg(text="150")
    state = _state(data={"pet_id": 1})
    await water_amount(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_water_amount_invalid():
    msg = _msg(text="abc")
    state = _state(data={"pet_id": 1})
    await water_amount(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_water_list_empty(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.list_water_entries = AsyncMock(return_value=[])
    cb = _cb()
    await cb_water_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_water_list_with_entries(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.list_water_entries = AsyncMock(return_value=[
        {"amount_ml": 150, "pet_id": 1, "recorded_at": __import__('datetime').datetime(2026, 1, 1, 12, 0)},
    ])
    cb = _cb()
    await cb_water_list(cb)
    cb.message.edit_text.assert_awaited_once()


# ── allergies ──


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_allergy_add_no_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    state = _state()
    await cb_allergy_add(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_allergy_add_with_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb()
    state = _state()
    await cb_allergy_add(cb, state)
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_allergy_pet(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="pet:select_allergy:1")
    state = _state()
    await cb_allergy_pet(cb, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_allergy_allergen_valid():
    msg = _msg(text="Chicken")
    state = _state()
    await allergy_allergen(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_allergy_allergen_too_long():
    msg = _msg(text="X" * 201)
    state = _state()
    await allergy_allergen(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_allergy_reaction_text():
    msg = _msg(text="Itching")
    state = _state()
    await allergy_reaction(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_allergy_reaction_skip():
    msg = _msg(text="-")
    state = _state()
    await allergy_reaction(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_allergy_notes_handler(mock_api: MagicMock):
    mock_api.create_allergy = AsyncMock(return_value={"id": 1})
    msg = _msg(text="severe")
    state = _state(data={"pet_id": 1, "allergen": "Chicken", "reaction": "Itching"})
    await allergy_notes(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_allergy_list_empty(mock_api: MagicMock):
    mock_api.list_allergies_by_user = AsyncMock(return_value=[])
    cb = _cb()
    await cb_allergy_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_allergy_list_with_items(mock_api: MagicMock):
    mock_api.list_allergies_by_user = AsyncMock(return_value=[
        {"id": 1, "allergen": "Chicken", "reaction": "Itching", "pet_id": 1},
    ])
    cb = _cb()
    await cb_allergy_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_allergy_delete(mock_api: MagicMock):
    mock_api.delete_allergy = AsyncMock(return_value=True)
    mock_api.list_allergies_by_user = AsyncMock(return_value=[])
    cb = _cb(data="food:allergy:del:1")
    await cb_allergy_delete(cb)
    cb.answer.assert_awaited()


# ── clear ──


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_meal_clear_confirm(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb()
    await cb_meal_clear_confirm(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_meal_clear(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.clear_food_entries = AsyncMock()
    cb = _cb()
    await cb_meal_clear(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_water_clear_confirm(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb()
    await cb_water_clear_confirm(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_water_clear(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.clear_water_entries = AsyncMock()
    cb = _cb()
    await cb_water_clear(cb)
    cb.message.edit_text.assert_awaited_once()


# ── daily summary ──


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_food_today_no_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    await cb_food_today(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.food.api_client")
async def test_cb_food_today_with_data(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.get_daily_summary = AsyncMock(return_value={
        "food_entries": [{"food_name": "Chicken", "portion": "100g", "meal_time": __import__('datetime').datetime(2026, 1, 1, 12, 0)}],
        "water_entries": [{"amount_ml": 150, "recorded_at": __import__('datetime').datetime(2026, 1, 1, 12, 0)}],
        "total_food": 1,
        "total_water_ml": 150,
    })
    cb = _cb()
    await cb_food_today(cb)
    cb.message.edit_text.assert_awaited_once()
