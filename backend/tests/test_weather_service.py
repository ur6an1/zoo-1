"""Tests for backend.services.weather — alert generation."""

from backend.services.weather import generate_pet_weather_alert


class TestGeneratePetWeatherAlert:
    def _weather(self, temp_c=20, wind_kmph=10, uv=3):
        return {
            "temp_c": temp_c, "feels_like": temp_c,
            "humidity": 50, "wind_kmph": wind_kmph,
            "uv": uv, "description": "Облачно",
        }

    def test_normal_no_alert(self):
        assert generate_pet_weather_alert(self._weather()) is None

    def test_heat_30(self):
        result = generate_pet_weather_alert(self._weather(temp_c=30))
        assert "Жара" in result

    def test_warm_25(self):
        result = generate_pet_weather_alert(self._weather(temp_c=25))
        assert "Тепло" in result

    def test_cold_minus15(self):
        result = generate_pet_weather_alert(self._weather(temp_c=-15))
        assert "Мороз" in result

    def test_cold_minus5(self):
        result = generate_pet_weather_alert(self._weather(temp_c=-5))
        assert "Холод" in result

    def test_strong_wind_50(self):
        result = generate_pet_weather_alert(self._weather(wind_kmph=50))
        assert "ветер" in result.lower()

    def test_moderate_wind_30(self):
        result = generate_pet_weather_alert(self._weather(wind_kmph=30))
        assert "Ветрено" in result

    def test_high_uv(self):
        result = generate_pet_weather_alert(self._weather(uv=8))
        assert "UV" in result

    def test_moderate_uv(self):
        result = generate_pet_weather_alert(self._weather(uv=6))
        assert "UV" in result

    def test_combined(self):
        result = generate_pet_weather_alert(self._weather(temp_c=35, wind_kmph=55, uv=9))
        assert "Жара" in result
        assert "ветер" in result.lower()
        assert "UV" in result

    def test_header_includes_description(self):
        result = generate_pet_weather_alert(self._weather(temp_c=35))
        assert "Облачно" in result
