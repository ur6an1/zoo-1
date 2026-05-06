"""Tests for bot.handlers.common — /start, /help, /cancel, menu navigation."""

from unittest.mock import AsyncMock, patch

from bot.handlers.common import (
    ai_hub,
    back_to_menu_text,
    cb_cancel,
    cb_main_menu,
    cmd_cancel,
    cmd_help,
    cmd_start,
    health_hub,
    pets_hub,
    settings_hub,
)


class TestCmdStart:
    @patch("bot.handlers.common.api_client")
    async def test_sends_welcome(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.track_event = AsyncMock()

        await cmd_start(mock_message, fsm_context)

        assert mock_message.answer.await_count == 2
        first_call_text = mock_message.answer.call_args_list[0][0][0]
        assert "ZooBuddy" in first_call_text

    @patch("bot.handlers.common.api_client")
    async def test_clears_state(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.track_event = AsyncMock()

        await fsm_context.set_state("SomeState:x")
        await cmd_start(mock_message, fsm_context)

        state = await fsm_context.get_state()
        assert state is None

    @patch("bot.handlers.common.api_client")
    async def test_tracks_activity(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        mock_api.track_event = AsyncMock()

        await cmd_start(mock_message, fsm_context)
        mock_api.track_user_activity.assert_awaited_once()
        mock_api.track_event.assert_awaited_once()


class TestCmdHelp:
    async def test_sends_help(self, mock_message):
        await cmd_help(mock_message)
        mock_message.answer.assert_awaited_once()
        text = mock_message.answer.call_args[0][0]
        assert "/start" in text
        assert "/help" in text
        assert "/cancel" in text


class TestCmdCancel:
    async def test_no_state(self, mock_message, fsm_context):
        await cmd_cancel(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "Нечего отменять" in text

    async def test_with_state(self, mock_message, fsm_context):
        await fsm_context.set_state("PetForm:name")
        await cmd_cancel(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "отменено" in text
        state = await fsm_context.get_state()
        assert state is None


class TestCbCancel:
    async def test_inline_cancel(self, mock_callback, fsm_context):
        await fsm_context.set_state("PetForm:name")
        await cb_cancel(mock_callback, fsm_context)
        mock_callback.message.edit_text.assert_awaited_once()
        mock_callback.answer.assert_awaited_once()
        state = await fsm_context.get_state()
        assert state is None


class TestCbMainMenu:
    async def test_clears_state_and_responds(self, mock_callback, fsm_context):
        await fsm_context.set_state("PetForm:name")
        await cb_main_menu(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state is None
        mock_callback.message.answer.assert_awaited_once()
        mock_callback.answer.assert_awaited_once()


class TestBackToMenuText:
    async def test_clears_state(self, mock_message, fsm_context):
        await fsm_context.set_state("PetForm:name")
        await back_to_menu_text(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None
        mock_message.answer.assert_awaited_once()


class TestMenuHubs:
    async def test_pets_hub(self, mock_message):
        await pets_hub(mock_message)
        mock_message.answer.assert_awaited_once()
        text = mock_message.answer.call_args[0][0]
        assert "Питомцы" in text or "питомцев" in text

    async def test_health_hub(self, mock_message):
        await health_hub(mock_message)
        mock_message.answer.assert_awaited_once()

    async def test_ai_hub(self, mock_message):
        await ai_hub(mock_message)
        mock_message.answer.assert_awaited_once()

    async def test_settings_hub(self, mock_message):
        await settings_hub(mock_message)
        mock_message.answer.assert_awaited_once()
