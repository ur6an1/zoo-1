"""Tests for worker.tasks.reminders — schedule_reminder logic."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from worker.tasks.reminders import _now_local, schedule_reminder, send_reminder
from zoo_shared.db.models import Reminder


class TestScheduleReminder:
    def _make_scheduler(self):
        scheduler = MagicMock()
        scheduler.get_job.return_value = None
        return scheduler

    def _make_reminder(self, repeat="once", is_active=True, remind_at=None):
        if remind_at is None:
            remind_at = datetime.now() + timedelta(hours=1)
        return Reminder(
            id=42,
            pet_id=1,
            user_id=1,
            category="feeding",
            title="Feed",
            description="",
            remind_at=remind_at,
            repeat=repeat,
            is_active=is_active,
        )

    def test_inactive_reminder_not_scheduled(self):
        scheduler = self._make_scheduler()
        schedule_reminder(scheduler, self._make_reminder(is_active=False))
        scheduler.add_job.assert_not_called()

    def test_once_future_scheduled(self):
        scheduler = self._make_scheduler()
        now = _now_local()
        future = now + timedelta(hours=1)
        schedule_reminder(scheduler, self._make_reminder(repeat="once", remind_at=future))
        scheduler.add_job.assert_called_once()

    def test_once_past_not_scheduled(self):
        scheduler = self._make_scheduler()
        now = _now_local()
        past = now - timedelta(hours=1)
        schedule_reminder(scheduler, self._make_reminder(repeat="once", remind_at=past))
        scheduler.add_job.assert_not_called()

    def test_daily_scheduled(self):
        scheduler = self._make_scheduler()
        schedule_reminder(scheduler, self._make_reminder(repeat="daily"))
        scheduler.add_job.assert_called_once()
        call_kwargs = scheduler.add_job.call_args
        assert call_kwargs.kwargs["id"] == "reminder_42"

    def test_weekly_scheduled(self):
        scheduler = self._make_scheduler()
        schedule_reminder(scheduler, self._make_reminder(repeat="weekly"))
        scheduler.add_job.assert_called_once()

    def test_monthly_scheduled(self):
        scheduler = self._make_scheduler()
        schedule_reminder(scheduler, self._make_reminder(repeat="monthly"))
        scheduler.add_job.assert_called_once()

    def test_yearly_scheduled(self):
        scheduler = self._make_scheduler()
        schedule_reminder(scheduler, self._make_reminder(repeat="yearly"))
        scheduler.add_job.assert_called_once()

    def test_unknown_repeat_not_scheduled(self):
        scheduler = self._make_scheduler()
        schedule_reminder(scheduler, self._make_reminder(repeat="biweekly"))
        scheduler.add_job.assert_not_called()

    def test_existing_job_removed(self):
        scheduler = self._make_scheduler()
        existing_job = MagicMock()
        scheduler.get_job.return_value = existing_job
        schedule_reminder(scheduler, self._make_reminder(repeat="daily"))
        existing_job.remove.assert_called_once()
        scheduler.add_job.assert_called_once()


class TestSendReminder:
    @pytest.mark.asyncio
    async def test_reminder_not_found(self):
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("worker.tasks.reminders.async_session", return_value=mock_session):
            await send_reminder(999)

    @pytest.mark.asyncio
    async def test_reminder_inactive(self):
        mock_reminder = MagicMock()
        mock_reminder.is_active = False

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_reminder)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("worker.tasks.reminders.async_session", return_value=mock_session):
            await send_reminder(1)

    @pytest.mark.asyncio
    async def test_reminder_sent(self):
        mock_pet = MagicMock()
        mock_pet.name = "Rex"
        mock_reminder = MagicMock()
        mock_reminder.is_active = True
        mock_reminder.pet = mock_pet
        mock_reminder.category_emoji = "🍽"
        mock_reminder.title = "Feed Rex"
        mock_reminder.description = "Morning meal"
        mock_reminder.repeat_text = "ежедневно"
        mock_reminder.repeat = "daily"
        mock_reminder.user_id = 42

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_reminder)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("worker.tasks.reminders.async_session", return_value=mock_session),
            patch("worker.tasks.reminders.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await send_reminder(1)
            mock_send.assert_called_once()
            text = mock_send.call_args[0][1]
            assert "Rex" in text
            assert "Feed Rex" in text

    @pytest.mark.asyncio
    async def test_reminder_once_deactivated(self):
        mock_pet = MagicMock()
        mock_pet.name = "Cat"
        mock_reminder = MagicMock()
        mock_reminder.is_active = True
        mock_reminder.pet = mock_pet
        mock_reminder.category_emoji = "💊"
        mock_reminder.title = "Medicine"
        mock_reminder.description = ""
        mock_reminder.repeat_text = "однократно"
        mock_reminder.repeat = "once"
        mock_reminder.user_id = 42

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_reminder)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()

        with (
            patch("worker.tasks.reminders.async_session", return_value=mock_session),
            patch("worker.tasks.reminders.send_message", new_callable=AsyncMock),
        ):
            await send_reminder(1)
            assert mock_reminder.is_active is False
            mock_session.commit.assert_called_once()
