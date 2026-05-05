"""Reminder tasks — send reminders, load/schedule reminders."""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select
from zoo_shared.db import async_session
from zoo_shared.db.models import Reminder

from worker.bot_sender import send_message

logger = logging.getLogger(__name__)


async def send_reminder(reminder_id: int):
    """Отправляет напоминание пользователю."""
    async with async_session() as session:
        reminder = await session.get(Reminder, reminder_id)
        if not reminder or not reminder.is_active:
            return

        pet = reminder.pet
        pet_name = pet.name if pet else "питомец"
        emoji = reminder.category_emoji

        text = (
            f"{emoji} <b>Напоминание!</b>\n\n"
            f"🐾 Питомец: {pet_name}\n"
            f"📌 {reminder.title}\n"
        )
        if reminder.description:
            text += f"📝 {reminder.description}\n"
        text += f"\n🔄 Повтор: {reminder.repeat_text}"

        await send_message(reminder.user_id, text)

        if reminder.repeat == "once":
            reminder.is_active = False
            await session.commit()


def schedule_reminder(scheduler: AsyncIOScheduler, reminder: Reminder):
    """Добавляет напоминание в планировщик."""
    job_id = f"reminder_{reminder.id}"

    existing = scheduler.get_job(job_id)
    if existing:
        existing.remove()

    if not reminder.is_active:
        return

    dt = reminder.remind_at

    if reminder.repeat == "once":
        if dt <= datetime.now():
            return
        trigger = DateTrigger(run_date=dt)
    elif reminder.repeat == "daily":
        trigger = CronTrigger(hour=dt.hour, minute=dt.minute)
    elif reminder.repeat == "weekly":
        trigger = CronTrigger(day_of_week=dt.weekday(), hour=dt.hour, minute=dt.minute)
    elif reminder.repeat == "monthly":
        trigger = CronTrigger(day=dt.day, hour=dt.hour, minute=dt.minute)
    elif reminder.repeat == "yearly":
        trigger = CronTrigger(month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute)
    else:
        return

    scheduler.add_job(
        send_reminder,
        trigger=trigger,
        args=[reminder.id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600,
    )


async def load_all_reminders(scheduler: AsyncIOScheduler):
    """Загружает все активные напоминания при старте."""
    async with async_session() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.is_active == True)  # noqa: E712
        )
        reminders = result.scalars().all()
        count = 0
        for rem in reminders:
            try:
                schedule_reminder(scheduler, rem)
                count += 1
            except Exception as e:
                logger.error("Ошибка планирования напоминания %s: %s", rem.id, e)
        logger.info("Загружено %d активных напоминаний", count)
