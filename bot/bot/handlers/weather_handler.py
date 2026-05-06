"""Обработчики: погода и погодные предупреждения для питомцев."""

import logging
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from backend.backend.services.weather import generate_pet_weather_alert, get_weather
from bot import api_client
from bot.keyboards.keyboards import back_to_menu_kb, main_menu_kb

logger = logging.getLogger(__name__)
router = Router(name="weather_handler")


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

    weather = await get_weather(city)
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
            alert = generate_pet_weather_alert(weather, species)
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
