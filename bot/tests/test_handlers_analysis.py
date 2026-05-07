"""Tests for bot.handlers.analysis — AI medical test analysis."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.handlers.analysis import (
    _no_ai_message,
    _pet_info_str,
    analysis_not_photo,
    analysis_pet_chosen,
    analysis_photo_received,
    analysis_start,
    cb_analysis_start,
)
from bot.states.states import MedicalTestForm


SAMPLE_PET = {
    "id": 1,
    "name": "Барсик",
    "species": "Кот",
    "species_emoji": "🐱",
    "breed": "Британский",
    "birth_date": None,
    "age_str": "3 года",
    "weight": 4.5,
}


class TestHelpers:
    def test_no_ai_message(self):
        assert "недоступны" in _no_ai_message()

    def test_pet_info_str(self):
        result = _pet_info_str(SAMPLE_PET)
        assert "Кот" in result
        assert "Барсик" in result
        assert "4.5 кг" in result


class TestAnalysisStart:
    @patch("bot.handlers.analysis.api_client")
    async def test_start_ok(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.list_pets = AsyncMock(return_value=[SAMPLE_PET])
        await analysis_start(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == MedicalTestForm.choosing_pet

    @patch("bot.handlers.analysis.api_client")
    async def test_start_no_ai(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await analysis_start(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.analysis.api_client")
    async def test_start_no_pets(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.list_pets = AsyncMock(return_value=[])
        await analysis_start(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "нет питомцев" in text

    @patch("bot.handlers.analysis.api_client")
    async def test_cb_start_ok(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.list_pets = AsyncMock(return_value=[SAMPLE_PET])
        await cb_analysis_start(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == MedicalTestForm.choosing_pet

    @patch("bot.handlers.analysis.api_client")
    async def test_cb_start_no_ai(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await cb_analysis_start(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.analysis.api_client")
    async def test_cb_start_no_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_analysis_start(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "нет питомцев" in text


class TestAnalysisPetChosen:
    @patch("bot.handlers.analysis.api_client")
    async def test_pet_chosen_ok(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_analysis:1"
        mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
        await fsm_context.set_state(MedicalTestForm.choosing_pet)
        await analysis_pet_chosen(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == MedicalTestForm.waiting_photo

    @patch("bot.handlers.analysis.api_client")
    async def test_pet_chosen_invalid(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_analysis:abc"
        await analysis_pet_chosen(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.analysis.api_client")
    async def test_pet_chosen_not_found(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_analysis:999"
        mock_api.get_pet = AsyncMock(return_value=None)
        await analysis_pet_chosen(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()


class TestAnalysisPhotoReceived:
    @patch("bot.handlers.analysis.analyze_medical_test", new_callable=AsyncMock, return_value="Анализ в норме")
    @patch("bot.handlers.analysis.api_client")
    async def test_photo_ok(self, mock_api, mock_vision, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        await fsm_context.set_state(MedicalTestForm.waiting_photo)
        await fsm_context.update_data(analysis_pet_info="Кот Барсик")

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

        await analysis_photo_received(mock_message, fsm_context, bot)
        processing_msg.edit_text.assert_awaited()
        text = processing_msg.edit_text.call_args[0][0]
        assert "Результат" in text

    @patch("bot.handlers.analysis.api_client")
    async def test_photo_ai_down(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=False)
        await fsm_context.set_state(MedicalTestForm.waiting_photo)
        await fsm_context.update_data(analysis_pet_info="info")
        bot = AsyncMock()
        await analysis_photo_received(mock_message, fsm_context, bot)
        text = mock_message.answer.call_args[0][0]
        assert "недоступны" in text

    @patch("bot.handlers.analysis.api_client")
    async def test_photo_limit(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(False, 0))
        await fsm_context.set_state(MedicalTestForm.waiting_photo)
        await fsm_context.update_data(analysis_pet_info="info")
        bot = AsyncMock()
        await analysis_photo_received(mock_message, fsm_context, bot)
        text = mock_message.answer.call_args[0][0]
        assert "лимит" in text

    @patch("bot.handlers.analysis.api_client")
    async def test_photo_download_error(self, mock_api, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_api.refund_ai_limit = AsyncMock()
        await fsm_context.set_state(MedicalTestForm.waiting_photo)
        await fsm_context.update_data(analysis_pet_info="info")

        bot = AsyncMock()
        bot.get_file = AsyncMock(side_effect=Exception("fail"))
        bot.send_chat_action = AsyncMock()
        photo = MagicMock()
        photo.file_id = "abc"
        mock_message.photo = [photo]
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)

        await analysis_photo_received(mock_message, fsm_context, bot)
        mock_api.refund_ai_limit.assert_awaited_once()

    @patch("bot.handlers.analysis.analyze_medical_test", new_callable=AsyncMock, return_value=None)
    @patch("bot.handlers.analysis.api_client")
    async def test_photo_no_result(self, mock_api, mock_vision, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_api.refund_ai_limit = AsyncMock()
        await fsm_context.set_state(MedicalTestForm.waiting_photo)
        await fsm_context.update_data(analysis_pet_info="info")

        bot = AsyncMock()
        file_mock = MagicMock()
        file_mock.file_path = "p.jpg"
        bot.get_file = AsyncMock(return_value=file_mock)
        bot.download_file = AsyncMock(return_value=io.BytesIO(b"img"))
        bot.send_chat_action = AsyncMock()

        photo = MagicMock()
        photo.file_id = "abc"
        mock_message.photo = [photo]
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)

        await analysis_photo_received(mock_message, fsm_context, bot)
        mock_api.refund_ai_limit.assert_awaited_once()

    @patch("bot.handlers.analysis.analyze_medical_test", new_callable=AsyncMock, side_effect=Exception("AI error"))
    @patch("bot.handlers.analysis.api_client")
    async def test_photo_ai_exception(self, mock_api, mock_vision, mock_message, fsm_context):
        mock_api.is_ai_operational = AsyncMock(return_value=True)
        mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
        mock_api.refund_ai_limit = AsyncMock()
        await fsm_context.set_state(MedicalTestForm.waiting_photo)
        await fsm_context.update_data(analysis_pet_info="info")

        bot = AsyncMock()
        file_mock = MagicMock()
        file_mock.file_path = "p.jpg"
        bot.get_file = AsyncMock(return_value=file_mock)
        bot.download_file = AsyncMock(return_value=io.BytesIO(b"img"))
        bot.send_chat_action = AsyncMock()

        photo = MagicMock()
        photo.file_id = "abc"
        mock_message.photo = [photo]
        processing_msg = AsyncMock()
        mock_message.answer = AsyncMock(return_value=processing_msg)

        await analysis_photo_received(mock_message, fsm_context, bot)
        mock_api.refund_ai_limit.assert_awaited_once()


class TestAnalysisNotPhoto:
    async def test_not_photo(self, mock_message):
        await analysis_not_photo(mock_message)
        text = mock_message.answer.call_args[0][0]
        assert "фото" in text
