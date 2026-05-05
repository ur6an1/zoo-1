"""Планировщик напоминаний на основе APScheduler."""

import logging
from datetime import datetime, date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from database import async_session
from models.models import Reminder, Vaccination, Pet
from config import BOT_TIMEZONE

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=BOT_TIMEZONE)

# Ссылка на экземпляр бота — устанавливается при запуске
_bot = None


def set_bot(bot):
    """Сохраняет ссылку на бота для отправки сообщений."""
    global _bot
    _bot = bot


async def send_reminder(reminder_id: int):
    """Отправляет напоминание пользователю."""
    if _bot is None:
        logger.error("Бот не инициализирован для отправки напоминаний")
        return

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

        try:
            await _bot.send_message(
                chat_id=reminder.user_id,
                text=text,
                parse_mode="HTML",
            )
            logger.info(f"Напоминание {reminder_id} отправлено пользователю {reminder.user_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания {reminder_id}: {e}")

        # Для разовых напоминаний — деактивируем
        if reminder.repeat == "once":
            reminder.is_active = False
            await session.commit()


def schedule_reminder(reminder: Reminder):
    """Добавляет напоминание в планировщик."""
    job_id = f"reminder_{reminder.id}"

    # Удаляем старое задание, если есть
    existing = scheduler.get_job(job_id)
    if existing:
        existing.remove()

    if not reminder.is_active:
        return

    dt = reminder.remind_at

    if reminder.repeat == "once":
        # Если время уже прошло — не планируем
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
    logger.info(f"Запланировано напоминание {job_id}: {reminder.title} ({reminder.repeat_text})")


def remove_reminder_job(reminder_id: int):
    """Удаляет задание из планировщика."""
    job_id = f"reminder_{reminder_id}"
    existing = scheduler.get_job(job_id)
    if existing:
        existing.remove()
        logger.info(f"Удалено задание {job_id}")


async def load_all_reminders():
    """Загружает все активные напоминания из БД при старте."""
    async with async_session() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.is_active == True)  # noqa: E712
        )
        reminders = result.scalars().all()
        count = 0
        for rem in reminders:
            try:
                schedule_reminder(rem)
                count += 1
            except Exception as e:
                logger.error(f"Ошибка планирования напоминания {rem.id}: {e}")
        logger.info(f"Загружено {count} активных напоминаний")


# ══════════════════════════════════════════════
#  ЕЖЕДНЕВНАЯ ПРОВЕРКА ПРИВИВОК
# ══════════════════════════════════════════════


async def check_vaccination_schedule():
    """Проверяет просроченные и предстоящие прививки, уведомляет владельцев."""
    if _bot is None:
        return

    today = date.today()
    soon = today + timedelta(days=7)  # предупреждать за 7 дней

    async with async_session() as session:
        # Просроченные прививки
        overdue_result = await session.execute(
            select(Vaccination).where(
                Vaccination.next_date != None,  # noqa: E711
                Vaccination.next_date < today,
            )
        )
        overdue = overdue_result.scalars().all()

        # Скоро предстоящие
        upcoming_result = await session.execute(
            select(Vaccination).where(
                Vaccination.next_date != None,  # noqa: E711
                Vaccination.next_date >= today,
                Vaccination.next_date <= soon,
            )
        )
        upcoming = upcoming_result.scalars().all()

        # Собираем по user_id
        notifications: dict[int, list[str]] = {}

        for v in overdue:
            pet = await session.get(Pet, v.pet_id)
            if not pet:
                continue
            uid = pet.user_id
            if uid not in notifications:
                notifications[uid] = []
            days_overdue = (today - v.next_date).days
            notifications[uid].append(
                f"🔴 <b>{pet.name}</b>: прививка «{v.name}» просрочена на {days_overdue} дн.!"
            )

        for v in upcoming:
            pet = await session.get(Pet, v.pet_id)
            if not pet:
                continue
            uid = pet.user_id
            if uid not in notifications:
                notifications[uid] = []
            days_left = (v.next_date - today).days
            if days_left == 0:
                notifications[uid].append(
                    f"🟡 <b>{pet.name}</b>: прививка «{v.name}» — <b>сегодня!</b>"
                )
            else:
                notifications[uid].append(
                    f"🟡 <b>{pet.name}</b>: прививка «{v.name}» через {days_left} дн."
                )

    for user_id, lines in notifications.items():
        text = "💉 <b>Напоминание о прививках</b>\n\n" + "\n".join(lines)
        try:
            await _bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о прививках user={user_id}: {e}")

    logger.info(f"Проверка прививок: {sum(len(v) for v in notifications.values())} уведомлений")


def schedule_daily_vaccination_check():
    """Запланировать ежедневную проверку прививок в 9:00."""
    scheduler.add_job(
        check_vaccination_schedule,
        trigger=CronTrigger(hour=9, minute=0),
        id="daily_vaccination_check",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Запланирована ежедневная проверка прививок в 09:00")


# ══════════════════════════════════════════════
#  НАПОМИНАНИЯ О ПОДПИСКЕ
# ══════════════════════════════════════════════


async def send_subscription_expiration_notifications():
    """Отправляет напоминания о скором окончании подписки."""
    if _bot is None:
        return

    from models.models import UserSettings

    today = date.today()
    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(
                UserSettings.is_premium == True,  # noqa: E712
                UserSettings.premium_until != None,  # noqa: E711
            )
        )
        users = result.scalars().all()

    for s in users:
        if not s.premium_until:
            continue
        days_left = (s.premium_until.date() - today).days
        if days_left not in (3, 1, 0, -1):
            continue

        if days_left > 0:
            text = (
                "⏳ <b>Подписка скоро закончится</b>\n\n"
                f"Осталось {days_left} дн. до окончания.\n"
                "Продлите подписку, чтобы не потерять доступ к PRO-функциям."
            )
        elif days_left == 0:
            text = (
                "⏰ <b>Подписка заканчивается сегодня</b>\n\n"
                "Продлите подписку, чтобы сохранить доступ к PRO-функциям."
            )
        else:
            text = (
                "❌ <b>Подписка истекла</b>\n\n"
                "Доступ к PRO-функциям закрыт. Вы можете продлить подписку в настройках."
            )

        try:
            await _bot.send_message(chat_id=s.user_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.error("Ошибка напоминания о подписке user=%s: %s", s.user_id, e)


def schedule_subscription_expiration_notifications():
    """Ежедневные напоминания о подписке в 10:00."""
    scheduler.add_job(
        send_subscription_expiration_notifications,
        trigger=CronTrigger(hour=10, minute=0),
        id="subscription_expiration_notices",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Запланированы напоминания о подписке в 10:00")

# ══════════════════════════════════════════════
#  ПОГОДНЫЕ УВЕДОМЛЕНИЯ
# ══════════════════════════════════════════════


async def send_weather_notifications():
    """Отправляет погодные уведомления пользователям с включённой опцией."""
    if _bot is None:
        return

    from models.models import UserSettings
    from services.weather import get_weather, generate_pet_weather_alert

    users = []
    species_by_user: dict[int, set[str]] = {}
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
        if user_ids:
            pet_rows = await session.execute(
                select(Pet.user_id, Pet.species).where(Pet.user_id.in_(user_ids))
            )
            for user_id, species in pet_rows.all():
                species_by_user.setdefault(user_id, set()).add(species)

    sent = 0
    for user_settings in users:
        weather = await get_weather(user_settings.city)
        if not weather:
            continue

        species_set = species_by_user.get(user_settings.user_id, {"собака"})

        alerts = []
        for species in species_set:
            alert = generate_pet_weather_alert(weather, species)
            if alert:
                alerts.append(alert)

        if alerts:
            text = f"🌤 <b>Утренний прогноз — {user_settings.city}</b>\n\n" + "\n\n".join(alerts)
            try:
                await _bot.send_message(chat_id=user_settings.user_id, text=text, parse_mode="HTML")
                sent += 1
            except Exception as e:
                logger.error(f"Ошибка отправки погоды user={user_settings.user_id}: {e}")

    logger.info(f"Погодные уведомления: {sent} отправлено")


def schedule_weather_notifications():
    """Запланировать утренние погодные уведомления в 7:30."""
    scheduler.add_job(
        send_weather_notifications,
        trigger=CronTrigger(hour=7, minute=30),
        id="daily_weather",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Запланированы погодные уведомления в 07:30")


async def reconcile_card_payments_job():
    """Фоновая сверка платежей YooKassa, чтобы не требовать ручной клик."""
    if _bot is None:
        return

    from handlers.payment import reconcile_pending_card_payments

    await reconcile_pending_card_payments(_bot)


def schedule_payment_reconciliation():
    """Запланировать частую фоновую сверку карточных платежей."""
    scheduler.add_job(
        reconcile_card_payments_job,
        trigger=IntervalTrigger(seconds=30),
        id="card_payment_reconciliation",
        replace_existing=True,
        misfire_grace_time=120,
    )
    logger.info("Запланирована фоновая сверка карточных платежей каждые 30 секунд")
