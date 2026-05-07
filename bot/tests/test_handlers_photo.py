"""Tests for bot.handlers.photo — photo recognition, nutrition, symptoms handlers."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.handlers.photo import (
    _pet_info_str,
    cb_nutrition_start,
    cb_photo_food,
    cb_photo_menu,
    cb_photo_pet,
    cb_symptoms_start,
    handle_photo,
    handle_voice_anywhere,
    nutrition_not_photo,
    nutrition_pet_chosen,
    nutrition_photo_received,
    nutrition_start,
    photo_menu,
    symptoms_not_text,
    symptoms_pet_chosen,
    symptoms_start,
    symptoms_text_received,
    symptoms_voice_received,
)

PET = {"id": 1, "name": "Rex", "species": "собака", "breed": "Лабрадор",
       "birth_date": None, "weight": 5.0, "age_str": "2 года",
       "species_emoji": "🐶"}


def _msg(text: str = "📷 Распознать фото") -> MagicMock:
    m = MagicMock()
    m.text = text
    m.from_user = MagicMock(id=1)
    m.chat = MagicMock(id=1)
    m.answer = AsyncMock()
    photo_obj = MagicMock()
    photo_obj.file_id = "file123"
    m.photo = [photo_obj]
    voice_obj = MagicMock()
    voice_obj.file_id = "voice123"
    m.voice = voice_obj
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


def _state(data: dict | None = None, current_state: str | None = None) -> MagicMock:
    s = MagicMock()
    s.clear = AsyncMock()
    s.set_state = AsyncMock()
    s.update_data = AsyncMock()
    s.get_data = AsyncMock(return_value=data or {})
    s.get_state = AsyncMock(return_value=current_state)
    return s


def _bot() -> MagicMock:
    bot = MagicMock()
    bot.send_chat_action = AsyncMock()
    file_mock = MagicMock()
    file_mock.file_path = "voice/file.ogg"
    bot.get_file = AsyncMock(return_value=file_mock)
    bot.download_file = AsyncMock(return_value=io.BytesIO(b"fakedata"))
    return bot


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


# ── nutrition_photo_received ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.analyze_food_for_pet", new_callable=AsyncMock, return_value="Good food")
@patch("bot.handlers.photo.api_client")
async def test_nutrition_photo_received_ok(mock_api, mock_analyze):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state(data={"nutrition_pet_info": "собака Rex"})
    await nutrition_photo_received(msg, state, bot)
    processing.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_nutrition_photo_received_ai_not_ok(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    msg = _msg()
    state = _state()
    bot = _bot()
    await nutrition_photo_received(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_nutrition_photo_received_limit(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(False, 0))
    msg = _msg()
    state = _state()
    bot = _bot()
    await nutrition_photo_received(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_nutrition_photo_received_download_error(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    bot.get_file = AsyncMock(side_effect=RuntimeError("download error"))
    state = _state()
    await nutrition_photo_received(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.analyze_food_for_pet", new_callable=AsyncMock, return_value=None)
@patch("bot.handlers.photo.api_client")
async def test_nutrition_photo_received_no_result(mock_api, mock_analyze):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state()
    await nutrition_photo_received(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.analyze_food_for_pet", new_callable=AsyncMock, return_value="x" * 5000)
@patch("bot.handlers.photo.api_client")
async def test_nutrition_photo_received_long_result(mock_api, mock_analyze):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state(data={"nutrition_pet_info": "собака Rex"})
    await nutrition_photo_received(msg, state, bot)
    processing.edit_text.assert_awaited_once()


# ── symptoms_text_received ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_symptoms_text_received_too_short(mock_api):
    msg = _msg(text="hi")
    state = _state()
    bot = _bot()
    await symptoms_text_received(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_symptoms_text_received_ai_not_ok(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    msg = _msg(text="My pet is sick and vomiting")
    state = _state(data={"symptoms_pet_info": "собака Rex"})
    bot = _bot()
    await symptoms_text_received(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_symptoms_text_received_limit(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(False, 0))
    msg = _msg(text="My pet is sick and vomiting")
    state = _state(data={"symptoms_pet_info": "собака Rex"})
    bot = _bot()
    await symptoms_text_received(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value="AI diagnosis")
@patch("bot.handlers.photo.api_client")
async def test_symptoms_text_received_ok(mock_api, mock_consult):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    msg = _msg(text="My pet is sick and vomiting")
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    state = _state(data={"symptoms_pet_info": "собака Rex"})
    bot = _bot()
    await symptoms_text_received(msg, state, bot)
    processing.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value=None)
@patch("bot.handlers.photo.api_client")
async def test_symptoms_text_received_no_result(mock_api, mock_consult):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    msg = _msg(text="My pet is sick and vomiting")
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    state = _state(data={"symptoms_pet_info": "собака Rex"})
    bot = _bot()
    await symptoms_text_received(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value="x" * 5000)
@patch("bot.handlers.photo.api_client")
async def test_symptoms_text_received_long_result(mock_api, mock_consult):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    msg = _msg(text="My pet is sick and vomiting heavily")
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    state = _state(data={"symptoms_pet_info": "собака Rex"})
    bot = _bot()
    await symptoms_text_received(msg, state, bot)
    processing.edit_text.assert_awaited_once()


# ── symptoms_voice_received ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_symptoms_voice_received_ai_not_ok(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    state = _state()
    bot = _bot()
    await symptoms_voice_received(msg, state, bot)
    processing.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_symptoms_voice_received_limit(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(False, 0))
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    state = _state()
    bot = _bot()
    await symptoms_voice_received(msg, state, bot)
    processing.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_symptoms_voice_received_download_error(mock_api):
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
    await symptoms_voice_received(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="")
@patch("bot.handlers.photo.api_client")
async def test_symptoms_voice_received_no_transcription(mock_api, mock_tr):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state()
    await symptoms_voice_received(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value="AI answer")
@patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="My pet is ill")
@patch("bot.handlers.photo.api_client")
async def test_symptoms_voice_received_ok(mock_api, mock_tr, mock_consult):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state(data={"symptoms_pet_info": "собака Rex"})
    await symptoms_voice_received(msg, state, bot)
    assert processing.edit_text.await_count >= 2


@pytest.mark.asyncio
@patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value=None)
@patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="My pet is ill")
@patch("bot.handlers.photo.api_client")
async def test_symptoms_voice_received_no_result(mock_api, mock_tr, mock_consult):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state(data={"symptoms_pet_info": "собака Rex"})
    await symptoms_voice_received(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


# ── handle_photo ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_handle_photo_protected_state(mock_api):
    msg = _msg()
    from bot.states.states import PetForm
    state = _state(current_state=PetForm.photo.state)
    bot = _bot()
    await handle_photo(msg, state, bot)
    msg.answer.assert_not_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_handle_photo_no_mode(mock_api):
    msg = _msg()
    state = _state(data={})
    bot = _bot()
    await handle_photo(msg, state, bot)
    msg.answer.assert_not_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_handle_photo_ai_not_ok(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    msg = _msg()
    state = _state(data={"photo_mode": "pet"})
    bot = _bot()
    await handle_photo(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_handle_photo_limit(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(False, 0))
    msg = _msg()
    state = _state(data={"photo_mode": "pet"})
    bot = _bot()
    await handle_photo(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_handle_photo_download_error(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    bot.get_file = AsyncMock(side_effect=RuntimeError("err"))
    state = _state(data={"photo_mode": "pet"})
    await handle_photo(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.analyze_pet_photo", new_callable=AsyncMock, return_value="A cute dog")
@patch("bot.handlers.photo.api_client")
async def test_handle_photo_pet_mode_ok(mock_api, mock_analyze):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state(data={"photo_mode": "pet"})
    await handle_photo(msg, state, bot)
    processing.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.analyze_food_photo", new_callable=AsyncMock, return_value="Good food")
@patch("bot.handlers.photo.api_client")
async def test_handle_photo_food_mode_ok(mock_api, mock_analyze):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state(data={"photo_mode": "food"})
    await handle_photo(msg, state, bot)
    processing.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.analyze_pet_photo", new_callable=AsyncMock, return_value=None)
@patch("bot.handlers.photo.api_client")
async def test_handle_photo_no_result(mock_api, mock_analyze):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state(data={"photo_mode": "pet"})
    await handle_photo(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


# ── handle_voice_anywhere ──


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_handle_voice_anywhere_protected_state(mock_api):
    msg = _msg()
    from bot.states.states import VoiceNoteForm
    state = _state(current_state=VoiceNoteForm.waiting_voice.state)
    bot = _bot()
    await handle_voice_anywhere(msg, state, bot)
    msg.answer.assert_not_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_handle_voice_anywhere_ai_not_ok(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    msg = _msg()
    state = _state()
    bot = _bot()
    await handle_voice_anywhere(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_handle_voice_anywhere_limit(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(False, 0))
    msg = _msg()
    state = _state()
    bot = _bot()
    await handle_voice_anywhere(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.api_client")
async def test_handle_voice_anywhere_download_error(mock_api):
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
    await handle_voice_anywhere(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="")
@patch("bot.handlers.photo.api_client")
async def test_handle_voice_anywhere_no_transcription(mock_api, mock_tr):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state()
    await handle_voice_anywhere(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value="AI says ok")
@patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="My pet problem")
@patch("bot.handlers.photo.api_client")
async def test_handle_voice_anywhere_ok_with_pets(mock_api, mock_tr, mock_consult):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.list_pets = AsyncMock(return_value=[PET])
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state()
    await handle_voice_anywhere(msg, state, bot)
    assert processing.edit_text.await_count >= 2


@pytest.mark.asyncio
@patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value="AI says ok")
@patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="My pet problem")
@patch("bot.handlers.photo.api_client")
async def test_handle_voice_anywhere_ok_no_pets(mock_api, mock_tr, mock_consult):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.list_pets = AsyncMock(return_value=[])
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state()
    await handle_voice_anywhere(msg, state, bot)
    assert processing.edit_text.await_count >= 2


@pytest.mark.asyncio
@patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value=None)
@patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="My pet problem")
@patch("bot.handlers.photo.api_client")
async def test_handle_voice_anywhere_no_result(mock_api, mock_tr, mock_consult):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    mock_api.list_pets = AsyncMock(return_value=[PET])
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state()
    await handle_voice_anywhere(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()
