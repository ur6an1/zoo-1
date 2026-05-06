"""Обработчики: погода и погодные предупреждения для питомцев."""

import logging
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot import api_client
from bot.keyboards.keyboards import back_to_menu_kb, main_menu_kb

logger = logging.getLogger(__name__)
router = Router(name="weather_handler")


def _generate_pet_weather_alert(weather: dict, species: str = "собака") -> str | None:
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
            f"🔴 <b>Мороз {temp}°C!</b> Сократите прогулку. Мелким породам нужна одежда."
            " Протирайте лапы от реагентов."
        )
    elif temp <= -5:
        alerts.append(f"🟡 <b>Холод {temp}°C.</b> Одевайте питомца, если он мёрзнет.")

    if wind >= 50:
        alerts.append(f"🌪 <b>Сильный ветер {wind} км/ч!</b> Лучше остаться дома.")
    elif wind >= 30:
        alerts.append(f"💨 Ветрено ({wind} км/ч). Мелким питомцам может быть некомфортно.")

    if uv >= 8:
        alerts.append(
            f"☀️ <b>UV-индекс {uv}!</b> Избегайте прямого солнца,"
            " возможен солнечный ожог (особенно для светлых пород)."
        )
    elif uv >= 6:
        alerts.append(f"🌤 UV-индекс {uv}. Гуляйте в тени.")

    if not alerts:
        return None

    header = f"🌡 <b>Погода сейчас:</b> {temp}°C, {weather['description']}\n\n"
    return header + "\n".join(alerts)


async def _build_weather_response(user_id: int) -> tuple[str | None, str | None]:
    """Returns (text, error_text). Only one is set."""
    settings = await api_client.get_user_settings(user_id)
    city = settings.get("city") or ""

    if not city:
        return None, (
            "🌤 <b>Погода</b>\n\n"
            "⚠️ Город не указан.\n\n"
            "Перейдите в <b>⚙️ Настройки → 🌤 Погода (город)</b>,\n"
            "чтобы указать свой город."
        )

    weather = await api_client.get_weather(city)
    if not weather:
        return None, (
            f"😕 Не удалось получить погоду для города <b>{escape(city)}</b>.\n\n"
            "Проверьте название города в настройках."
        )

    lines = [
        f"🌤 <b>Погода в {escape(city)}</b>\n",
        f"🌡 Температура: <b>{weather['temp_c']}°C</b> (ощущается {weather['feels_like']}°C)",
        f"💧 Влажность: {weather['humidity']}%",
        f"💨 Ветер: {weather['wind_kmph']} км/ч",
        f"☀️ UV-индекс: {weather['uv']}",
        f"📝 {weather['description']}",
    ]

    try:
        pets = await api_client.list_pets(user_id)
    except Exception as e:
        logger.error(f"Ошибка получения питомцев: {e}")
        pets = []

    if pets:
        seen_species: set[str] = set()
        alerts: list[str] = []
        for pet in pets:
            species = pet.get("species", "")
            if species in seen_species:
                continue
            seen_species.add(species)
            alert = _generate_pet_weather_alert(weather, species)
            if alert:
                species_emoji = pet.get("species_emoji", "🐾")
                alerts.append(f"\n{species_emoji} <b>Для {escape(species)}:</b>")
                alert_lines = alert.split("\n")
                for line in alert_lines:
                    if line.strip() and not line.startswith("🌡"):
                        alerts.append(line)

        if alerts:
            lines.append("\n─────────────────")
            lines.append("🐾 <b>Предупреждения для питомцев:</b>")
            lines.extend(alerts)
        else:
            lines.append("\n✅ Погода комфортная для прогулок с питомцами!")
    else:
        lines.append(
            "\n💡 Добавьте питомцев в разделе 🐾 Мои питомцы,\n"
            "чтобы получать персональные погодные советы."
        )

    return "\n".join(lines), None


@router.message(F.text == "🌤 Погода")
async def weather_show(message: Message):
    """Показывает текущую погоду и предупреждения для питомцев."""
    try:
        text, error = await _build_weather_response(message.from_user.id)
    except Exception as e:
        logger.error(f"Ошибка получения настроек пользователя: {e}")
        await message.answer(
            "😕 Не удалось загрузить настройки. Попробуйте позже.",
            reply_markup=main_menu_kb,
        )
        return

    if error:
        await message.answer(error, parse_mode="HTML", reply_markup=main_menu_kb)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb)


@router.callback_query(F.data == "weather:show")
async def weather_show_cb(callback: CallbackQuery):
    """Inline-вариант отображения погоды."""
    try:
        text, error = await _build_weather_response(callback.from_user.id)
    except Exception as e:
        logger.error(f"Ошибка получения настроек пользователя: {e}")
        await callback.message.edit_text(
            "😕 Не удалось загрузить настройки. Попробуйте позже.",
            reply_markup=back_to_menu_kb,
        )
        await callback.answer()
        return

    if error:
        await callback.message.edit_text(error, parse_mode="HTML", reply_markup=back_to_menu_kb)
    else:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_kb)

    await callback.answer()
