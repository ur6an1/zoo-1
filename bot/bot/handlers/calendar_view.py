"""Обработчики: календарь событий (напоминания, прививки, визиты к ветеринару)."""

import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from zoo_shared.db import async_session
from zoo_shared.db.models import Pet, Reminder, Vaccination, VetVisit

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
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=back_to_menu_kb
        )
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
    future_30 = today + timedelta(days=30)

    events: list[tuple[datetime, str]] = []

    async with async_session() as session:
        # Питомцы пользователя
        pets_result = await session.execute(
            select(Pet).where(Pet.user_id == user_id)
        )
        pets = pets_result.scalars().all()
        pet_map = {p.id: p for p in pets}
        pet_ids = [p.id for p in pets]

        if not pet_ids:
            return (
                "📅 <b>Календарь</b>\n\n"
                "😕 У вас нет питомцев.\n"
                "Добавьте питомца, чтобы увидеть события."
            )

        # Активные напоминания (ближайшие 30 дней)
        reminders_result = await session.execute(
            select(Reminder).where(
                Reminder.user_id == user_id,
                Reminder.is_active == True,  # noqa: E712
                Reminder.remind_at >= now,
                Reminder.remind_at <= datetime(future_30.year, future_30.month, future_30.day, 23, 59, 59),
            )
        )
        reminders = reminders_result.scalars().all()

        for rem in reminders:
            pet = pet_map.get(rem.pet_id)
            pet_label = f"{pet.species_emoji} {pet.name}" if pet else "?"
            events.append((
                rem.remind_at,
                f"{rem.category_emoji} <b>{rem.title}</b>\n"
                f"   🐾 {pet_label} | ⏰ {rem.remind_at.strftime('%H:%M')} | 🔄 {rem.repeat_text}",
            ))

        # Предстоящие прививки
        vaccinations_result = await session.execute(
            select(Vaccination).where(
                Vaccination.pet_id.in_(pet_ids),
                Vaccination.next_date != None,  # noqa: E711
                Vaccination.next_date >= today,
            )
        )
        vaccinations = vaccinations_result.scalars().all()

        for v in vaccinations:
            pet = pet_map.get(v.pet_id)
            pet_label = f"{pet.species_emoji} {pet.name}" if pet else "?"
            event_dt = datetime(v.next_date.year, v.next_date.month, v.next_date.day)
            events.append((
                event_dt,
                f"💉 <b>{v.name}</b> (следующая)\n"
                f"   🐾 {pet_label} | 📅 {format_date(v.next_date)}",
            ))

        # Последние визиты к ветеринару (5 шт.)
        vetvisits_result = await session.execute(
            select(VetVisit)
            .where(VetVisit.pet_id.in_(pet_ids))
            .order_by(VetVisit.visit_date.desc())
            .limit(5)
        )
        vet_visits = vetvisits_result.scalars().all()

        for vv in vet_visits:
            pet = pet_map.get(vv.pet_id)
            pet_label = f"{pet.species_emoji} {pet.name}" if pet else "?"
            event_dt = datetime(vv.visit_date.year, vv.visit_date.month, vv.visit_date.day)
            diag = vv.diagnosis[:60] + "..." if len(vv.diagnosis) > 60 else vv.diagnosis
            diag_text = f" — {diag}" if diag else ""
            events.append((
                event_dt,
                f"🏥 <b>Визит к ветеринару</b>{diag_text}\n"
                f"   🐾 {pet_label} | 📅 {format_date(vv.visit_date)}",
            ))

    # Сортировка по дате
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
