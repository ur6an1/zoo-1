"""Tests for bot/bot/handlers/pets.py."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.pets import (
    my_pets,
    cb_pet_list,
    cb_pet_view,
    cb_pet_add,
    pet_name,
    pet_species,
    pet_breed_skip,
    pet_breed,
    pet_birth_skip,
    pet_birth_date,
    pet_weight_skip,
    pet_weight,
    pet_photo_skip,
    pet_photo,
    pet_photo_invalid,
    _save_pet,
    cb_pet_edit,
    cb_edit_field,
    edit_name,
    edit_breed,
    edit_birth,
    edit_weight,
    edit_photo,
    cb_confirm_delete,
    cb_delete_pet,
    cb_pet_stats,
    cb_pet_export,
)


def _msg(user_id: int = 1, text: str = "") -> MagicMock:
    m = AsyncMock()
    m.from_user = MagicMock(id=user_id)
    m.text = text
    m.answer = AsyncMock()
    m.answer_document = AsyncMock()
    m.answer_photo = AsyncMock()
    m.photo = None
    return m


def _cb(user_id: int = 1, data: str = "") -> MagicMock:
    c = AsyncMock()
    c.from_user = MagicMock(id=user_id)
    c.data = data
    c.message = AsyncMock()
    c.message.edit_text = AsyncMock()
    c.message.answer = AsyncMock()
    c.message.answer_document = AsyncMock()
    c.message.answer_photo = AsyncMock()
    c.message.delete = AsyncMock()
    c.answer = AsyncMock()
    return c


def _state(data: dict | None = None) -> AsyncMock:
    s = AsyncMock()
    s.clear = AsyncMock()
    s.set_state = AsyncMock()
    s.update_data = AsyncMock()
    s.get_data = AsyncMock(return_value=data or {})
    return s


SAMPLE_PET = {
    "id": 1, "name": "Rex", "species": "Собака", "species_emoji": "🐶",
    "breed": "Лабрадор", "birth_date": None, "age_str": "2 года",
    "weight": 25.0, "photo_file_id": None,
}


# ── list/view ──


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_my_pets_empty(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.list_pets = AsyncMock(return_value=[])
    msg = _msg()
    await my_pets(msg)
    msg.answer.assert_awaited_once()
    assert "нет питомцев" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_my_pets_with_pets(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    mock_api.list_pets = AsyncMock(return_value=[SAMPLE_PET])
    msg = _msg()
    await my_pets(msg)
    msg.answer.assert_awaited_once()
    assert "1" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_list_empty(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb(data="pet:list")
    await cb_pet_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_list_with_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[SAMPLE_PET])
    cb = _cb(data="pet:list")
    await cb_pet_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_view_found_no_photo(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
    cb = _cb(data="pet:view:1")
    await cb_pet_view(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_view_found_with_photo(mock_api: MagicMock):
    pet_with_photo = {**SAMPLE_PET, "photo_file_id": "abc123"}
    mock_api.get_pet = AsyncMock(return_value=pet_with_photo)
    cb = _cb(data="pet:view:1")
    await cb_pet_view(cb)
    cb.message.answer_photo.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_view_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="pet:view:1")
    await cb_pet_view(cb)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_pet_view_bad_id():
    cb = _cb(data="pet:view:abc")
    await cb_pet_view(cb)
    cb.answer.assert_awaited_once()


# ── add pet flow ──


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_add_allowed(mock_api: MagicMock):
    mock_api.check_pet_limit = AsyncMock(return_value=(True, 3))
    mock_api.track_event = AsyncMock()
    cb = _cb(data="pet:add")
    state = _state()
    await cb_pet_add(cb, state)
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_add_limit_reached(mock_api: MagicMock):
    mock_api.check_pet_limit = AsyncMock(return_value=(False, 0))
    mock_api.get_plan_tier = AsyncMock(return_value="free")
    cb = _cb(data="pet:add")
    state = _state()
    await cb_pet_add(cb, state)
    cb.message.edit_text.assert_awaited_once()
    assert "лимит" in cb.message.edit_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_pet_name_valid():
    msg = _msg(text="Rex")
    state = _state()
    await pet_name(msg, state)
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_pet_name_too_long():
    msg = _msg(text="A" * 101)
    state = _state()
    await pet_name(msg, state)
    msg.answer.assert_awaited_once()
    assert "длинное" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_pet_name_empty():
    msg = _msg(text="")
    state = _state()
    await pet_name(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_pet_species():
    cb = _cb(data="species:Собака")
    state = _state()
    await pet_species(cb, state)
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_pet_breed_skip_handler():
    cb = _cb(data="skip")
    state = _state()
    await pet_breed_skip(cb, state)
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_pet_breed_valid():
    msg = _msg(text="Лабрадор")
    state = _state()
    await pet_breed(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_pet_breed_too_long():
    msg = _msg(text="B" * 101)
    state = _state()
    await pet_breed(msg, state)
    msg.answer.assert_awaited_once()
    assert "длинное" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_pet_birth_skip_handler():
    cb = _cb(data="skip")
    state = _state()
    await pet_birth_skip(cb, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_pet_birth_date_valid():
    msg = _msg(text="15.03.2020")
    state = _state()
    await pet_birth_date(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_pet_birth_date_invalid():
    msg = _msg(text="not_a_date")
    state = _state()
    await pet_birth_date(msg, state)
    msg.answer.assert_awaited_once()
    assert "формат" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_pet_weight_skip_handler():
    cb = _cb(data="skip")
    state = _state()
    await pet_weight_skip(cb, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_pet_weight_valid():
    msg = _msg(text="4.5")
    state = _state()
    await pet_weight(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_pet_weight_invalid():
    msg = _msg(text="abc")
    state = _state()
    await pet_weight(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_pet_photo_skip_handler(mock_api: MagicMock):
    mock_api.create_pet = AsyncMock(return_value=SAMPLE_PET)
    mock_api.get_pet_count = AsyncMock(return_value=1)
    mock_api.track_event = AsyncMock()
    cb = _cb(data="skip")
    state = _state(data={"name": "Rex", "species": "Собака", "breed": ""})
    await pet_photo_skip(cb, state)
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_pet_photo_handler(mock_api: MagicMock):
    mock_api.create_pet = AsyncMock(return_value=SAMPLE_PET)
    mock_api.get_pet_count = AsyncMock(return_value=2)
    mock_api.track_event = AsyncMock()
    msg = _msg()
    photo_mock = MagicMock(file_id="photo_abc")
    msg.photo = [photo_mock]
    state = _state(data={"name": "Rex", "species": "Собака", "breed": "Lab"})
    await pet_photo(msg, state)
    mock_api.create_pet.assert_awaited_once()


@pytest.mark.asyncio
async def test_pet_photo_invalid_handler():
    msg = _msg(text="not a photo")
    await pet_photo_invalid(msg)
    msg.answer.assert_awaited_once()
    assert "фото" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_save_pet(mock_api: MagicMock):
    mock_api.create_pet = AsyncMock(return_value=SAMPLE_PET)
    mock_api.get_pet_count = AsyncMock(return_value=1)
    mock_api.track_event = AsyncMock()
    msg = _msg()
    state = _state(data={
        "name": "Rex", "species": "Собака", "breed": "Lab",
        "birth_date": "2020-01-15", "weight": 25.0, "photo_file_id": None,
    })
    await _save_pet(msg, state, 42)
    mock_api.create_pet.assert_awaited_once()
    assert msg.answer.await_count == 2


# ── edit ──


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_edit_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
    cb = _cb(data="pet:edit:1")
    await cb_pet_edit(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_edit_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="pet:edit:1")
    await cb_pet_edit(cb)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_edit_field_name(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
    cb = _cb(data="pet:edit_field:name:1")
    state = _state()
    await cb_edit_field(cb, state)
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_edit_field_bad_params(mock_api: MagicMock):
    cb = _cb(data="pet:edit_field:")
    state = _state()
    await cb_edit_field(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_edit_name_success(mock_api: MagicMock):
    mock_api.update_pet = AsyncMock(return_value=SAMPLE_PET)
    msg = _msg(text="Max")
    state = _state(data={"edit_pet_id": 1})
    await edit_name(msg, state)
    msg.answer.assert_awaited_once()
    assert "Max" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_edit_name_too_long():
    msg = _msg(text="A" * 101)
    state = _state(data={"edit_pet_id": 1})
    await edit_name(msg, state)
    msg.answer.assert_awaited_once()
    assert "символов" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_edit_name_pet_not_found(mock_api: MagicMock):
    mock_api.update_pet = AsyncMock(return_value=None)
    msg = _msg(text="Max")
    state = _state(data={"edit_pet_id": 1})
    await edit_name(msg, state)
    assert "не найден" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_edit_breed_success(mock_api: MagicMock):
    mock_api.update_pet = AsyncMock(return_value=SAMPLE_PET)
    msg = _msg(text="Пудель")
    state = _state(data={"edit_pet_id": 1})
    await edit_breed(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_edit_birth_success(mock_api: MagicMock):
    mock_api.update_pet = AsyncMock(return_value=SAMPLE_PET)
    msg = _msg(text="15.03.2020")
    state = _state(data={"edit_pet_id": 1})
    await edit_birth(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_edit_birth_invalid():
    msg = _msg(text="bad_date")
    state = _state(data={"edit_pet_id": 1})
    await edit_birth(msg, state)
    assert "формат" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_edit_weight_success(mock_api: MagicMock):
    mock_api.update_pet = AsyncMock(return_value=SAMPLE_PET)
    msg = _msg(text="5.5")
    state = _state(data={"edit_pet_id": 1})
    await edit_weight(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_edit_weight_invalid():
    msg = _msg(text="abc")
    state = _state(data={"edit_pet_id": 1})
    await edit_weight(msg, state)
    assert "формат" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_edit_photo_success(mock_api: MagicMock):
    mock_api.update_pet = AsyncMock(return_value=SAMPLE_PET)
    msg = _msg()
    photo_mock = MagicMock(file_id="new_photo")
    msg.photo = [photo_mock]
    state = _state(data={"edit_pet_id": 1})
    await edit_photo(msg, state)
    msg.answer.assert_awaited_once()


# ── delete ──


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_confirm_delete(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
    cb = _cb(data="pet:confirm_delete:1")
    await cb_confirm_delete(cb)
    cb.message.edit_text.assert_awaited_once()
    assert "уверены" in cb.message.edit_text.call_args[0][0].lower()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_confirm_delete_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="pet:confirm_delete:1")
    await cb_confirm_delete(cb)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_delete_pet_success(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
    mock_api.delete_pet = AsyncMock(return_value=True)
    cb = _cb(data="pet:delete:1")
    await cb_delete_pet(cb)
    cb.message.edit_text.assert_awaited_once()
    assert "удалён" in cb.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_delete_pet_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="pet:delete:1")
    await cb_delete_pet(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_delete_pet_failed(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
    mock_api.delete_pet = AsyncMock(return_value=False)
    cb = _cb(data="pet:delete:1")
    await cb_delete_pet(cb)
    cb.message.edit_text.assert_awaited_once()


# ── stats ──


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_stats(mock_api: MagicMock):
    from datetime import date as dt_date

    mock_api.get_pet_stats = AsyncMock(return_value={
        "pet": SAMPLE_PET,
        "counts": {
            "vaccinations": 2, "vet_visits": 1, "weight_records": 3,
            "food_entries": 10, "water_entries": 5, "allergies": 0,
            "documents": 1, "active_reminders": 2,
        },
        "last_vaccination": {"date_done": dt_date(2025, 1, 1), "name": "Rabies"},
        "next_vaccination": {"next_date": dt_date(2026, 1, 1), "name": "Rabies"},
        "last_visit": {"visit_date": dt_date(2025, 6, 1)},
        "last_weight": {"weight": 25.0, "recorded_at": dt_date(2025, 6, 1)},
    })
    cb = _cb(data="pet:stats:1")
    await cb_pet_stats(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_stats_not_found(mock_api: MagicMock):
    mock_api.get_pet_stats = AsyncMock(return_value=None)
    cb = _cb(data="pet:stats:1")
    await cb_pet_stats(cb)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_stats_no_records(mock_api: MagicMock):
    mock_api.get_pet_stats = AsyncMock(return_value={
        "pet": SAMPLE_PET,
        "counts": {
            "vaccinations": 0, "vet_visits": 0, "weight_records": 0,
            "food_entries": 0, "water_entries": 0, "allergies": 0,
            "documents": 0, "active_reminders": 0,
        },
    })
    cb = _cb(data="pet:stats:1")
    await cb_pet_stats(cb)
    cb.message.edit_text.assert_awaited_once()


# ── export ──


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_export(mock_api: MagicMock):
    from datetime import date as dt_date

    mock_api.get_pet_export = AsyncMock(return_value={
        "pet": SAMPLE_PET,
        "vaccinations": [{"date_done": dt_date(2025, 1, 1), "name": "Rabies", "next_date": dt_date(2026, 1, 1), "notes": "ok"}],
        "vet_visits": [{"visit_date": dt_date(2025, 6, 1), "diagnosis": "Healthy", "treatment": "None"}],
        "weight_records": [{"recorded_at": dt_date(2025, 6, 1), "weight": 25.0}],
        "allergies": [{"allergen": "Chicken", "reaction": "Itching"}],
    })
    cb = _cb(data="pet:export:1")
    await cb_pet_export(cb)
    cb.message.answer_document.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.pets.api_client")
async def test_cb_pet_export_not_found(mock_api: MagicMock):
    mock_api.get_pet_export = AsyncMock(return_value=None)
    cb = _cb(data="pet:export:1")
    await cb_pet_export(cb)
    cb.answer.assert_awaited_once()
