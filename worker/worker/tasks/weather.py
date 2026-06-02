"""Weather notifications — morning weather alerts for pet owners."""

import logging

from sqlalchemy import select
from zoo_shared.db import async_session
from zoo_shared.db.models import Pet, UserSettings

from worker.bot_sender import send_message

logger = logging.getLogger(__name__)


async def _get_weather(city: str) -> dict | None:
    """Fetch weather for city via wttr.in."""
    import aiohttp

    try:
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://wttr.in/{city}?format=j1&lang=ru", timeout=aiohttp.ClientTimeout(total=10)) as resp:
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
        logger.error("Ошибка получения погоды для %s: %s", city, e)
        return None


def _generate_alert(weather: dict, species: str = "собака") -> str | None:
    """Generate pet weather alert text."""
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
    return "\n".join(alerts)


async def send_weather_notifications():
    """Отправляет погодные уведомления пользователям."""
    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(
                UserSettings.weather_notify == True,  # noqa: E712
                UserSettings.city != "",
                UserSettings.is_premium == True,  # noqa: E712
                UserSettings.plan_tier == "pro",
            )
        )
        users = result.scalars().all()
        user_ids = [u.user_id for u in users]

        species_by_user: dict[int, set[str]] = {}
        if user_ids:
            pet_rows = await session.execute(select(Pet.user_id, Pet.species).where(Pet.user_id.in_(user_ids)))
            for user_id, species in pet_rows.all():
                species_by_user.setdefault(user_id, set()).add(species)

    sent = 0
    for user_settings in users:
        weather = await _get_weather(user_settings.city)
        if not weather:
            continue

        species_set = species_by_user.get(user_settings.user_id, {"собака"})
        alerts = []
        for species in species_set:
            alert = _generate_alert(weather, species)
            if alert:
                alerts.append(alert)

        if alerts:
            text = f"🌤 <b>Утренний прогноз — {user_settings.city}</b>\n\n" + "\n\n".join(alerts)
            if await send_message(user_settings.user_id, text):
                sent += 1

    logger.info("Погодные уведомления: %d отправлено", sent)
