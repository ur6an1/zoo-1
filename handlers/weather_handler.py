"""Обработчики: погода и погодные предупреждения для питомцев."""

import logging
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database import async_session
from keyboards.keyboards import back_to_menu_kb, main_menu_kb
from models.models import Pet
from services.subscription import get_or_create_settings
from services.weather import generate_pet_weather_alert, get_weather

logger = logging.getLogger(__name__)
router = Router(name="weather_handler")


@router.message(F.text == "🌤 Погода")
async def weather_show(message: Message):
    """Показывает текущую погоду и предупреждения для питомцев."""
    user_id = message.from_user.id

    try:
        settings = await get_or_create_settings(user_id)
    except Exception as e:
        logger.error(f"Ошибка получения настроек пользователя: {e}")
        await message.answer(
            "😕 Не удалось загрузить настройки. Попробуйте позже.",
            reply_markup=main_menu_kb,
        )
        return

    if not settings.city:
        await message.answer(
            "🌤 <b>Погода</b>\n\n"
            "⚠️ Город не указан.\n\n"
            "Перейдите в <b>⚙️ Настройки → 🌤 Погода (город)</b>,\n"
            "чтобы указать свой город.",
            parse_mode="HTML",
            reply_markup=main_menu_kb,
        )
        return

    weather = await get_weather(settings.city)
    if not weather:
        await message.answer(
            f"😕 Не удалось получить погоду для города <b>{escape(settings.city)}</b>.\n\n"
            f"Проверьте название города в настройках.",
            parse_mode="HTML",
            reply_markup=main_menu_kb,
        )
        return

    # Основная информация о погоде
    lines = [
        f"🌤 <b>Погода в {escape(settings.city)}</b>\n",
        f"🌡 Температура: <b>{weather['temp_c']}°C</b> (ощущается {weather['feels_like']}°C)",
        f"💧 Влажность: {weather['humidity']}%",
        f"💨 Ветер: {weather['wind_kmph']} км/ч",
        f"☀️ UV-индекс: {weather['uv']}",
        f"📝 {weather['description']}",
    ]

    # Получаем питомцев пользователя
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Pet).where(Pet.user_id == user_id)
            )
            pets = result.scalars().all()
    except Exception as e:
        logger.error(f"Ошибка получения питомцев: {e}")
        pets = []

    # Генерируем предупреждения для каждого вида питомцев
    if pets:
        seen_species = set()
        alerts = []
        for pet in pets:
            if pet.species in seen_species:
                continue
            seen_species.add(pet.species)
            alert = generate_pet_weather_alert(weather, pet.species)
            if alert:
                alerts.append(f"\n{pet.species_emoji} <b>Для {escape(pet.species)}:</b>")
                # Убираем дублирующий заголовок из alert (он содержит погоду)
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

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=main_menu_kb,
    )


@router.callback_query(F.data == "weather:show")
async def weather_show_cb(callback: CallbackQuery):
    """Inline-вариант отображения погоды."""
    user_id = callback.from_user.id

    try:
        settings = await get_or_create_settings(user_id)
    except Exception as e:
        logger.error(f"Ошибка получения настроек пользователя: {e}")
        await callback.message.edit_text(
            "😕 Не удалось загрузить настройки. Попробуйте позже.",
            reply_markup=back_to_menu_kb,
        )
        await callback.answer()
        return

    if not settings.city:
        await callback.message.edit_text(
            "🌤 <b>Погода</b>\n\n"
            "⚠️ Город не указан.\n\n"
            "Перейдите в <b>⚙️ Настройки → 🌤 Погода (город)</b>,\n"
            "чтобы указать свой город.",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )
        await callback.answer()
        return

    weather = await get_weather(settings.city)
    if not weather:
        await callback.message.edit_text(
            f"😕 Не удалось получить погоду для города <b>{escape(settings.city)}</b>.\n\n"
            "Проверьте название города в настройках.",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )
        await callback.answer()
        return

    lines = [
        f"🌤 <b>Погода в {escape(settings.city)}</b>\n",
        f"🌡 Температура: <b>{weather['temp_c']}°C</b> (ощущается {weather['feels_like']}°C)",
        f"💧 Влажность: {weather['humidity']}%",
        f"💨 Ветер: {weather['wind_kmph']} км/ч",
        f"☀️ UV-индекс: {weather['uv']}",
        f"📝 {weather['description']}",
    ]

    try:
        async with async_session() as session:
            result = await session.execute(select(Pet).where(Pet.user_id == user_id))
            pets = result.scalars().all()
    except Exception as e:
        logger.error(f"Ошибка получения питомцев: {e}")
        pets = []

    if pets:
        seen_species = set()
        alerts = []
        for pet in pets:
            if pet.species in seen_species:
                continue
            seen_species.add(pet.species)
            alert = generate_pet_weather_alert(weather, pet.species)
            if alert:
                alerts.append(f"\n{pet.species_emoji} <b>Для {escape(pet.species)}:</b>")
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

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer()
