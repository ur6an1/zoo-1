"""Обработчики: настройки, админ-подписка, погодный город."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from zoo_shared.config import get_settings

from bot import api_client
from bot.keyboards.keyboards import back_to_menu_kb, cancel_kb, main_menu_kb, settings_menu_kb
from bot.states.states import WeatherCityForm

logger = logging.getLogger(__name__)
router = Router(name="subscription")

PLAN_BASIC = "basic"
PLAN_PRO = "pro"


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message, state: FSMContext):
    """Главное меню настроек."""
    await state.clear()
    await api_client.track_user_activity(message.from_user.id, source="settings")
    await message.answer(
        "⚙️ <b>Настройки</b>\n\nВыберите раздел:",
        parse_mode="HTML",
        reply_markup=settings_menu_kb,
    )


@router.callback_query(F.data == "settings:menu")
async def settings_menu_cb(callback: CallbackQuery, state: FSMContext):
    """Inline-вход в меню настроек."""
    await state.clear()
    await api_client.track_user_activity(callback.from_user.id, source="settings")
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

    report = await api_client.get_funnel_report(days=7)
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
            "⚠️ user_id и days должны быть числами.\nПример: <code>/premium 123456789 30 pro</code>",
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
        result = await api_client.grant_premium(target_user_id, days, plan_tier=plan_tier)
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
            "⚠️ user_id должен быть числом.\nПример: <code>/revoke 123456789</code>",
            parse_mode="HTML",
        )
        return

    try:
        result = await api_client.revoke_premium(target_user_id)
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
    sub = await api_client.get_subscription_status(callback.from_user.id)
    if not sub.get("is_premium"):
        await callback.message.edit_text(
            "ℹ️ У вас нет активной подписки.",
            reply_markup=settings_menu_kb,
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "❌ <b>Отменить подписку</b>\n\nПодписка будет отключена немедленно.\nВы уверены?",
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
    await api_client.revoke_premium(callback.from_user.id)
    await callback.message.edit_text(
        "✅ Подписка отменена. Вы можете снова подключить её в любое время.",
        reply_markup=settings_menu_kb,
    )
    await callback.answer()


@router.callback_query(F.data == "settings:weather_city")
async def cb_weather_city(callback: CallbackQuery, state: FSMContext):
    """Начало ввода города для погоды."""
    sub = await api_client.get_subscription_status(callback.from_user.id)
    current_city = sub.get("city") or "не указан"

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
        await api_client.update_user_settings(message.from_user.id, city=city)
        await message.answer(
            f"✅ Город сохранён: <b>{city}</b>\n\nТеперь вы можете получать погоду для этого города.",
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
    can_weather = await api_client.check_feature_permission(callback.from_user.id, "weather_notifications")
    if not can_weather:
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
        result = await api_client.toggle_weather_notify(callback.from_user.id)
        new_state = result.get("weather_notify", False)

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
