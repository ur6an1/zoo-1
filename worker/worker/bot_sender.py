"""Bot(token) singleton — output-only Telegram sender for worker.

FORBIDDEN: set_webhook, delete_webhook, get_updates, Dispatcher, start_polling.
Only: send_message, send_photo, and other outgoing methods.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from zoo_shared.config import get_settings

logger = logging.getLogger(__name__)

_bot: Bot | None = None


def get_bot() -> Bot:
    """Get or create the Bot singleton."""
    global _bot
    if _bot is None:
        settings = get_settings()
        _bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return _bot


async def send_message(chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Send a text message. Returns True on success."""
    bot = get_bot()
    for attempt in range(1, 4):
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            logger.info("Message sent to %s", chat_id)
            return True
        except Exception as e:
            logger.warning("Failed to send message to %s (attempt %s/3): %s", chat_id, attempt, e)
            if attempt < 3:
                await asyncio.sleep(2 * attempt)
    return False


async def close_bot() -> None:
    """Close bot session on shutdown."""
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None
