"""Tests for bot/bot/handlers/subscription.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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


def _msg(user_id: int = 1, text: str = "") -> MagicMock:
    m = AsyncMock()
    m.from_user = MagicMock(id=user_id)
    m.text = text
    m.answer = AsyncMock()
    return m


def _cb(user_id: int = 1, data: str = "") -> MagicMock:
    c = AsyncMock()
    c.from_user = MagicMock(id=user_id)
    c.data = data
    c.message = AsyncMock()
    c.message.edit_text = AsyncMock()
    c.message.answer = AsyncMock()
    c.answer = AsyncMock()
    return c


def _state(current: str | None = None) -> AsyncMock:
    s = AsyncMock()
    s.clear = AsyncMock()
    s.set_state = AsyncMock()
    s.get_state = AsyncMock(return_value=current)
    return s


@pytest.mark.asyncio
@patch("bot.handlers.subscription.api_client")
async def test_settings_menu(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    msg = _msg(text="⚙️ Настройки")
    state = _state()

    await settings_menu(msg, state)

    state.clear.assert_awaited_once()
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.subscription.api_client")
async def test_settings_menu_cb(mock_api: MagicMock):
    mock_api.track_user_activity = AsyncMock()
    cb = _cb(data="settings:menu")
    state = _state()

    await settings_menu_cb(cb, state)

    state.clear.assert_awaited_once()
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.subscription.get_settings")
@patch("bot.handlers.subscription.api_client")
async def test_cmd_funnel_admin(mock_api: MagicMock, mock_settings: MagicMock):
    mock_settings.return_value = MagicMock(ADMIN_IDS=[42])
    mock_api.get_funnel_report = AsyncMock(return_value="report data")

    msg = _msg(user_id=42, text="/funnel")
    await cmd_funnel(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.subscription.get_settings")
async def test_cmd_funnel_non_admin(mock_settings: MagicMock):
    mock_settings.return_value = MagicMock(ADMIN_IDS=[42])
    msg = _msg(user_id=1, text="/funnel")

    await cmd_funnel(msg)

    msg.answer.assert_not_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.subscription.get_settings")
@patch("bot.handlers.subscription.api_client")
async def test_cmd_grant_premium_success(mock_api: MagicMock, mock_settings: MagicMock):
    mock_settings.return_value = MagicMock(ADMIN_IDS=[42])
    mock_api.grant_premium = AsyncMock(return_value=True)

    msg = _msg(user_id=42, text="/premium 100 30 pro")
    await cmd_grant_premium(msg)
    msg.answer.assert_awaited_once()
    assert "Подписка выдана" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("bot.handlers.subscription.get_settings")
async def test_cmd_grant_premium_non_admin(mock_settings: MagicMock):
    mock_settings.return_value = MagicMock(ADMIN_IDS=[42])
    msg = _msg(user_id=1, text="/premium 100 30")
    await cmd_grant_premium(msg)
    msg.answer.assert_not_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.subscription.get_settings")
async def test_cmd_grant_premium_missing_args(mock_settings: MagicMock):
    mock_settings.return_value = MagicMock(ADMIN_IDS=[42])
    msg = _msg(user_id=42, text="/premium")
    await cmd_grant_premium(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.subscription.get_settings")
async def test_cmd_grant_premium_invalid_days(mock_settings: MagicMock):
    mock_settings.return_value = MagicMock(ADMIN_IDS=[42])
    msg = _msg(user_id=42, text="/premium 100 -5")
    await cmd_grant_premium(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.subscription.get_settings")
@patch("bot.handlers.subscription.api_client")
async def test_cmd_revoke_premium_success(mock_api: MagicMock, mock_settings: MagicMock):
    mock_settings.return_value = MagicMock(ADMIN_IDS=[42])
    mock_api.revoke_premium = AsyncMock(return_value=True)

    msg = _msg(user_id=42, text="/revoke 100")
    await cmd_revoke_premium(msg)
    msg.answer.assert_awaited_once()
    assert "отозвана" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("bot.handlers.subscription.get_settings")
async def test_cmd_revoke_non_admin(mock_settings: MagicMock):
    mock_settings.return_value = MagicMock(ADMIN_IDS=[42])
    msg = _msg(user_id=1, text="/revoke 100")
    await cmd_revoke_premium(msg)
    msg.answer.assert_not_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.subscription.api_client")
async def test_cb_subscription_cancel_no_premium(mock_api: MagicMock):
    mock_api.get_subscription_status = AsyncMock(return_value={"is_premium": False})

    cb = _cb(data="settings:sub_cancel")
    await cb_subscription_cancel(cb)

    cb.message.edit_text.assert_awaited_once()
    assert "нет активной" in cb.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
@patch("bot.handlers.subscription.api_client")
async def test_cb_subscription_cancel_with_premium(mock_api: MagicMock):
    mock_api.get_subscription_status = AsyncMock(return_value={"is_premium": True})

    cb = _cb(data="settings:sub_cancel")
    await cb_subscription_cancel(cb)

    cb.message.edit_text.assert_awaited_once()
    assert "Отменить" in cb.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
@patch("bot.handlers.subscription.api_client")
async def test_cb_subscription_cancel_confirm(mock_api: MagicMock):
    mock_api.revoke_premium = AsyncMock()

    cb = _cb(data="settings:sub_cancel_confirm")
    await cb_subscription_cancel_confirm(cb)

    mock_api.revoke_premium.assert_awaited_once()
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.subscription.api_client")
async def test_cb_weather_city(mock_api: MagicMock):
    mock_api.get_subscription_status = AsyncMock(return_value={"city": "Москва"})

    cb = _cb(data="settings:weather_city")
    state = _state()

    await cb_weather_city(cb, state)

    state.set_state.assert_awaited_once()
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.subscription.api_client")
async def test_weather_city_entered_valid(mock_api: MagicMock):
    mock_api.update_user_settings = AsyncMock()

    msg = _msg(text="Санкт-Петербург")
    state = _state()

    await weather_city_entered(msg, state)

    state.clear.assert_awaited_once()
    mock_api.update_user_settings.assert_awaited_once()
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_weather_city_entered_empty():
    msg = _msg(text="")
    state = _state()

    await weather_city_entered(msg, state)

    msg.answer.assert_awaited_once()
    assert "корректное" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_weather_city_invalid():
    msg = _msg()
    await weather_city_invalid(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.subscription.api_client")
async def test_cb_weather_toggle_no_permission(mock_api: MagicMock):
    mock_api.check_feature_permission = AsyncMock(return_value=False)

    cb = _cb(data="settings:weather_toggle")
    await cb_weather_toggle(cb)

    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.subscription.api_client")
async def test_cb_weather_toggle_enabled(mock_api: MagicMock):
    mock_api.check_feature_permission = AsyncMock(return_value=True)
    mock_api.toggle_weather_notify = AsyncMock(return_value={"weather_notify": True})

    cb = _cb(data="settings:weather_toggle")
    await cb_weather_toggle(cb)

    cb.message.edit_text.assert_awaited_once()
    assert "включены" in cb.message.edit_text.call_args[0][0]
