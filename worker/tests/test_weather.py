"""Tests for worker/worker/tasks/weather.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from worker.tasks.weather import _generate_alert

# ── _generate_alert ──


def test_generate_alert_extreme_heat():
    weather = {"temp_c": 35, "wind_kmph": 10, "uv": 3}
    result = _generate_alert(weather)
    assert result is not None
    assert "Жара" in result


def test_generate_alert_warm():
    weather = {"temp_c": 27, "wind_kmph": 10, "uv": 3}
    result = _generate_alert(weather)
    assert result is not None
    assert "Тепло" in result


def test_generate_alert_extreme_cold():
    weather = {"temp_c": -20, "wind_kmph": 10, "uv": 0}
    result = _generate_alert(weather)
    assert result is not None
    assert "Мороз" in result


def test_generate_alert_cold():
    weather = {"temp_c": -8, "wind_kmph": 10, "uv": 0}
    result = _generate_alert(weather)
    assert result is not None
    assert "Холод" in result


def test_generate_alert_strong_wind():
    weather = {"temp_c": 20, "wind_kmph": 55, "uv": 3}
    result = _generate_alert(weather)
    assert result is not None
    assert "ветер" in result.lower()


def test_generate_alert_moderate_wind():
    weather = {"temp_c": 20, "wind_kmph": 35, "uv": 3}
    result = _generate_alert(weather)
    assert result is not None
    assert "Ветрено" in result


def test_generate_alert_high_uv():
    weather = {"temp_c": 20, "wind_kmph": 10, "uv": 9}
    result = _generate_alert(weather)
    assert result is not None
    assert "UV" in result


def test_generate_alert_moderate_uv():
    weather = {"temp_c": 20, "wind_kmph": 10, "uv": 7}
    result = _generate_alert(weather)
    assert result is not None
    assert "UV" in result


def test_generate_alert_no_alerts():
    weather = {"temp_c": 20, "wind_kmph": 10, "uv": 3}
    result = _generate_alert(weather)
    assert result is None


def test_generate_alert_multiple():
    weather = {"temp_c": 35, "wind_kmph": 55, "uv": 9}
    result = _generate_alert(weather)
    assert result is not None
    assert "Жара" in result
    assert "UV" in result


# ── _get_weather ──


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_get_weather_ok(mock_session_cls):
    from worker.tasks.weather import _get_weather

    resp = AsyncMock()
    resp.status = 200
    resp.json = AsyncMock(return_value={
        "current_condition": [{
            "temp_C": "25",
            "FeelsLikeC": "27",
            "humidity": "60",
            "windspeedKmph": "15",
            "uvIndex": "5",
            "lang_ru": [{"value": "Ясно"}],
            "weatherDesc": [{"value": "Clear"}],
        }]
    })

    session = AsyncMock()
    session.get = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=resp),
        __aexit__=AsyncMock(return_value=False),
    ))

    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await _get_weather("Moscow")
    assert result is not None
    assert result["temp_c"] == 25


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_get_weather_not_200(mock_session_cls):
    from worker.tasks.weather import _get_weather

    resp = AsyncMock()
    resp.status = 500

    session = AsyncMock()
    session.get = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=resp),
        __aexit__=AsyncMock(return_value=False),
    ))

    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await _get_weather("Moscow")
    assert result is None


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_get_weather_exception(mock_session_cls):
    from worker.tasks.weather import _get_weather

    mock_session_cls.return_value.__aenter__ = AsyncMock(
        side_effect=RuntimeError("network error")
    )
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await _get_weather("Moscow")
    assert result is None


# ── send_weather_notifications ──


@pytest.mark.asyncio
@patch("worker.tasks.weather.send_message", new_callable=AsyncMock, return_value=True)
@patch("worker.tasks.weather._get_weather", new_callable=AsyncMock)
@patch("worker.tasks.weather.async_session")
async def test_send_weather_notifications_with_alerts(
    mock_session_maker, mock_get_weather, mock_send
):
    from worker.tasks.weather import send_weather_notifications

    user_settings = MagicMock()
    user_settings.user_id = 42
    user_settings.city = "Moscow"

    session = AsyncMock()
    users_result = MagicMock()
    users_result.scalars.return_value.all.return_value = [user_settings]

    pets_result = MagicMock()
    pets_result.all.return_value = [(42, "собака")]

    session.execute = AsyncMock(side_effect=[users_result, pets_result])
    mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_get_weather.return_value = {"temp_c": 35, "wind_kmph": 10, "uv": 3}

    await send_weather_notifications()
    mock_send.assert_awaited_once()


@pytest.mark.asyncio
@patch("worker.tasks.weather.send_message", new_callable=AsyncMock)
@patch("worker.tasks.weather._get_weather", new_callable=AsyncMock, return_value=None)
@patch("worker.tasks.weather.async_session")
async def test_send_weather_notifications_no_weather(
    mock_session_maker, mock_get_weather, mock_send
):
    from worker.tasks.weather import send_weather_notifications

    user_settings = MagicMock()
    user_settings.user_id = 42
    user_settings.city = "Moscow"

    session = AsyncMock()
    users_result = MagicMock()
    users_result.scalars.return_value.all.return_value = [user_settings]

    pets_result = MagicMock()
    pets_result.all.return_value = []

    session.execute = AsyncMock(side_effect=[users_result, pets_result])
    mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

    await send_weather_notifications()
    mock_send.assert_not_awaited()


@pytest.mark.asyncio
@patch("worker.tasks.weather.send_message", new_callable=AsyncMock)
@patch("worker.tasks.weather._get_weather", new_callable=AsyncMock)
@patch("worker.tasks.weather.async_session")
async def test_send_weather_notifications_no_alerts(
    mock_session_maker, mock_get_weather, mock_send
):
    from worker.tasks.weather import send_weather_notifications

    user_settings = MagicMock()
    user_settings.user_id = 42
    user_settings.city = "Moscow"

    session = AsyncMock()
    users_result = MagicMock()
    users_result.scalars.return_value.all.return_value = [user_settings]

    pets_result = MagicMock()
    pets_result.all.return_value = [(42, "собака")]

    session.execute = AsyncMock(side_effect=[users_result, pets_result])
    mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_get_weather.return_value = {"temp_c": 20, "wind_kmph": 10, "uv": 3}

    await send_weather_notifications()
    mock_send.assert_not_awaited()


@pytest.mark.asyncio
@patch("worker.tasks.weather.send_message", new_callable=AsyncMock)
@patch("worker.tasks.weather._get_weather", new_callable=AsyncMock)
@patch("worker.tasks.weather.async_session")
async def test_send_weather_notifications_no_users(
    mock_session_maker, mock_get_weather, mock_send
):
    from worker.tasks.weather import send_weather_notifications

    session = AsyncMock()
    users_result = MagicMock()
    users_result.scalars.return_value.all.return_value = []

    session.execute = AsyncMock(side_effect=[users_result])
    mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

    await send_weather_notifications()
    mock_send.assert_not_awaited()
