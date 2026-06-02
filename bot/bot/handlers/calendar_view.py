"""Обработчики: календарь событий (напоминания, прививки, визиты к ветеринару)."""

import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot import api_client
from bot.keyboards.keyboards import back_to_menu_kb, main_menu_kb
from bot.utils.helpers import format_date

logger = logging.getLogger(__name__)
router = Router(name="calendar")


@router.message(F.text == "📅 Календарь")
async def calendar_menu(message: Message):
    """Показывает сводный календарь всех событий."""
    try:
        text = await _build_calendar(message.from_user.id)
        await message.answer(text, parse_mode="HTML", reply_markup=back_to_menu_kb)
    except Exception as e:
        logger.error(f"Ошибка календаря: {e}")
        await message.answer(
            "😕 Не удалось загрузить календарь. Попробуйте позже.",
            reply_markup=main_menu_kb,
        )


@router.callback_query(F.data == "calendar:view")
async def cb_calendar_view(callback: CallbackQuery):
    """Inline-вариант отображения календаря."""
    try:
        text = await _build_calendar(callback.from_user.id)
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_kb)
    except Exception as e:
        logger.error(f"Ошибка календаря: {e}")
        await callback.message.edit_text(
            "😕 Не удалось загрузить календарь. Попробуйте позже.",
            reply_markup=back_to_menu_kb,
        )
    await callback.answer()


async def _build_calendar(user_id: int) -> str:
    """Собирает все предстоящие события в единый текст-таймлайн."""
    now = datetime.now()
    today = now.date()

    data = await api_client.get_medical_calendar(user_id)

    if not data.get("pets"):
        return "📅 <b>Календарь</b>\n\n😕 У вас нет питомцев.\nДобавьте питомца, чтобы увидеть события."

    events: list[tuple[datetime, str]] = []

    for rem in data.get("reminders", []):
        try:
            remind_at = datetime.fromisoformat(rem["remind_at"])
        except (ValueError, KeyError):
            continue
        pet_name = rem.get("pet_name", "?")
        cat_emoji = rem.get("category_emoji", "🔔")
        events.append(
            (
                remind_at,
                f"{cat_emoji} <b>{rem['title']}</b>\n"
                f"   🐾 {pet_name} | ⏰ {remind_at.strftime('%H:%M')} | 🔄 {rem.get('repeat_text', '')}",
            )
        )

    for v in data.get("vaccinations", []):
        next_date_str = v.get("next_date")
        if not next_date_str:
            continue
        try:
            nd = datetime.fromisoformat(next_date_str)
        except (ValueError, TypeError):
            continue
        if nd.date() < today:
            continue
        pet_name = v.get("pet_name", "?")
        events.append(
            (
                nd,
                f"💉 <b>{v['name']}</b> (следующая)\n   🐾 {pet_name} | 📅 {format_date(nd.date())}",
            )
        )

    for vv in data.get("vet_visits", [])[:5]:
        try:
            vd = datetime.fromisoformat(vv["visit_date"])
        except (ValueError, KeyError):
            continue
        pet_name = vv.get("pet_name", "?")
        diagnosis = vv.get("diagnosis", "")
        diag = diagnosis[:60] + "..." if len(diagnosis) > 60 else diagnosis
        diag_text = f" — {diag}" if diag else ""
        events.append(
            (
                vd,
                f"🏥 <b>Визит к ветеринару</b>{diag_text}\n   🐾 {pet_name} | 📅 {format_date(vd.date())}",
            )
        )

    events.sort(key=lambda e: e[0])

    if not events:
        return (
            "📅 <b>Календарь</b>\n\n"
            "🎉 Нет предстоящих событий.\n\n"
            "Добавьте напоминания, прививки или визиты к ветеринару,\n"
            "и они отобразятся здесь."
        )

    lines = ["📅 <b>Календарь событий</b>\n"]

    current_date_label = ""
    for event_dt, event_text in events:
        d = event_dt.date()
        date_label = format_date(d)
        if d == today:
            date_label = f"📌 Сегодня ({date_label})"
        elif d == today + timedelta(days=1):
            date_label = f"➡️ Завтра ({date_label})"

        if date_label != current_date_label:
            current_date_label = date_label
            lines.append(f"\n<b>{date_label}</b>")

        lines.append(event_text)

    total = len(events)
    lines.append(f"\n📊 Всего событий: <b>{total}</b>")

    return "\n".join(lines)
