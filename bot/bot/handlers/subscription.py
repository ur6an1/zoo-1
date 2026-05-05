"""Обработчики: настройки, админ-подписка, погодный город."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from zoo_shared.config import get_settings
from zoo_shared.db import async_session
from zoo_shared.db.models import UserSettings

from backend.backend.services.analytics import build_funnel_report, track_user_activity
from backend.backend.services.subscription import (
    PLAN_BASIC,
    PLAN_PRO,
    can_use_weather_notifications,
    get_or_create_settings,
    grant_premium,
    is_premium,
    revoke_premium,
)
from bot.keyboards.keyboards import back_to_menu_kb, cancel_kb, main_menu_kb, settings_menu_kb
from bot.states.states import WeatherCityForm

logger = logging.getLogger(__name__)
router = Router(name="subscription")


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message, state: FSMContext):
    """Главное меню настроек."""
    await state.clear()
    await track_user_activity(message.from_user.id, source="settings")
    await message.answer(
        "⚙️ <b>Настройки</b>\n\nВыберите раздел:",
        parse_mode="HTML",
        reply_markup=settings_menu_kb,
    )


@router.callback_query(F.data == "settings:menu")
async def settings_menu_cb(callback: CallbackQuery, state: FSMContext):
    """Inline-вход в меню настроек."""
    await state.clear()
    await track_user_activity(callback.from_user.id, source="settings")
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\nВыберите раздел:",
        parse_mode="HTML",
        reply_markup=settings_menu_kb,
    )
    await callback.answer()


@router.message(Command("funnel"))
async def cmd_funnel(message: Message):
    """Админская сводка по базовой воронке."""
    if message.from_user.id not in get_settings().ADMIN_IDS:
        return

    report = await build_funnel_report(days=7)
    await message.answer(f"<b>Analytics</b>\n\n{report}", parse_mode="HTML")


@router.message(Command("premium"))
async def cmd_grant_premium(message: Message):
    """Админ-команда: /premium {user_id} {days} [basic|pro]."""
    if message.from_user.id not in get_settings().ADMIN_IDS:
        return

    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "⚠️ Использование: <code>/premium {user_id} {days} [basic|pro]</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_user_id = int(args[1])
        days = int(args[2])
    except ValueError:
        await message.answer(
            "⚠️ user_id и days должны быть числами.\n"
            "Пример: <code>/premium 123456789 30 pro</code>",
            parse_mode="HTML",
        )
        return

    if days <= 0 or days > 3650:
        await message.answer("⚠️ Количество дней: от 1 до 3650.")
        return

    plan_tier = PLAN_PRO
    if len(args) >= 4:
        candidate = args[3].strip().lower()
        if candidate in (PLAN_BASIC, PLAN_PRO):
            plan_tier = candidate
        else:
            await message.answer("⚠️ Тариф должен быть basic или pro.")
            return

    try:
        result = await grant_premium(target_user_id, days, plan_tier=plan_tier)
        if result:
            await message.answer(
                "✅ Подписка выдана!\n\n"
                f"👤 Пользователь: <code>{target_user_id}</code>\n"
                f"📅 Срок: {days} дней\n"
                f"📦 Тариф: <b>{plan_tier.upper()}</b>",
                parse_mode="HTML",
            )
        else:
            await message.answer("😕 Не удалось выдать подписку.")
    except Exception as e:
        logger.error("Ошибка выдачи премиума: %s", e)
        await message.answer("😕 Ошибка при выдаче подписки.")


@router.message(Command("revoke"))
async def cmd_revoke_premium(message: Message):
    """Админ-команда: /revoke {user_id} — отзыв подписки."""
    if message.from_user.id not in get_settings().ADMIN_IDS:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "⚠️ Использование: <code>/revoke {user_id}</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer(
            "⚠️ user_id должен быть числом.\n"
            "Пример: <code>/revoke 123456789</code>",
            parse_mode="HTML",
        )
        return

    try:
        result = await revoke_premium(target_user_id)
        if result:
            await message.answer(
                f"✅ Подписка отозвана у пользователя <code>{target_user_id}</code>.",
                parse_mode="HTML",
            )
        else:
            await message.answer("😕 Не удалось отозвать подписку.")
    except Exception as e:
        logger.error("Ошибка отзыва премиума: %s", e)
        await message.answer("😕 Ошибка при отзыве подписки.")


@router.callback_query(F.data == "settings:sub_cancel")
async def cb_subscription_cancel(callback: CallbackQuery):
    if not await is_premium(callback.from_user.id):
        await callback.message.edit_text(
            "ℹ️ У вас нет активной подписки.",
            reply_markup=settings_menu_kb,
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "❌ <b>Отменить подписку</b>\n\n"
        "Подписка будет отключена немедленно.\n"
        "Вы уверены?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, отменить", callback_data="settings:sub_cancel_confirm")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="settings:menu")],
            ]
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "settings:sub_cancel_confirm")
async def cb_subscription_cancel_confirm(callback: CallbackQuery):
    await revoke_premium(callback.from_user.id)
    await callback.message.edit_text(
        "✅ Подписка отменена. Вы можете снова подключить её в любое время.",
        reply_markup=settings_menu_kb,
    )
    await callback.answer()


@router.callback_query(F.data == "settings:weather_city")
async def cb_weather_city(callback: CallbackQuery, state: FSMContext):
    """Начало ввода города для погоды."""
    settings = await get_or_create_settings(callback.from_user.id)
    current_city = settings.city or "не указан"

    await state.set_state(WeatherCityForm.waiting_city)
    await callback.message.edit_text(
        "🌤 <b>Настройка города для погоды</b>\n\n"
        f"Текущий город: <b>{current_city}</b>\n\n"
        "Введите название города (например: <b>Москва</b>):",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(WeatherCityForm.waiting_city, F.text)
async def weather_city_entered(message: Message, state: FSMContext):
    """Пользователь ввёл город — сохраняем."""
    city = message.text.strip()
    if not city or len(city) > 200:
        await message.answer(
            "⚠️ Введите корректное название города (до 200 символов).",
            reply_markup=cancel_kb,
        )
        return

    await state.clear()

    try:
        async with async_session() as session:
            result = await session.execute(
                select(UserSettings).where(UserSettings.user_id == message.from_user.id)
            )
            settings = result.scalar()
            if not settings:
                settings = UserSettings(user_id=message.from_user.id, city=city)
                session.add(settings)
            else:
                settings.city = city
            await session.commit()

        await message.answer(
            f"✅ Город сохранён: <b>{city}</b>\n\n"
            "Теперь вы можете получать погоду для этого города.",
            parse_mode="HTML",
            reply_markup=main_menu_kb,
        )
    except Exception as e:
        logger.error("Ошибка сохранения города: %s", e)
        await message.answer(
            "😕 Не удалось сохранить город. Попробуйте ещё раз.",
            reply_markup=back_to_menu_kb,
        )


@router.message(WeatherCityForm.waiting_city)
async def weather_city_invalid(message: Message):
    """Ожидали текст, получили другое."""
    await message.answer(
        "✏️ Пожалуйста, введите <b>название города</b> текстом.",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )


@router.callback_query(F.data == "settings:weather_toggle")
async def cb_weather_toggle(callback: CallbackQuery):
    """Включает/выключает погодные уведомления (доступно только на PRO)."""
    if not await can_use_weather_notifications(callback.from_user.id):
        await callback.message.edit_text(
            "🔒 <b>Погодные уведомления доступны только в тарифе PRO.</b>\n\n"
            "Откройте раздел подписки, чтобы подключить или повысить тариф.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⭐️ Подписка", callback_data="settings:subscription")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
                ]
            ),
        )
        await callback.answer("Доступно только на PRO", show_alert=True)
        return

    try:
        async with async_session() as session:
            result = await session.execute(
                select(UserSettings).where(UserSettings.user_id == callback.from_user.id)
            )
            settings = result.scalar()
            if not settings:
                settings = UserSettings(user_id=callback.from_user.id)
                session.add(settings)
                await session.flush()

            settings.weather_notify = not settings.weather_notify
            new_state = settings.weather_notify
            await session.commit()

        status = "включены ✅" if new_state else "выключены ❌"
        await callback.message.edit_text(
            f"🔔 Погодные уведомления <b>{status}</b>",
            parse_mode="HTML",
            reply_markup=settings_menu_kb,
        )
    except Exception as e:
        logger.error("Ошибка переключения уведомлений: %s", e)
        await callback.message.edit_text(
            "😕 Не удалось изменить настройку.",
            reply_markup=back_to_menu_kb,
        )

    await callback.answer()
