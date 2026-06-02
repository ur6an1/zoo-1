"""Сервис погоды для уведомлений владельцев питомцев."""

import logging

import aiohttp

logger = logging.getLogger(__name__)

WTTR_URL = "https://wttr.in/{city}?format=j1&lang=ru"


async def get_weather(city: str) -> dict | None:
    """Получает погоду через wttr.in (бесплатный, без ключа).

    Returns:
        {"temp_c": int, "feels_like": int, "humidity": int,
         "wind_kmph": int, "description": str, "uv": int} или None
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                WTTR_URL.format(city=city),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json(content_type=None)
                current = data["current_condition"][0]
                return {
                    "temp_c": int(current["temp_C"]),
                    "feels_like": int(current["FeelsLikeC"]),
                    "humidity": int(current["humidity"]),
                    "wind_kmph": int(current["windspeedKmph"]),
                    "description": (
                        current.get("lang_ru", [{}])[0].get(
                            "value", current.get("weatherDesc", [{}])[0].get("value", "")
                        )
                    ),
                    "uv": int(current.get("uvIndex", 0)),
                }
    except Exception as e:
        logger.error(f"Ошибка получения погоды для {city}: {e}")
        return None


def generate_pet_weather_alert(weather: dict, species: str = "собака") -> str | None:
    """Генерирует предупреждение для питомца на основе погоды."""
    alerts = []
    temp = weather["temp_c"]
    wind = weather["wind_kmph"]
    uv = weather["uv"]

    if temp >= 30:
        alerts.append(
            f"🔴 <b>Жара {temp}°C!</b> Не гуляйте в пик жары (12-16ч). Берите воду."
            " Проверяйте лапы на горячем асфальте!"
        )
    elif temp >= 25:
        alerts.append(f"🟡 <b>Тепло {temp}°C.</b> Гуляйте в тени, берите воду.")
    elif temp <= -15:
        alerts.append(
            f"🔴 <b>Мороз {temp}°C!</b> Сократите прогулку. Мелким породам нужна одежда. Протирайте лапы от реагентов."
        )
    elif temp <= -5:
        alerts.append(f"🟡 <b>Холод {temp}°C.</b> Одевайте питомца, если он мёрзнет.")

    if wind >= 50:
        alerts.append(f"🌪 <b>Сильный ветер {wind} км/ч!</b> Лучше остаться дома.")
    elif wind >= 30:
        alerts.append(f"💨 Ветрено ({wind} км/ч). Мелким питомцам может быть некомфортно.")

    if uv >= 8:
        alerts.append(
            f"☀️ <b>UV-индекс {uv}!</b> Избегайте прямого солнца, возможен солнечный ожог (особенно для светлых пород)."
        )
    elif uv >= 6:
        alerts.append(f"🌤 UV-индекс {uv}. Гуляйте в тени.")

    if not alerts:
        return None

    header = f"🌡 <b>Погода сейчас:</b> {temp}°C, {weather['description']}\n\n"
    return header + "\n".join(alerts)
