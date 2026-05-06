"""Tests for bot.handlers.calendar_view — event calendar."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from bot.handlers.calendar_view import _build_calendar, calendar_menu, cb_calendar_view


class TestBuildCalendar:
    @patch("bot.handlers.calendar_view.api_client")
    async def test_no_pets(self, mock_api):
        mock_api.get_medical_calendar = AsyncMock(return_value={"pets": []})
        text = await _build_calendar(12345)
        assert "нет питомцев" in text

    @patch("bot.handlers.calendar_view.api_client")
    async def test_no_events(self, mock_api):
        mock_api.get_medical_calendar = AsyncMock(return_value={
            "pets": [{"id": 1}],
            "reminders": [],
            "vaccinations": [],
            "vet_visits": [],
        })
        text = await _build_calendar(12345)
        assert "Нет предстоящих событий" in text

    @patch("bot.handlers.calendar_view.api_client")
    async def test_with_reminders(self, mock_api):
        future = (datetime.now() + timedelta(hours=2)).isoformat()
        mock_api.get_medical_calendar = AsyncMock(return_value={
            "pets": [{"id": 1}],
            "reminders": [{
                "remind_at": future,
                "pet_name": "Рекс",
                "category_emoji": "🍽",
                "title": "Кормление",
                "repeat_text": "ежедневно",
            }],
            "vaccinations": [],
            "vet_visits": [],
        })
        text = await _build_calendar(12345)
        assert "Кормление" in text
        assert "Рекс" in text

    @patch("bot.handlers.calendar_view.api_client")
    async def test_with_vaccinations(self, mock_api):
        future = (datetime.now() + timedelta(days=7)).isoformat()
        mock_api.get_medical_calendar = AsyncMock(return_value={
            "pets": [{"id": 1}],
            "reminders": [],
            "vaccinations": [{
                "next_date": future,
                "pet_name": "Мурка",
                "name": "Бешенство",
            }],
            "vet_visits": [],
        })
        text = await _build_calendar(12345)
        assert "Бешенство" in text
        assert "Мурка" in text

    @patch("bot.handlers.calendar_view.api_client")
    async def test_with_vet_visits(self, mock_api):
        future = (datetime.now() + timedelta(days=1)).isoformat()
        mock_api.get_medical_calendar = AsyncMock(return_value={
            "pets": [{"id": 1}],
            "reminders": [],
            "vaccinations": [],
            "vet_visits": [{
                "visit_date": future,
                "pet_name": "Чарли",
                "diagnosis": "Осмотр",
            }],
        })
        text = await _build_calendar(12345)
        assert "ветеринару" in text.lower() or "Визит" in text
        assert "Чарли" in text

    @patch("bot.handlers.calendar_view.api_client")
    async def test_invalid_reminder_date_skipped(self, mock_api):
        mock_api.get_medical_calendar = AsyncMock(return_value={
            "pets": [{"id": 1}],
            "reminders": [{"remind_at": "not-a-date", "title": "Bad"}],
            "vaccinations": [],
            "vet_visits": [],
        })
        text = await _build_calendar(12345)
        assert "Bad" not in text

    @patch("bot.handlers.calendar_view.api_client")
    async def test_today_label(self, mock_api):
        now = datetime.now().replace(hour=23, minute=59)
        mock_api.get_medical_calendar = AsyncMock(return_value={
            "pets": [{"id": 1}],
            "reminders": [{
                "remind_at": now.isoformat(),
                "pet_name": "X",
                "category_emoji": "🍽",
                "title": "Test",
                "repeat_text": "",
            }],
            "vaccinations": [],
            "vet_visits": [],
        })
        text = await _build_calendar(12345)
        assert "Сегодня" in text

    @patch("bot.handlers.calendar_view.api_client")
    async def test_tomorrow_label(self, mock_api):
        tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=12, minute=0)
        mock_api.get_medical_calendar = AsyncMock(return_value={
            "pets": [{"id": 1}],
            "reminders": [{
                "remind_at": tomorrow.isoformat(),
                "pet_name": "X",
                "category_emoji": "🍽",
                "title": "Test",
                "repeat_text": "",
            }],
            "vaccinations": [],
            "vet_visits": [],
        })
        text = await _build_calendar(12345)
        assert "Завтра" in text


class TestCalendarMenu:
    @patch("bot.handlers.calendar_view._build_calendar")
    async def test_success(self, mock_build, mock_message):
        mock_build.return_value = "📅 Calendar text"
        await calendar_menu(mock_message)
        mock_message.answer.assert_awaited_once()

    @patch("bot.handlers.calendar_view._build_calendar")
    async def test_error(self, mock_build, mock_message):
        mock_build.side_effect = Exception("fail")
        await calendar_menu(mock_message)
        text = mock_message.answer.call_args[0][0]
        assert "Не удалось" in text


class TestCbCalendarView:
    @patch("bot.handlers.calendar_view._build_calendar")
    async def test_success(self, mock_build, mock_callback):
        mock_build.return_value = "📅 Calendar text"
        await cb_calendar_view(mock_callback)
        mock_callback.message.edit_text.assert_awaited_once()
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.calendar_view._build_calendar")
    async def test_error(self, mock_build, mock_callback):
        mock_build.side_effect = Exception("fail")
        await cb_calendar_view(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Не удалось" in text
