"""Tests for bot.handlers.subscription — settings, admin commands, weather city."""

from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.subscription import (
    cb_subscription_cancel,
    cb_subscription_cancel_confirm,
    cb_weather_city,
    cb_weather_toggle,
    cmd_funnel,
    cmd_grant_premium,
    cmd_revoke_premium,
    settings_menu,
    settings_menu_cb,
    weather_city_entered,
    weather_city_invalid,
)
from bot.states.states import WeatherCityForm


class TestSettingsMenu:
    @patch("bot.handlers.subscription.api_client")
    async def test_message(self, mock_api, mock_message, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        await settings_menu(mock_message, fsm_context)
        mock_message.answer.assert_awaited_once()

    @patch("bot.handlers.subscription.api_client")
    async def test_callback(self, mock_api, mock_callback, fsm_context):
        mock_api.track_user_activity = AsyncMock()
        await settings_menu_cb(mock_callback, fsm_context)
        mock_callback.message.edit_text.assert_awaited_once()
        mock_callback.answer.assert_awaited_once()


class TestCmdFunnel:
    @patch("bot.handlers.subscription.get_settings")
    @patch("bot.handlers.subscription.api_client")
    async def test_admin_gets_report(self, mock_api, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [12345]
        mock_api.get_funnel_report = AsyncMock(return_value="Report data")
        mock_message.text = "/funnel"
        await cmd_funnel(mock_message)
        mock_message.answer.assert_awaited_once()

    @patch("bot.handlers.subscription.get_settings")
    async def test_non_admin_ignored(self, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [99999]
        mock_message.text = "/funnel"
        await cmd_funnel(mock_message)
        mock_message.answer.assert_not_awaited()


class TestCmdGrantPremium:
    @patch("bot.handlers.subscription.get_settings")
    @patch("bot.handlers.subscription.api_client")
    async def test_grant_success(self, mock_api, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [12345]
        mock_api.grant_premium = AsyncMock(return_value=True)
        mock_message.text = "/premium 67890 30 pro"
        await cmd_grant_premium(mock_message)
        mock_message.answer.assert_awaited_once()
        assert "Подписка выдана" in mock_message.answer.call_args[0][0]

    @patch("bot.handlers.subscription.get_settings")
    @patch("bot.handlers.subscription.api_client")
    async def test_grant_failure(self, mock_api, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [12345]
        mock_api.grant_premium = AsyncMock(return_value=False)
        mock_message.text = "/premium 67890 30"
        await cmd_grant_premium(mock_message)
        mock_message.answer.assert_awaited_once()
        assert "Не удалось" in mock_message.answer.call_args[0][0]

    @patch("bot.handlers.subscription.get_settings")
    async def test_missing_args(self, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [12345]
        mock_message.text = "/premium"
        await cmd_grant_premium(mock_message)
        mock_message.answer.assert_awaited_once()

    @patch("bot.handlers.subscription.get_settings")
    async def test_non_admin_ignored(self, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [99999]
        mock_message.text = "/premium 67890 30"
        await cmd_grant_premium(mock_message)
        mock_message.answer.assert_not_awaited()

    @patch("bot.handlers.subscription.get_settings")
    async def test_invalid_user_id(self, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [12345]
        mock_message.text = "/premium abc 30"
        await cmd_grant_premium(mock_message)
        mock_message.answer.assert_awaited_once()

    @patch("bot.handlers.subscription.get_settings")
    async def test_invalid_days(self, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [12345]
        mock_message.text = "/premium 67890 0"
        await cmd_grant_premium(mock_message)
        mock_message.answer.assert_awaited_once()

    @patch("bot.handlers.subscription.get_settings")
    async def test_invalid_tier(self, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [12345]
        mock_message.text = "/premium 67890 30 invalid_tier"
        await cmd_grant_premium(mock_message)
        mock_message.answer.assert_awaited_once()
        assert "basic или pro" in mock_message.answer.call_args[0][0]

    @patch("bot.handlers.subscription.get_settings")
    @patch("bot.handlers.subscription.api_client")
    async def test_grant_exception(self, mock_api, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [12345]
        mock_api.grant_premium = AsyncMock(side_effect=Exception("fail"))
        mock_message.text = "/premium 67890 30"
        await cmd_grant_premium(mock_message)
        mock_message.answer.assert_awaited_once()


class TestCmdRevokePremium:
    @patch("bot.handlers.subscription.get_settings")
    @patch("bot.handlers.subscription.api_client")
    async def test_revoke_success(self, mock_api, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [12345]
        mock_api.revoke_premium = AsyncMock(return_value=True)
        mock_message.text = "/revoke 67890"
        await cmd_revoke_premium(mock_message)
        assert "отозвана" in mock_message.answer.call_args[0][0]

    @patch("bot.handlers.subscription.get_settings")
    async def test_missing_args(self, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [12345]
        mock_message.text = "/revoke"
        await cmd_revoke_premium(mock_message)
        mock_message.answer.assert_awaited_once()

    @patch("bot.handlers.subscription.get_settings")
    async def test_non_admin_ignored(self, mock_settings, mock_message):
        mock_settings.return_value.ADMIN_IDS = [99999]
        mock_message.text = "/revoke 67890"
        await cmd_revoke_premium(mock_message)
        mock_message.answer.assert_not_awaited()


class TestSubscriptionCancel:
    @patch("bot.handlers.subscription.api_client")
    async def test_no_premium(self, mock_api, mock_callback):
        mock_api.get_subscription_status = AsyncMock(return_value={"is_premium": False})
        await cb_subscription_cancel(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "нет активной подписки" in text

    @patch("bot.handlers.subscription.api_client")
    async def test_has_premium(self, mock_api, mock_callback):
        mock_api.get_subscription_status = AsyncMock(return_value={"is_premium": True})
        await cb_subscription_cancel(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Отменить" in text or "отменить" in text


class TestSubscriptionCancelConfirm:
    @patch("bot.handlers.subscription.api_client")
    async def test_confirmed(self, mock_api, mock_callback):
        mock_api.revoke_premium = AsyncMock(return_value=True)
        await cb_subscription_cancel_confirm(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "отменена" in text


class TestWeatherCity:
    @patch("bot.handlers.subscription.api_client")
    async def test_prompts_city_input(self, mock_api, mock_callback, fsm_context):
        mock_api.get_subscription_status = AsyncMock(return_value={"city": "Москва"})
        await cb_weather_city(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == WeatherCityForm.waiting_city.state
        mock_callback.message.edit_text.assert_awaited_once()

    @patch("bot.handlers.subscription.api_client")
    async def test_save_city_success(self, mock_api, mock_message, fsm_context):
        mock_api.update_user_settings = AsyncMock()
        mock_message.text = "Санкт-Петербург"
        await fsm_context.set_state(WeatherCityForm.waiting_city)
        await weather_city_entered(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "Санкт-Петербург" in text
        state = await fsm_context.get_state()
        assert state is None

    @patch("bot.handlers.subscription.api_client")
    async def test_save_city_error(self, mock_api, mock_message, fsm_context):
        mock_api.update_user_settings = AsyncMock(side_effect=Exception("fail"))
        mock_message.text = "Москва"
        await weather_city_entered(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "Не удалось" in text

    async def test_empty_city(self, mock_message, fsm_context):
        mock_message.text = ""
        await weather_city_entered(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "корректное" in text

    async def test_city_too_long(self, mock_message, fsm_context):
        mock_message.text = "X" * 201
        await weather_city_entered(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "корректное" in text or "200" in text

    async def test_non_text_input(self, mock_message):
        await weather_city_invalid(mock_message)
        text = mock_message.answer.call_args[0][0]
        assert "текстом" in text


class TestWeatherToggle:
    @patch("bot.handlers.subscription.api_client")
    async def test_no_permission(self, mock_api, mock_callback):
        mock_api.check_feature_permission = AsyncMock(return_value=False)
        await cb_weather_toggle(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "PRO" in text

    @patch("bot.handlers.subscription.api_client")
    async def test_toggle_on(self, mock_api, mock_callback):
        mock_api.check_feature_permission = AsyncMock(return_value=True)
        mock_api.toggle_weather_notify = AsyncMock(return_value={"weather_notify": True})
        await cb_weather_toggle(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "включены" in text

    @patch("bot.handlers.subscription.api_client")
    async def test_toggle_off(self, mock_api, mock_callback):
        mock_api.check_feature_permission = AsyncMock(return_value=True)
        mock_api.toggle_weather_notify = AsyncMock(return_value={"weather_notify": False})
        await cb_weather_toggle(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "выключены" in text

    @patch("bot.handlers.subscription.api_client")
    async def test_toggle_error(self, mock_api, mock_callback):
        mock_api.check_feature_permission = AsyncMock(return_value=True)
        mock_api.toggle_weather_notify = AsyncMock(side_effect=Exception("fail"))
        await cb_weather_toggle(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Не удалось" in text
