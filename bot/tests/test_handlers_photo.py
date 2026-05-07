"""Tests for bot.handlers.photo — photo recognition, nutrition, symptoms AI."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.handlers.photo import (
    _no_ai_message,
    _pet_info_str,
    cb_photo_food,
    cb_photo_menu,
    cb_photo_pet,
    cb_nutrition_start,
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
from bot.states.states import NutritionForm, SymptomsForm


SAMPLE_PET = {
    "id": 1,
    "name": "Барсик",
    "species": "Кот",
    "species_emoji": "🐱",
    "breed": "Мейн-кун",
    "birth_date": None,
    "age_str": "2 года",
    "weight": 5.0,
}


# ── helpers ──────────────────────────────────────────


class TestHelpers:
    def test_no_ai_message(self):
        assert "AI-функции временно недоступны" in _no_ai_message()

    def test_pet_info_str_full(self):
        result = _pet_info_str(SAMPLE_PET)
        assert "Кот" in result
        assert "Барсик" in result
        assert "Мейн-кун" in result
        assert "5.0 кг" in result

    def test_pet_info_str_minimal(self):
        result = _pet_info_str({"species": "Собака", "name": "Рекс"})
        assert "Собака" in result
        assert "Рекс" in result


# ── photo menu ───────────────────────────────────────


class TestPhotoMenu:
    @patch("bot.handlers.photo.api_client")
    async def test_photo_menu_ok(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        await photo_menu(mock_message, fsm_context)
        mock_message.answer.assert_awaited()
        text = mock_message.answer.call_args[0][0]
        assert "Распознавание фото" in text

    @patch("bot.handlers.photo.api_client")
    async def test_photo_menu_ai_down(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await photo_menu(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.photo.api_client")
    async def test_cb_photo_menu_ok(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        await cb_photo_menu(mock_callback, fsm_context)
        mock_callback.message.edit_text.assert_awaited()

    @patch("bot.handlers.photo.api_client")
    async def test_cb_photo_menu_ai_down(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await cb_photo_menu(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "недоступны" in text


# ── photo pet / food mode ────────────────────────────


class TestPhotoModes:
    @patch("bot.handlers.photo.api_client")
    async def test_cb_photo_pet_ok(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        await cb_photo_pet(mock_callback, fsm_context)
        data = await fsm_context.get_data()
        assert data["photo_mode"] == "pet"

    @patch("bot.handlers.photo.api_client")
    async def test_cb_photo_pet_ai_down(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await cb_photo_pet(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.photo.api_client")
    async def test_cb_photo_food_ok(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        await cb_photo_food(mock_callback, fsm_context)
        data = await fsm_context.get_data()
        assert data["photo_mode"] == "food"

    @patch("bot.handlers.photo.api_client")
    async def test_cb_photo_food_ai_down(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await cb_photo_food(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "недоступны" in text


# ── nutrition FSM ────────────────────────────────────


class TestNutritionStart:
    @patch("bot.handlers.photo.api_client")
    async def test_start_ok(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.list_pets = AsyncMock(return_value=[SAMPLE_PET])
        await nutrition_start(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == NutritionForm.choosing_pet

    @patch("bot.handlers.photo.api_client")
    async def test_start_no_ai(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await nutrition_start(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.photo.api_client")
    async def test_start_no_pets(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.list_pets = AsyncMock(return_value=[])
        await nutrition_start(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "нет питомцев" in text

    @patch("bot.handlers.photo.api_client")
    async def test_cb_start_ok(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.list_pets = AsyncMock(return_value=[SAMPLE_PET])
        await cb_nutrition_start(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == NutritionForm.choosing_pet

    @patch("bot.handlers.photo.api_client")
    async def test_cb_start_no_ai(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await cb_nutrition_start(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.photo.api_client")
    async def test_cb_start_no_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_nutrition_start(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "нет питомцев" in text


class TestNutritionPetChosen:
    @patch("bot.handlers.photo.api_client")
    async def test_pet_chosen_ok(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_nutrition:1"
        mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
        await fsm_context.set_state(NutritionForm.choosing_pet)
        await nutrition_pet_chosen(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == NutritionForm.waiting_photo

    @patch("bot.handlers.photo.api_client")
    async def test_pet_chosen_invalid_id(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_nutrition:abc"
        await nutrition_pet_chosen(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.photo.api_client")
    async def test_pet_chosen_not_found(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_nutrition:999"
        mock_api.get_pet = AsyncMock(return_value=None)
        await nutrition_pet_chosen(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()


class TestNutritionPhotoReceived:
    @patch("bot.handlers.photo.analyze_food_for_pet", new_callable=AsyncMock, return_value="Рекомендации")
    @patch("bot.handlers.photo.api_client")
    async def test_photo_ok(self, mock_api, mock_vision, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        await fsm_context.set_state(NutritionForm.waiting_photo)
        await fsm_context.update_data(nutrition_pet_info="Кот Барсик")

        bot = AsyncMock()
        file_mock = MagicMock()
        file_mock.file_path = "photos/file.jpg"
        bot.get_file = AsyncMock(return_value=file_mock)
        bot.download_file = AsyncMock(return_value=io.BytesIO(b"image"))
        bot.send_chat_action = AsyncMock()

        photo = MagicMock()
        photo.file_id = "abc123"
        mock_message.photo = [photo]

        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)

        await nutrition_photo_received(mock_message, fsm_context, bot)
        processing_msg.edit_text.assert_awaited()

    @patch("bot.handlers.photo.api_client")
    async def test_photo_ai_down(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await fsm_context.set_state(NutritionForm.waiting_photo)
        await fsm_context.update_data(nutrition_pet_info="info")
        bot = AsyncMock()
        await nutrition_photo_received(mock_message, fsm_context, bot)
        text = mock_message.answer.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.photo.api_client")
    async def test_photo_limit_exceeded(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(False, 0))
        await fsm_context.set_state(NutritionForm.waiting_photo)
        await fsm_context.update_data(nutrition_pet_info="info")
        bot = AsyncMock()
        await nutrition_photo_received(mock_message, fsm_context, bot)
        text = mock_message.answer.call_args[0][0]
        assert "лимит" in text

    @patch("bot.handlers.photo.api_client")
    async def test_photo_download_error(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_api.refund_ai_limit = AsyncMock()
        await fsm_context.set_state(NutritionForm.waiting_photo)
        await fsm_context.update_data(nutrition_pet_info="info")

        bot = AsyncMock()
        bot.get_file = AsyncMock(side_effect=Exception("download fail"))
        bot.send_chat_action = AsyncMock()
        photo = MagicMock()
        photo.file_id = "abc"
        mock_message.photo = [photo]
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)

        await nutrition_photo_received(mock_message, fsm_context, bot)
        mock_api.refund_ai_limit.assert_awaited_once()

    async def test_nutrition_not_photo(self, mock_message):
        await nutrition_not_photo(mock_message)
        text = mock_message.answer.call_args[0][0]
        assert "фото корма" in text


# ── symptoms FSM ─────────────────────────────────────


class TestSymptomsStart:
    @patch("bot.handlers.photo.api_client")
    async def test_start_ok(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.list_pets = AsyncMock(return_value=[SAMPLE_PET])
        await symptoms_start(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == SymptomsForm.choosing_pet

    @patch("bot.handlers.photo.api_client")
    async def test_start_no_ai(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await symptoms_start(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.photo.api_client")
    async def test_start_no_pets(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.list_pets = AsyncMock(return_value=[])
        await symptoms_start(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "нет питомцев" in text

    @patch("bot.handlers.photo.api_client")
    async def test_cb_start_ok(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.list_pets = AsyncMock(return_value=[SAMPLE_PET])
        await cb_symptoms_start(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == SymptomsForm.choosing_pet

    @patch("bot.handlers.photo.api_client")
    async def test_cb_start_no_ai(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await cb_symptoms_start(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.photo.api_client")
    async def test_cb_start_no_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_symptoms_start(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "нет питомцев" in text


class TestSymptomsPetChosen:
    @patch("bot.handlers.photo.api_client")
    async def test_pet_chosen_ok(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_symptoms:1"
        mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
        await fsm_context.set_state(SymptomsForm.choosing_pet)
        await symptoms_pet_chosen(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == SymptomsForm.waiting_text

    @patch("bot.handlers.photo.api_client")
    async def test_pet_chosen_invalid(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_symptoms:abc"
        await symptoms_pet_chosen(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.photo.api_client")
    async def test_pet_chosen_not_found(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_symptoms:999"
        mock_api.get_pet = AsyncMock(return_value=None)
        await symptoms_pet_chosen(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()


class TestSymptomsTextReceived:
    @patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value="Рекомендация")
    @patch("bot.handlers.photo.api_client")
    async def test_text_ok(self, mock_api, mock_consult, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_message.text = "Кот не ест второй день"
        await fsm_context.set_state(SymptomsForm.waiting_text)
        await fsm_context.update_data(symptoms_pet_info="Кот Барсик")

        bot = AsyncMock()
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)

        await symptoms_text_received(mock_message, fsm_context, bot)
        processing_msg.edit_text.assert_awaited()

    @patch("bot.handlers.photo.api_client")
    async def test_text_too_short(self, mock_api, mock_message, fsm_context):
        mock_message.text = "ab"
        await fsm_context.set_state(SymptomsForm.waiting_text)
        bot = AsyncMock()
        await symptoms_text_received(mock_message, fsm_context, bot)
        text = mock_message.answer.call_args[0][0]
        assert "подробнее" in text

    @patch("bot.handlers.photo.api_client")
    async def test_text_ai_down(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        mock_message.text = "Собака хромает"
        await fsm_context.set_state(SymptomsForm.waiting_text)
        await fsm_context.update_data(symptoms_pet_info="info")
        bot = AsyncMock()
        await symptoms_text_received(mock_message, fsm_context, bot)
        text = mock_message.answer.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.photo.api_client")
    async def test_text_limit(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(False, 0))
        mock_message.text = "Кот чихает"
        await fsm_context.set_state(SymptomsForm.waiting_text)
        await fsm_context.update_data(symptoms_pet_info="info")
        bot = AsyncMock()
        await symptoms_text_received(mock_message, fsm_context, bot)
        text = mock_message.answer.call_args[0][0]
        assert "лимит" in text

    @patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value=None)
    @patch("bot.handlers.photo.api_client")
    async def test_text_ai_no_result(self, mock_api, mock_consult, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_api.refund_ai_limit = AsyncMock()
        mock_message.text = "Собака вялая"
        await fsm_context.set_state(SymptomsForm.waiting_text)
        await fsm_context.update_data(symptoms_pet_info="info")
        bot = AsyncMock()
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)
        await symptoms_text_received(mock_message, fsm_context, bot)
        mock_api.refund_ai_limit.assert_awaited_once()


class TestSymptomsVoiceReceived:
    @patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value="Совет ветеринара")
    @patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="Кот хромает")
    @patch("bot.handlers.photo.api_client")
    async def test_voice_ok(self, mock_api, mock_transcribe, mock_consult, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        await fsm_context.set_state(SymptomsForm.waiting_text)
        await fsm_context.update_data(symptoms_pet_info="info")

        bot = AsyncMock()
        file_mock = MagicMock()
        file_mock.file_path = "voice/file.ogg"
        bot.get_file = AsyncMock(return_value=file_mock)
        bot.download_file = AsyncMock(return_value=io.BytesIO(b"voice"))
        bot.send_chat_action = AsyncMock()

        voice = MagicMock()
        voice.file_id = "voice123"
        mock_message.voice = voice

        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)

        await symptoms_voice_received(mock_message, fsm_context, bot)
        assert processing_msg.edit_text.await_count >= 1

    @patch("bot.handlers.photo.api_client")
    async def test_voice_ai_down(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await fsm_context.set_state(SymptomsForm.waiting_text)
        bot = AsyncMock()
        voice = MagicMock()
        voice.file_id = "v1"
        mock_message.voice = voice
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)
        await symptoms_voice_received(mock_message, fsm_context, bot)
        text = processing_msg.edit_text.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="ab")
    @patch("bot.handlers.photo.api_client")
    async def test_voice_transcription_too_short(self, mock_api, mock_transcribe, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_api.refund_ai_limit = AsyncMock()
        await fsm_context.set_state(SymptomsForm.waiting_text)
        bot = AsyncMock()
        file_mock = MagicMock()
        file_mock.file_path = "voice/file.ogg"
        bot.get_file = AsyncMock(return_value=file_mock)
        bot.download_file = AsyncMock(return_value=io.BytesIO(b"voice"))
        bot.send_chat_action = AsyncMock()
        voice = MagicMock()
        voice.file_id = "v1"
        mock_message.voice = voice
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)
        await symptoms_voice_received(mock_message, fsm_context, bot)
        mock_api.refund_ai_limit.assert_awaited_once()

    @patch("bot.handlers.photo.api_client")
    async def test_voice_download_error(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_api.refund_ai_limit = AsyncMock()
        await fsm_context.set_state(SymptomsForm.waiting_text)
        bot = AsyncMock()
        bot.get_file = AsyncMock(side_effect=Exception("err"))
        bot.send_chat_action = AsyncMock()
        voice = MagicMock()
        voice.file_id = "v1"
        mock_message.voice = voice
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)
        await symptoms_voice_received(mock_message, fsm_context, bot)
        mock_api.refund_ai_limit.assert_awaited_once()

    async def test_symptoms_not_text(self, mock_message):
        await symptoms_not_text(mock_message)
        mock_message.answer.assert_awaited()


# ── handle_photo (general) ───────────────────────────


class TestHandlePhoto:
    @patch("bot.handlers.photo.analyze_pet_photo", new_callable=AsyncMock, return_value="Это кот")
    @patch("bot.handlers.photo.api_client")
    async def test_photo_pet_mode(self, mock_api, mock_vision, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        await fsm_context.update_data(photo_mode="pet")

        bot = AsyncMock()
        file_mock = MagicMock()
        file_mock.file_path = "photos/file.jpg"
        bot.get_file = AsyncMock(return_value=file_mock)
        bot.download_file = AsyncMock(return_value=io.BytesIO(b"img"))
        bot.send_chat_action = AsyncMock()

        photo = MagicMock()
        photo.file_id = "ph1"
        mock_message.photo = [photo]
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)

        await handle_photo(mock_message, fsm_context, bot)
        processing_msg.edit_text.assert_awaited()

    @patch("bot.handlers.photo.analyze_food_photo", new_callable=AsyncMock, return_value="Корм Royal Canin")
    @patch("bot.handlers.photo.api_client")
    async def test_photo_food_mode(self, mock_api, mock_vision, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        await fsm_context.update_data(photo_mode="food")

        bot = AsyncMock()
        file_mock = MagicMock()
        file_mock.file_path = "photos/file.jpg"
        bot.get_file = AsyncMock(return_value=file_mock)
        bot.download_file = AsyncMock(return_value=io.BytesIO(b"img"))
        bot.send_chat_action = AsyncMock()

        photo = MagicMock()
        photo.file_id = "ph2"
        mock_message.photo = [photo]
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)

        await handle_photo(mock_message, fsm_context, bot)
        processing_msg.edit_text.assert_awaited()

    @patch("bot.handlers.photo.api_client")
    async def test_photo_no_mode(self, mock_api, mock_message, fsm_context):
        bot = AsyncMock()
        mock_message.photo = [MagicMock()]
        await handle_photo(mock_message, fsm_context, bot)
        mock_message.answer.assert_not_awaited()

    @patch("bot.handlers.photo.api_client")
    async def test_photo_protected_state(self, mock_api, mock_message, fsm_context):
        from bot.states.states import PetForm
        await fsm_context.set_state(PetForm.photo)
        bot = AsyncMock()
        mock_message.photo = [MagicMock()]
        await handle_photo(mock_message, fsm_context, bot)
        mock_message.answer.assert_not_awaited()

    @patch("bot.handlers.photo.api_client")
    async def test_photo_ai_down(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await fsm_context.update_data(photo_mode="pet")
        bot = AsyncMock()
        mock_message.photo = [MagicMock()]
        await handle_photo(mock_message, fsm_context, bot)
        text = mock_message.answer.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.photo.api_client")
    async def test_photo_limit(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(False, 0))
        await fsm_context.update_data(photo_mode="pet")
        bot = AsyncMock()
        mock_message.photo = [MagicMock()]
        await handle_photo(mock_message, fsm_context, bot)
        text = mock_message.answer.call_args[0][0]
        assert "лимит" in text

    @patch("bot.handlers.photo.analyze_pet_photo", new_callable=AsyncMock, return_value=None)
    @patch("bot.handlers.photo.api_client")
    async def test_photo_no_result(self, mock_api, mock_vision, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_api.refund_ai_limit = AsyncMock()
        await fsm_context.update_data(photo_mode="pet")

        bot = AsyncMock()
        file_mock = MagicMock()
        file_mock.file_path = "p.jpg"
        bot.get_file = AsyncMock(return_value=file_mock)
        bot.download_file = AsyncMock(return_value=io.BytesIO(b"img"))
        bot.send_chat_action = AsyncMock()

        photo = MagicMock()
        photo.file_id = "ph"
        mock_message.photo = [photo]
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)

        await handle_photo(mock_message, fsm_context, bot)
        mock_api.refund_ai_limit.assert_awaited_once()


# ── handle_voice_anywhere ────────────────────────────


class TestHandleVoiceAnywhere:
    @patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value="Совет")
    @patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="Кот болеет")
    @patch("bot.handlers.photo.api_client")
    async def test_voice_ok_with_pets(self, mock_api, mock_tr, mock_consult, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_api.list_pets = AsyncMock(return_value=[SAMPLE_PET])

        bot = AsyncMock()
        file_mock = MagicMock()
        file_mock.file_path = "v.ogg"
        bot.get_file = AsyncMock(return_value=file_mock)
        bot.download_file = AsyncMock(return_value=io.BytesIO(b"v"))
        bot.send_chat_action = AsyncMock()

        voice = MagicMock()
        voice.file_id = "v1"
        mock_message.voice = voice
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)

        await handle_voice_anywhere(mock_message, fsm_context, bot)
        assert processing_msg.edit_text.await_count >= 1

    @patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value="Совет")
    @patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="Вопрос")
    @patch("bot.handlers.photo.api_client")
    async def test_voice_ok_no_pets(self, mock_api, mock_tr, mock_consult, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_api.list_pets = AsyncMock(return_value=[])

        bot = AsyncMock()
        file_mock = MagicMock()
        file_mock.file_path = "v.ogg"
        bot.get_file = AsyncMock(return_value=file_mock)
        bot.download_file = AsyncMock(return_value=io.BytesIO(b"v"))
        bot.send_chat_action = AsyncMock()

        voice = MagicMock()
        voice.file_id = "v1"
        mock_message.voice = voice
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)

        await handle_voice_anywhere(mock_message, fsm_context, bot)
        processing_msg.edit_text.assert_awaited()

    @patch("bot.handlers.photo.api_client")
    async def test_voice_ai_down(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        bot = AsyncMock()
        voice = MagicMock()
        voice.file_id = "v1"
        mock_message.voice = voice
        await handle_voice_anywhere(mock_message, fsm_context, bot)
        text = mock_message.answer.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.photo.api_client")
    async def test_voice_limit(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(False, 0))
        bot = AsyncMock()
        voice = MagicMock()
        voice.file_id = "v1"
        mock_message.voice = voice
        await handle_voice_anywhere(mock_message, fsm_context, bot)
        text = mock_message.answer.call_args[0][0]
        assert "лимит" in text

    @patch("bot.handlers.photo.api_client")
    async def test_voice_protected_state(self, mock_api, mock_message, fsm_context):
        from bot.states.states import VoiceNoteForm
        await fsm_context.set_state(VoiceNoteForm.waiting_voice)
        bot = AsyncMock()
        voice = MagicMock()
        voice.file_id = "v1"
        mock_message.voice = voice
        mock_message.answer = AsyncMock()
        await handle_voice_anywhere(mock_message, fsm_context, bot)
        mock_message.answer.assert_not_awaited()

    @patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="ab")
    @patch("bot.handlers.photo.api_client")
    async def test_voice_transcription_short(self, mock_api, mock_tr, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_api.refund_ai_limit = AsyncMock()
        bot = AsyncMock()
        file_mock = MagicMock()
        file_mock.file_path = "v.ogg"
        bot.get_file = AsyncMock(return_value=file_mock)
        bot.download_file = AsyncMock(return_value=io.BytesIO(b"v"))
        bot.send_chat_action = AsyncMock()
        voice = MagicMock()
        voice.file_id = "v1"
        mock_message.voice = voice
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)
        await handle_voice_anywhere(mock_message, fsm_context, bot)
        mock_api.refund_ai_limit.assert_awaited_once()

    @patch("bot.handlers.photo.consult_symptoms", new_callable=AsyncMock, return_value=None)
    @patch("bot.handlers.photo.transcribe_voice", new_callable=AsyncMock, return_value="Вопрос ветеринару")
    @patch("bot.handlers.photo.api_client")
    async def test_voice_no_result(self, mock_api, mock_tr, mock_consult, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_api.refund_ai_limit = AsyncMock()
        mock_api.list_pets = AsyncMock(return_value=[])
        bot = AsyncMock()
        file_mock = MagicMock()
        file_mock.file_path = "v.ogg"
        bot.get_file = AsyncMock(return_value=file_mock)
        bot.download_file = AsyncMock(return_value=io.BytesIO(b"v"))
        bot.send_chat_action = AsyncMock()
        voice = MagicMock()
        voice.file_id = "v1"
        mock_message.voice = voice
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)
        await handle_voice_anywhere(mock_message, fsm_context, bot)
        mock_api.refund_ai_limit.assert_awaited_once()
