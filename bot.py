"""
ZooBuddy — Telegram-бот для владельцев домашних животных.

Главный файл запуска бота.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

try:
    from aiogram.fsm.storage.redis import RedisStorage
except Exception:  # pragma: no cover - optional dependency
    RedisStorage = None

from config import BOT_TOKEN, REDIS_URL
from database import init_db
from handlers import get_all_routers
from middlewares.throttle import ThrottleMiddleware
from middlewares.error_guard import ErrorGuardMiddleware
from services.scheduler import (
    scheduler, set_bot, load_all_reminders,
    schedule_daily_vaccination_check, schedule_payment_reconciliation, schedule_weather_notifications, schedule_subscription_expiration_notifications,
)
from services.provider_health import refresh_provider_health

# ──────────────────── ЛОГИРОВАНИЕ ────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    logger.info("🚀 Инициализация бота...")

    await init_db()
    logger.info("✅ База данных инициализирована")

    try:
        await refresh_provider_health(force=True)
        logger.info("✅ Проверка внешних провайдеров выполнена")
    except Exception as e:
        logger.warning("⚠️ Не удалось обновить статус провайдеров: %s", e)

    set_bot(bot)
    scheduler.start()
    await load_all_reminders()
    schedule_daily_vaccination_check()
    schedule_weather_notifications()
    schedule_payment_reconciliation()
    schedule_subscription_expiration_notifications()
    logger.info("✅ Планировщик запущен (прививки 09:00, погода 07:30, платежи каждые 30 сек)")

    bot_info = await bot.get_me()
    logger.info(f"✅ Бот @{bot_info.username} ({bot_info.first_name}) запущен!")


async def on_shutdown(bot: Bot):
    logger.info("🛑 Остановка бота...")
    scheduler.shutdown(wait=False)
    logger.info("🛑 Планировщик остановлен")


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = MemoryStorage()
    if REDIS_URL and RedisStorage is not None:
        try:
            storage = RedisStorage.from_url(REDIS_URL)
            logger.info("✅ FSM storage: Redis")
        except Exception as e:
            logger.warning("⚠️ Не удалось инициализировать RedisStorage (%s). Используем MemoryStorage.", e)
    else:
        logger.info("✅ FSM storage: Memory")

    dp = Dispatcher(storage=storage)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    error_guard = ErrorGuardMiddleware()
    dp.message.middleware(error_guard)
    dp.callback_query.middleware(error_guard)
    dp.callback_query.middleware(ThrottleMiddleware())
    logger.info("🛡 ErrorGuardMiddleware зарегистрирован")
    logger.info("🛡 ThrottleMiddleware зарегистрирован")

    for router in get_all_routers():
        dp.include_router(router)
        logger.info(f"  📌 Роутер '{router.name}' зарегистрирован")

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🔄 Запуск polling...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
