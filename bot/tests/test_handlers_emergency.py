"""Tests for bot.handlers.emergency — SOS, emergency tips, clinic search."""

from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.emergency import (
    cb_clinic_radius,
    cb_sos_clinic,
    cb_sos_clinic_rated,
    cb_sos_general,
    cb_sos_injury,
    cb_sos_overheat,
    cb_sos_poisoning,
    emergency_menu,
    emergency_menu_cb,
    handle_location,
    location_expected,
)
from bot.states.states import ClinicSearchForm


class TestEmergencyMenu:
    async def test_message(self, mock_message):
        await emergency_menu(mock_message)
        mock_message.answer.assert_awaited_once()
        text = mock_message.answer.call_args[0][0]
        assert "Экстренная помощь" in text

    async def test_callback(self, mock_callback):
        await emergency_menu_cb(mock_callback)
        mock_callback.message.edit_text.assert_awaited_once()
        mock_callback.answer.assert_awaited_once()


class TestCbSosClinic:
    async def test_sets_state_and_asks_location(self, mock_callback, fsm_context):
        await cb_sos_clinic(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == ClinicSearchForm.waiting_location.state
        mock_callback.message.answer.assert_awaited_once()


class TestCbSosClinicRated:
    async def test_sets_filter_state(self, mock_callback, fsm_context):
        await cb_sos_clinic_rated(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == ClinicSearchForm.waiting_filters.state
        mock_callback.message.edit_text.assert_awaited_once()


class TestCbClinicRadius:
    async def test_valid_radius(self, mock_callback, fsm_context):
        mock_callback.data = "clinic:r:5000"
        await fsm_context.set_state(ClinicSearchForm.waiting_filters)
        await cb_clinic_radius(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == ClinicSearchForm.waiting_location.state
        data = await fsm_context.get_data()
        assert data["clinic_radius"] == 5000

    async def test_invalid_radius(self, mock_callback, fsm_context):
        mock_callback.data = "clinic:r:abc"
        await fsm_context.set_state(ClinicSearchForm.waiting_filters)
        await cb_clinic_radius(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()


class TestHandleLocation:
    @patch("bot.handlers.emergency.search_and_format")
    async def test_searches_and_responds(self, mock_search, mock_message, fsm_context):
        mock_search.return_value = "Найдено 3 клиники"
        mock_message.location = MagicMock()
        mock_message.location.latitude = 55.75
        mock_message.location.longitude = 37.62
        mock_message.answer = AsyncMock(return_value=AsyncMock())

        await fsm_context.set_state(ClinicSearchForm.waiting_location)
        await fsm_context.update_data(clinic_radius=5000)

        await handle_location(mock_message, fsm_context)

        state = await fsm_context.get_state()
        assert state is None
        assert mock_message.answer.await_count >= 2


class TestLocationExpected:
    async def test_wrong_input(self, mock_message):
        await location_expected(mock_message)
        text = mock_message.answer.call_args[0][0]
        assert "геолокацию" in text


class TestEmergencyTipHandlers:
    @patch("bot.handlers.emergency.EMERGENCY_POISONING", "Текст отравление")
    async def test_poisoning(self, mock_callback):
        await cb_sos_poisoning(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Текст отравление" in text

    @patch("bot.handlers.emergency.EMERGENCY_INJURY", "Текст травма")
    async def test_injury(self, mock_callback):
        await cb_sos_injury(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Текст травма" in text

    @patch("bot.handlers.emergency.EMERGENCY_OVERHEAT", "Текст перегрев")
    async def test_overheat(self, mock_callback):
        await cb_sos_overheat(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Текст перегрев" in text

    @patch("bot.handlers.emergency.EMERGENCY_GENERAL", "Общая памятка")
    async def test_general(self, mock_callback):
        await cb_sos_general(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Общая памятка" in text
