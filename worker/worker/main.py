"""ZooBuddy Worker — background tasks with APScheduler.

Bot(token) singleton: output-only (send_message, send_photo).
FORBIDDEN: set_webhook, delete_webhook, get_updates, Dispatcher, start_polling.
"""

import asyncio
import logging
import signal
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from zoo_shared.config import get_settings

from worker.bot_sender import close_bot
from worker.tasks.payments import reconcile_pending_payments
from worker.tasks.reminders import load_all_reminders, periodic_sync_reminders
from worker.tasks.subscriptions import send_subscription_expiration_notifications
from worker.tasks.vaccinations import check_vaccination_schedule
from worker.tasks.weather import send_weather_notifications

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main():
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone=settings.BOT_TIMEZONE)

    await load_all_reminders(scheduler)

    scheduler.add_job(
        check_vaccination_schedule,
        trigger=CronTrigger(hour=9, minute=0),
        id="daily_vaccination_check",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        send_weather_notifications,
        trigger=CronTrigger(hour=7, minute=30),
        id="daily_weather",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        reconcile_pending_payments,
        trigger=IntervalTrigger(seconds=30),
        id="card_payment_reconciliation",
        replace_existing=True,
        misfire_grace_time=120,
    )

    scheduler.add_job(
        send_subscription_expiration_notifications,
        trigger=CronTrigger(hour=10, minute=0),
        id="subscription_expiration_notices",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        periodic_sync_reminders,
        trigger=IntervalTrigger(seconds=60),
        id="reminder_sync",
        replace_existing=True,
        misfire_grace_time=120,
    )

    scheduler.start()
    logger.info("Worker started (vaccinations 09:00, weather 07:30, payments 30s, subscriptions 10:00, reminders sync 60s)")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()

    logger.info("Shutting down worker...")
    scheduler.shutdown(wait=False)
    await close_bot()
    logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
