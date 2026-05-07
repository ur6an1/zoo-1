"""Tests for bot.handlers.weather_handler — weather display handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.weather_handler import (
    _generate_pet_weather_alert,
    weather_show,
    weather_show_cb,
)

PET = {"id": 1, "name": "Rex", "species": "собака", "species_emoji": "🐶"}

WEATHER_HOT = {
    "temp_c": 35, "feels_like": 38, "humidity": 60,
    "wind_kmph": 10, "uv": 9, "description": "Солнечно",
}
WEATHER_COLD = {
    "temp_c": -20, "feels_like": -25, "humidity": 80,
    "wind_kmph": 55, "uv": 1, "description": "Снег",
}
WEATHER_OK = {
    "temp_c": 20, "feels_like": 18, "humidity": 50,
    "wind_kmph": 10, "uv": 3, "description": "Облачно",
}


def _msg(text: str = "🌤 Погода") -> MagicMock:
    m = MagicMock()
    m.text = text
    m.from_user = MagicMock(id=1)
    m.answer = AsyncMock()
    return m


def _cb(data: str = "weather:show") -> MagicMock:
    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock(id=1)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


# ── _generate_pet_weather_alert ──


def test_alert_hot():
    result = _generate_pet_weather_alert(WEATHER_HOT)
    assert result is not None
    assert "Жара" in result


def test_alert_cold():
    result = _generate_pet_weather_alert(WEATHER_COLD)
    assert result is not None
    assert "Мороз" in result


def test_alert_ok():
    result = _generate_pet_weather_alert(WEATHER_OK)
    assert result is None


def test_alert_warm():
    weather = {**WEATHER_OK, "temp_c": 27, "uv": 7, "wind_kmph": 35}
    result = _generate_pet_weather_alert(weather)
    assert result is not None


def test_alert_mild_cold():
    weather = {**WEATHER_OK, "temp_c": -10, "wind_kmph": 5, "uv": 1}
    result = _generate_pet_weather_alert(weather)
    assert result is not None
    assert "Холод" in result


# ── weather_show ──


@pytest.mark.asyncio
@patch("bot.handlers.weather_handler.api_client")
async def test_weather_show_no_city(mock_api: MagicMock):
    mock_api.get_user_settings = AsyncMock(return_value={"city": ""})
    msg = _msg()
    await weather_show(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weather_handler.api_client")
async def test_weather_show_no_weather_data(mock_api: MagicMock):
    mock_api.get_user_settings = AsyncMock(return_value={"city": "Москва"})
    mock_api.get_weather = AsyncMock(return_value=None)
    msg = _msg()
    await weather_show(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weather_handler.api_client")
async def test_weather_show_ok(mock_api: MagicMock):
    mock_api.get_user_settings = AsyncMock(return_value={"city": "Москва"})
    mock_api.get_weather = AsyncMock(return_value=WEATHER_OK)
    mock_api.list_pets = AsyncMock(return_value=[PET])
    msg = _msg()
    await weather_show(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weather_handler.api_client")
async def test_weather_show_error(mock_api: MagicMock):
    mock_api.get_user_settings = AsyncMock(side_effect=RuntimeError("fail"))
    msg = _msg()
    await weather_show(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weather_handler.api_client")
async def test_weather_show_hot_alert(mock_api: MagicMock):
    mock_api.get_user_settings = AsyncMock(return_value={"city": "Москва"})
    mock_api.get_weather = AsyncMock(return_value=WEATHER_HOT)
    mock_api.list_pets = AsyncMock(return_value=[PET])
    msg = _msg()
    await weather_show(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weather_handler.api_client")
async def test_weather_show_no_pets(mock_api: MagicMock):
    mock_api.get_user_settings = AsyncMock(return_value={"city": "Москва"})
    mock_api.get_weather = AsyncMock(return_value=WEATHER_OK)
    mock_api.list_pets = AsyncMock(return_value=[])
    msg = _msg()
    await weather_show(msg)
    msg.answer.assert_awaited_once()


# ── weather_show_cb ──


@pytest.mark.asyncio
@patch("bot.handlers.weather_handler.api_client")
async def test_weather_show_cb_no_city(mock_api: MagicMock):
    mock_api.get_user_settings = AsyncMock(return_value={"city": ""})
    cb = _cb()
    await weather_show_cb(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.weather_handler.api_client")
async def test_weather_show_cb_ok(mock_api: MagicMock):
    mock_api.get_user_settings = AsyncMock(return_value={"city": "Москва"})
    mock_api.get_weather = AsyncMock(return_value=WEATHER_OK)
    mock_api.list_pets = AsyncMock(return_value=[])
    cb = _cb()
    await weather_show_cb(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.weather_handler.api_client")
async def test_weather_show_cb_error(mock_api: MagicMock):
    mock_api.get_user_settings = AsyncMock(side_effect=RuntimeError("fail"))
    cb = _cb()
    await weather_show_cb(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()
