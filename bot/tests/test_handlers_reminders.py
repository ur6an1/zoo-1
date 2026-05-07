"""Tests for bot.handlers.reminders — reminder CRUD and FSM flow."""

from unittest.mock import AsyncMock, patch

from bot.handlers.reminders import (
    cb_reminder_add,
    cb_reminder_cancel,
    cb_reminder_delete,
    cb_reminder_list,
    cb_reminder_pause,
    cb_reminder_pet,
    cb_reminder_resume,
    cb_reminder_view,
    cb_reminders_menu,
    reminder_category,
    reminder_date,
    reminder_description,
    reminder_repeat,
    reminder_time,
    reminder_title,
    reminders_menu,
)
from bot.states.states import ReminderForm

SAMPLE_REMINDER = {
    "id": 1, "title": "Кормление", "description": "Утром",
    "category_emoji": "🍽", "pet_name": "Рекс",
    "remind_at": None, "repeat_text": "ежедневно",
    "repeat": "daily", "is_active": True,
}


class TestRemindersMenu:
    @patch("bot.handlers.reminders.api_client")
    async def test_message(self, mock_api, mock_message):
        mock_api.track_user_activity = AsyncMock()
        await reminders_menu(mock_message)
        text = mock_message.answer.call_args[0][0]
        assert "Напоминания" in text

    async def test_callback(self, mock_callback):
        await cb_reminders_menu(mock_callback)
        mock_callback.message.edit_text.assert_awaited_once()
        mock_callback.answer.assert_awaited_once()


class TestCbReminderAdd:
    @patch("bot.handlers.reminders.api_client")
    async def test_no_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_reminder_add(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "добавьте питомца" in text.lower()

    @patch("bot.handlers.reminders.api_client")
    async def test_with_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        await cb_reminder_add(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == ReminderForm.choosing_pet.state


class TestCbReminderPet:
    @patch("bot.handlers.reminders.api_client")
    async def test_valid(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_reminder:1"
        mock_api.get_pet = AsyncMock(return_value={"id": 1, "name": "Рекс"})
        await fsm_context.set_state(ReminderForm.choosing_pet)
        await cb_reminder_pet(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == ReminderForm.category.state

    @patch("bot.handlers.reminders.api_client")
    async def test_not_found(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_reminder:999"
        mock_api.get_pet = AsyncMock(return_value=None)
        await fsm_context.set_state(ReminderForm.choosing_pet)
        await cb_reminder_pet(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()

    async def test_invalid_id(self, mock_callback, fsm_context):
        mock_callback.data = "pet:select_reminder:abc"
        await fsm_context.set_state(ReminderForm.choosing_pet)
        await cb_reminder_pet(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()


class TestReminderCategory:
    async def test_select_category(self, mock_callback, fsm_context):
        mock_callback.data = "rem_cat:feeding"
        await fsm_context.set_state(ReminderForm.category)
        await reminder_category(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == ReminderForm.title.state
        data = await fsm_context.get_data()
        assert data["category"] == "feeding"


class TestReminderTitle:
    async def test_valid(self, mock_message, fsm_context):
        mock_message.text = "Кормление"
        await fsm_context.set_state(ReminderForm.title)
        await reminder_title(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == ReminderForm.description.state

    async def test_empty(self, mock_message, fsm_context):
        mock_message.text = ""
        await fsm_context.set_state(ReminderForm.title)
        await reminder_title(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == ReminderForm.title.state

    async def test_too_long(self, mock_message, fsm_context):
        mock_message.text = "X" * 201
        await fsm_context.set_state(ReminderForm.title)
        await reminder_title(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == ReminderForm.title.state


class TestReminderDescription:
    async def test_with_text(self, mock_message, fsm_context):
        mock_message.text = "Утром и вечером"
        await fsm_context.set_state(ReminderForm.description)
        await reminder_description(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == ReminderForm.date.state

    async def test_skip_with_dash(self, mock_message, fsm_context):
        mock_message.text = "-"
        await fsm_context.set_state(ReminderForm.description)
        await reminder_description(mock_message, fsm_context)
        data = await fsm_context.get_data()
        assert data["description"] == ""


class TestReminderDate:
    async def test_valid(self, mock_message, fsm_context):
        mock_message.text = "15.06.2026"
        await fsm_context.set_state(ReminderForm.date)
        await reminder_date(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == ReminderForm.time.state

    async def test_invalid(self, mock_message, fsm_context):
        mock_message.text = "invalid"
        await fsm_context.set_state(ReminderForm.date)
        await reminder_date(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == ReminderForm.date.state


class TestReminderTime:
    async def test_valid(self, mock_message, fsm_context):
        mock_message.text = "09:00"
        await fsm_context.set_state(ReminderForm.time)
        await reminder_time(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == ReminderForm.repeat.state

    async def test_invalid(self, mock_message, fsm_context):
        mock_message.text = "invalid"
        await fsm_context.set_state(ReminderForm.time)
        await reminder_time(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == ReminderForm.time.state


class TestReminderRepeat:
    @patch("bot.handlers.reminders.api_client")
    async def test_save(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "repeat:daily"
        mock_api.create_reminder = AsyncMock(return_value={"id": 1})
        mock_api.get_pet = AsyncMock(return_value={"id": 1, "name": "Рекс"})
        await fsm_context.set_state(ReminderForm.repeat)
        await fsm_context.update_data(
            pet_id=1, category="feeding", title="Кормление",
            description="", date="2026-06-15", hour=9, minute=0,
        )
        await reminder_repeat(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "создано" in text.lower()
        state = await fsm_context.get_state()
        assert state is None


class TestReminderList:
    @patch("bot.handlers.reminders.api_client")
    async def test_empty(self, mock_api, mock_callback):
        mock_api.list_reminders = AsyncMock(return_value=[])
        await cb_reminder_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "нет напоминаний" in text

    @patch("bot.handlers.reminders.api_client")
    async def test_with_reminders(self, mock_api, mock_callback):
        mock_api.list_reminders = AsyncMock(return_value=[SAMPLE_REMINDER])
        await cb_reminder_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Ваши напоминания" in text


class TestReminderView:
    @patch("bot.handlers.reminders.api_client")
    async def test_found(self, mock_api, mock_callback):
        mock_callback.data = "reminder:view:1"
        mock_api.get_reminder = AsyncMock(return_value=SAMPLE_REMINDER)
        await cb_reminder_view(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Кормление" in text

    @patch("bot.handlers.reminders.api_client")
    async def test_not_found(self, mock_api, mock_callback):
        mock_callback.data = "reminder:view:999"
        mock_api.get_reminder = AsyncMock(return_value=None)
        await cb_reminder_view(mock_callback)
        mock_callback.answer.assert_awaited_once()


class TestReminderPauseResume:
    @patch("bot.handlers.reminders.api_client")
    async def test_pause(self, mock_api, mock_callback):
        mock_callback.data = "reminder:pause:1"
        mock_api.pause_reminder = AsyncMock(return_value={"id": 1, "title": "Кормление"})
        await cb_reminder_pause(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "приостановлено" in text

    @patch("bot.handlers.reminders.api_client")
    async def test_pause_not_found(self, mock_api, mock_callback):
        mock_callback.data = "reminder:pause:999"
        mock_api.pause_reminder = AsyncMock(return_value=None)
        await cb_reminder_pause(mock_callback)
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.reminders.api_client")
    async def test_resume(self, mock_api, mock_callback):
        mock_callback.data = "reminder:resume:1"
        mock_api.resume_reminder = AsyncMock(return_value={"id": 1, "title": "Кормление"})
        await cb_reminder_resume(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "возобновлено" in text

    @patch("bot.handlers.reminders.api_client")
    async def test_resume_not_found(self, mock_api, mock_callback):
        mock_callback.data = "reminder:resume:999"
        mock_api.resume_reminder = AsyncMock(return_value=None)
        await cb_reminder_resume(mock_callback)
        mock_callback.answer.assert_awaited_once()


class TestReminderDelete:
    @patch("bot.handlers.reminders.api_client")
    async def test_delete(self, mock_api, mock_callback):
        mock_callback.data = "reminder:delete:1"
        mock_api.delete_reminder = AsyncMock(return_value=True)
        await cb_reminder_delete(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "удалено" in text

    @patch("bot.handlers.reminders.api_client")
    async def test_not_found(self, mock_api, mock_callback):
        mock_callback.data = "reminder:delete:999"
        mock_api.delete_reminder = AsyncMock(return_value=False)
        await cb_reminder_delete(mock_callback)
        mock_callback.answer.assert_awaited_once()

    async def test_invalid_id(self, mock_callback):
        mock_callback.data = "reminder:delete:abc"
        await cb_reminder_delete(mock_callback)
        mock_callback.answer.assert_awaited_once()


class TestReminderCancel:
    async def test_cancel(self, mock_callback, fsm_context):
        await fsm_context.set_state(ReminderForm.title)
        await cb_reminder_cancel(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state is None
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "отменено" in text
