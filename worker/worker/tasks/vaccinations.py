"""Vaccination check — daily notification about overdue/upcoming vaccinations."""

import logging
from datetime import date, timedelta

from sqlalchemy import select
from zoo_shared.db import async_session
from zoo_shared.db.models import Pet, Vaccination

from worker.bot_sender import send_message

logger = logging.getLogger(__name__)


async def check_vaccination_schedule():
    """Проверяет просроченные и предстоящие прививки."""
    today = date.today()
    soon = today + timedelta(days=7)

    async with async_session() as session:
        overdue_result = await session.execute(
            select(Vaccination).where(
                Vaccination.next_date != None,  # noqa: E711
                Vaccination.next_date < today,
            )
        )
        overdue = overdue_result.scalars().all()

        upcoming_result = await session.execute(
            select(Vaccination).where(
                Vaccination.next_date != None,  # noqa: E711
                Vaccination.next_date >= today,
                Vaccination.next_date <= soon,
            )
        )
        upcoming = upcoming_result.scalars().all()

        notifications: dict[int, list[str]] = {}

        for v in overdue:
            pet = await session.get(Pet, v.pet_id)
            if not pet:
                continue
            uid = pet.user_id
            if uid not in notifications:
                notifications[uid] = []
            days_overdue = (today - v.next_date).days
            notifications[uid].append(f"🔴 <b>{pet.name}</b>: прививка «{v.name}» просрочена на {days_overdue} дн.!")

        for v in upcoming:
            pet = await session.get(Pet, v.pet_id)
            if not pet:
                continue
            uid = pet.user_id
            if uid not in notifications:
                notifications[uid] = []
            days_left = (v.next_date - today).days
            if days_left == 0:
                notifications[uid].append(f"🟡 <b>{pet.name}</b>: прививка «{v.name}» — <b>сегодня!</b>")
            else:
                notifications[uid].append(f"🟡 <b>{pet.name}</b>: прививка «{v.name}» через {days_left} дн.")

    for user_id, lines in notifications.items():
        text = "💉 <b>Напоминание о прививках</b>\n\n" + "\n".join(lines)
        await send_message(user_id, text)

    logger.info("Проверка прививок: %d уведомлений", sum(len(v) for v in notifications.values()))
