"""Tests for bot.handlers.weather_handler — weather display & pet alerts."""

from unittest.mock import AsyncMock, patch

from bot.handlers.weather_handler import (
    _build_weather_response,
    _generate_pet_weather_alert,
    weather_show,
    weather_show_cb,
)


class TestGeneratePetWeatherAlert:
    def _weather(self, temp_c=20, wind_kmph=10, uv=3, description="ясно"):
        return {
            "temp_c": temp_c,
            "wind_kmph": wind_kmph,
            "uv": uv,
            "description": description,
            "feels_like": temp_c - 2,
            "humidity": 50,
        }

    def test_comfortable_weather_no_alert(self):
        result = _generate_pet_weather_alert(self._weather())
        assert result is None

    def test_extreme_heat(self):
        result = _generate_pet_weather_alert(self._weather(temp_c=35))
        assert result is not None
        assert "Жара" in result

    def test_moderate_heat(self):
        result = _generate_pet_weather_alert(self._weather(temp_c=27))
        assert result is not None
        assert "Тепло" in result

    def test_extreme_cold(self):
        result = _generate_pet_weather_alert(self._weather(temp_c=-20))
        assert result is not None
        assert "Мороз" in result

    def test_moderate_cold(self):
        result = _generate_pet_weather_alert(self._weather(temp_c=-10))
        assert result is not None
        assert "Холод" in result

    def test_strong_wind(self):
        result = _generate_pet_weather_alert(self._weather(wind_kmph=55))
        assert result is not None
        assert "ветер" in result.lower() or "ветр" in result.lower() or "Ветер" in result or "дома" in result

    def test_moderate_wind(self):
        result = _generate_pet_weather_alert(self._weather(wind_kmph=35))
        assert result is not None
        assert "Ветрено" in result or "ветр" in result.lower()

    def test_high_uv(self):
        result = _generate_pet_weather_alert(self._weather(uv=9))
        assert result is not None
        assert "UV" in result

    def test_moderate_uv(self):
        result = _generate_pet_weather_alert(self._weather(uv=7))
        assert result is not None
        assert "UV" in result

    def test_multiple_alerts(self):
        result = _generate_pet_weather_alert(self._weather(temp_c=35, wind_kmph=55, uv=10))
        assert result is not None
        assert "Жара" in result
        assert "UV" in result


class TestBuildWeatherResponse:
    @patch("bot.handlers.weather_handler.api_client")
    async def test_no_city_set(self, mock_api):
        mock_api.get_user_settings = AsyncMock(return_value={"city": ""})
        text, error = await _build_weather_response(12345)
        assert text is None
        assert error is not None
        assert "Город не указан" in error

    @patch("bot.handlers.weather_handler.api_client")
    async def test_weather_api_fails(self, mock_api):
        mock_api.get_user_settings = AsyncMock(return_value={"city": "Москва"})
        mock_api.get_weather = AsyncMock(return_value=None)
        text, error = await _build_weather_response(12345)
        assert text is None
        assert error is not None
        assert "Москва" in error

    @patch("bot.handlers.weather_handler.api_client")
    async def test_success_no_pets(self, mock_api):
        mock_api.get_user_settings = AsyncMock(return_value={"city": "Москва"})
        mock_api.get_weather = AsyncMock(return_value={
            "temp_c": 20, "feels_like": 18, "humidity": 50,
            "wind_kmph": 10, "uv": 3, "description": "ясно",
        })
        mock_api.list_pets = AsyncMock(return_value=[])

        text, error = await _build_weather_response(12345)
        assert text is not None
        assert error is None
        assert "Москва" in text
        assert "20°C" in text
        assert "Добавьте питомцев" in text

    @patch("bot.handlers.weather_handler.api_client")
    async def test_success_with_pets_comfortable(self, mock_api):
        mock_api.get_user_settings = AsyncMock(return_value={"city": "Москва"})
        mock_api.get_weather = AsyncMock(return_value={
            "temp_c": 20, "feels_like": 18, "humidity": 50,
            "wind_kmph": 10, "uv": 3, "description": "ясно",
        })
        mock_api.list_pets = AsyncMock(return_value=[
            {"species": "собака", "species_emoji": "🐶"},
        ])

        text, error = await _build_weather_response(12345)
        assert text is not None
        assert "комфортная" in text

    @patch("bot.handlers.weather_handler.api_client")
    async def test_success_with_pets_alerts(self, mock_api):
        mock_api.get_user_settings = AsyncMock(return_value={"city": "Москва"})
        mock_api.get_weather = AsyncMock(return_value={
            "temp_c": 35, "feels_like": 38, "humidity": 80,
            "wind_kmph": 10, "uv": 3, "description": "жарко",
        })
        mock_api.list_pets = AsyncMock(return_value=[
            {"species": "собака", "species_emoji": "🐶"},
        ])

        text, error = await _build_weather_response(12345)
        assert text is not None
        assert "Предупреждения" in text

    @patch("bot.handlers.weather_handler.api_client")
    async def test_deduplicates_species(self, mock_api):
        mock_api.get_user_settings = AsyncMock(return_value={"city": "Москва"})
        mock_api.get_weather = AsyncMock(return_value={
            "temp_c": 35, "feels_like": 38, "humidity": 80,
            "wind_kmph": 10, "uv": 3, "description": "жарко",
        })
        mock_api.list_pets = AsyncMock(return_value=[
            {"species": "собака", "species_emoji": "🐶"},
            {"species": "собака", "species_emoji": "🐶"},
        ])

        text, error = await _build_weather_response(12345)
        assert text is not None
        assert text.count("Для собака") <= 1


class TestWeatherShowHandler:
    @patch("bot.handlers.weather_handler._build_weather_response")
    async def test_success(self, mock_build, mock_message):
        mock_build.return_value = ("Погода: ясно", None)
        await weather_show(mock_message)
        mock_message.answer.assert_awaited_once()
        assert "Погода" in mock_message.answer.call_args[0][0]

    @patch("bot.handlers.weather_handler._build_weather_response")
    async def test_error(self, mock_build, mock_message):
        mock_build.return_value = (None, "Город не указан")
        await weather_show(mock_message)
        mock_message.answer.assert_awaited_once()
        assert "Город не указан" in mock_message.answer.call_args[0][0]

    @patch("bot.handlers.weather_handler._build_weather_response")
    async def test_exception(self, mock_build, mock_message):
        mock_build.side_effect = Exception("boom")
        await weather_show(mock_message)
        mock_message.answer.assert_awaited_once()
        assert "ошибка" in mock_message.answer.call_args[0][0].lower() or "Не удалось" in mock_message.answer.call_args[0][0]


class TestWeatherShowCb:
    @patch("bot.handlers.weather_handler._build_weather_response")
    async def test_success(self, mock_build, mock_callback):
        mock_build.return_value = ("Погода: ясно", None)
        await weather_show_cb(mock_callback)
        mock_callback.message.edit_text.assert_awaited_once()
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.weather_handler._build_weather_response")
    async def test_error(self, mock_build, mock_callback):
        mock_build.return_value = (None, "Город не указан")
        await weather_show_cb(mock_callback)
        mock_callback.message.edit_text.assert_awaited_once()

    @patch("bot.handlers.weather_handler._build_weather_response")
    async def test_exception(self, mock_build, mock_callback):
        mock_build.side_effect = Exception("boom")
        await weather_show_cb(mock_callback)
        mock_callback.message.edit_text.assert_awaited_once()
        mock_callback.answer.assert_awaited_once()
