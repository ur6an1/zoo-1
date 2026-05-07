"""Tests for bot/bot/handlers/medical.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.handlers.medical import (
    cb_doc_add,
    cb_doc_pet,
    cb_doc_type,
    cb_docs_list,
    cb_documents,
    cb_med_menu,
    cb_vaccine_add,
    cb_vaccine_pet,
    cb_vaccines,
    cb_vaccines_list,
    cb_vet_add,
    cb_vet_pet,
    cb_vetvisits,
    cb_vetvisits_list,
    cb_weight,
    cb_weight_add,
    cb_weight_list,
    cb_weight_pet,
    doc_description,
    doc_photo,
    doc_photo_invalid,
    medical_menu,
    vaccine_date_done,
    vaccine_name,
    vaccine_next_date,
    vaccine_next_skip,
    vaccine_notes,
    vet_date,
    vet_diagnosis,
    vet_notes,
    vet_treatment,
    weight_value,
)


def _msg(user_id: int = 1, text: str = "") -> MagicMock:
    m = AsyncMock()
    m.from_user = MagicMock(id=user_id)
    m.text = text
    m.answer = AsyncMock()
    m.answer_document = AsyncMock()
    m.photo = None
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


# ── menus ──


@pytest.mark.asyncio
async def test_medical_menu():
    msg = _msg()
    await medical_menu(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_med_menu():
    cb = _cb()
    await cb_med_menu(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_vaccines():
    cb = _cb()
    await cb_vaccines(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_vetvisits():
    cb = _cb()
    await cb_vetvisits(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_weight():
    cb = _cb()
    await cb_weight(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_documents():
    cb = _cb()
    await cb_documents(cb)
    cb.message.edit_text.assert_awaited_once()


# ── vaccines ──


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_vaccine_add_no_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    state = _state()
    await cb_vaccine_add(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_vaccine_add_with_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb()
    state = _state()
    await cb_vaccine_add(cb, state)
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_vaccine_pet(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="pet:select_vaccine:1")
    state = _state()
    await cb_vaccine_pet(cb, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_vaccine_pet_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="pet:select_vaccine:1")
    state = _state()
    await cb_vaccine_pet(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_vaccine_name_valid():
    msg = _msg(text="Rabies")
    state = _state()
    await vaccine_name(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_vaccine_name_too_long():
    msg = _msg(text="V" * 201)
    state = _state()
    await vaccine_name(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_vaccine_date_done_valid():
    msg = _msg(text="15.03.2026")
    state = _state()
    await vaccine_date_done(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_vaccine_date_done_invalid():
    msg = _msg(text="bad")
    state = _state()
    await vaccine_date_done(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_vaccine_next_skip():
    cb = _cb(data="skip")
    state = _state()
    await vaccine_next_skip(cb, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_vaccine_next_date_valid():
    msg = _msg(text="15.03.2027")
    state = _state()
    await vaccine_next_date(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_vaccine_next_date_invalid():
    msg = _msg(text="bad")
    state = _state()
    await vaccine_next_date(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_vaccine_notes_handler(mock_api: MagicMock):
    mock_api.create_vaccination = AsyncMock(return_value={"id": 1})
    msg = _msg(text="ok")
    state = _state(data={
        "pet_id": 1, "vac_name": "Rabies",
        "date_done": "2026-03-15", "next_date": "2027-03-15",  # strings OK here: sent to API
    })
    await vaccine_notes(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_vaccine_notes_no_next(mock_api: MagicMock):
    mock_api.create_vaccination = AsyncMock(return_value={"id": 1})
    msg = _msg(text="-")
    state = _state(data={
        "pet_id": 1, "vac_name": "Rabies", "date_done": "2026-03-15",  # strings OK: sent to API
    })
    await vaccine_notes(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_vaccines_list_no_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    await cb_vaccines_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_vaccines_list_empty(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.list_vaccinations = AsyncMock(return_value=[])
    cb = _cb()
    await cb_vaccines_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_vaccines_list_with_data(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.list_vaccinations = AsyncMock(return_value=[
        {"name": "Rabies", "pet_id": 1,
         "date_done": __import__('datetime').date(2026, 1, 1),
         "next_date": __import__('datetime').date(2027, 1, 1)},
    ])
    cb = _cb()
    await cb_vaccines_list(cb)
    cb.message.edit_text.assert_awaited_once()


# ── vet visits ──


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_vet_add_no_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    state = _state()
    await cb_vet_add(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_vet_add_with_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb()
    state = _state()
    await cb_vet_add(cb, state)
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_vet_pet(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="pet:select_vetvisit:1")
    state = _state()
    await cb_vet_pet(cb, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_vet_date_valid():
    msg = _msg(text="15.03.2026")
    state = _state()
    await vet_date(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_vet_date_invalid():
    msg = _msg(text="bad")
    state = _state()
    await vet_date(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_vet_diagnosis():
    msg = _msg(text="Healthy")
    state = _state()
    await vet_diagnosis(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_vet_diagnosis_skip():
    msg = _msg(text="-")
    state = _state()
    await vet_diagnosis(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_vet_treatment():
    msg = _msg(text="Vitamins")
    state = _state()
    await vet_treatment(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_vet_notes_handler(mock_api: MagicMock):
    mock_api.create_vet_visit = AsyncMock(return_value={"id": 1})
    msg = _msg(text="ok")
    state = _state(data={
        "pet_id": 1, "visit_date": "2026-03-15",  # string OK: sent to API
        "diagnosis": "Healthy", "treatment": "None",
    })
    await vet_notes(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_vetvisits_list_empty(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.list_vet_visits = AsyncMock(return_value=[])
    cb = _cb()
    await cb_vetvisits_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_vetvisits_list_with_data(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.list_vet_visits = AsyncMock(return_value=[
        {"pet_id": 1, "visit_date": __import__('datetime').date(2026, 1, 1), "diagnosis": "OK", "treatment": ""},
    ])
    cb = _cb()
    await cb_vetvisits_list(cb)
    cb.message.edit_text.assert_awaited_once()


# ── weight ──


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_weight_add_no_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    state = _state()
    await cb_weight_add(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_weight_add_with_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb()
    state = _state()
    await cb_weight_add(cb, state)
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_weight_pet(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="pet:select_weight:1")
    state = _state()
    await cb_weight_pet(cb, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_weight_value_valid(mock_api: MagicMock):
    mock_api.create_weight_record = AsyncMock(return_value={
        "id": 1, "recorded_at": __import__('datetime').date(2026, 1, 1),
    })
    mock_api.get_pet = AsyncMock(return_value=PET)
    mock_api.update_pet = AsyncMock(return_value=PET)
    msg = _msg(text="4.5")
    state = _state(data={"pet_id": 1})
    await weight_value(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_weight_value_invalid():
    msg = _msg(text="abc")
    state = _state(data={"pet_id": 1})
    await weight_value(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_weight_list_empty(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.list_weight_records = AsyncMock(return_value=[])
    cb = _cb()
    await cb_weight_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_weight_list_with_data(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.list_weight_records = AsyncMock(return_value=[
        {"pet_id": 1, "weight": 4.5, "recorded_at": __import__('datetime').date(2026, 1, 1)},
    ])
    cb = _cb()
    await cb_weight_list(cb)
    cb.message.edit_text.assert_awaited_once()


# ── documents ──


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_doc_add_no_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    state = _state()
    await cb_doc_add(cb, state)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_doc_add_with_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    cb = _cb()
    state = _state()
    await cb_doc_add(cb, state)
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_doc_pet(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="pet:select_document:1")
    state = _state()
    await cb_doc_pet(cb, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_doc_type():
    cb = _cb(data="doc_type:passport")
    state = _state()
    await cb_doc_type(cb, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_doc_photo_handler():
    msg = _msg()
    photo_mock = MagicMock(file_id="photo_abc")
    msg.photo = [photo_mock]
    state = _state()
    await doc_photo(msg, state)
    state.update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_doc_photo_invalid_handler():
    msg = _msg(text="not a photo")
    await doc_photo_invalid(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_doc_description_handler(mock_api: MagicMock):
    mock_api.create_document = AsyncMock(return_value={"id": 1})
    msg = _msg(text="Passport scan")
    state = _state(data={"pet_id": 1, "doc_type": "passport", "file_id": "photo_abc"})
    await doc_description(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_docs_list_no_pets(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    await cb_docs_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_docs_list_empty(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.list_documents = AsyncMock(return_value=[])
    cb = _cb()
    await cb_docs_list(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.medical.api_client")
async def test_cb_docs_list_with_data(mock_api: MagicMock):
    mock_api.list_pets = AsyncMock(return_value=[PET])
    mock_api.list_documents = AsyncMock(return_value=[
        {"id": 1, "pet_id": 1, "doc_type": "passport", "description": "scan", "file_id": "abc"},
    ])
    cb = _cb()
    await cb_docs_list(cb)
    cb.message.answer_photo.assert_awaited_once()
    cb.message.answer.assert_awaited_once()
