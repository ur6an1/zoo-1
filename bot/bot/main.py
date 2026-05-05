"""
ZooBuddy — Telegram-бот для владельцев домашних животных.

Entrypoint: polling mode.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from zoo_shared.config import get_settings

from bot.handlers import get_all_routers
from bot.middlewares.error_guard import ErrorGuardMiddleware
from bot.middlewares.throttle import ThrottleMiddleware

try:
    from aiogram.fsm.storage.redis import RedisStorage
except Exception:
    RedisStorage = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    logger.info("Инициализация бота...")
    bot_info = await bot.get_me()
    logger.info("Бот @%s (%s) запущен!", bot_info.username, bot_info.first_name)


async def on_shutdown(bot: Bot):
    logger.info("Остановка бота...")


async def main():
    settings = get_settings()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = MemoryStorage()
    if settings.REDIS_URL and RedisStorage is not None:
        try:
            storage = RedisStorage.from_url(settings.REDIS_URL)
            logger.info("FSM storage: Redis")
        except Exception as e:
            logger.warning("Не удалось инициализировать RedisStorage (%s). Используем MemoryStorage.", e)
    else:
        logger.info("FSM storage: Memory")

    dp = Dispatcher(storage=storage)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    error_guard = ErrorGuardMiddleware()
    dp.message.middleware(error_guard)
    dp.callback_query.middleware(error_guard)
    dp.callback_query.middleware(ThrottleMiddleware())

    for router in get_all_routers():
        dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Запуск polling...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен (Ctrl+C)")
    except Exception as e:
        logger.critical("Критическая ошибка: %s", e, exc_info=True)
