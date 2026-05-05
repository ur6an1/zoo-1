"""Конфигурация бота."""

import logging
import os

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./zoo_bot.db")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TRANSCRIBE_MODEL: str = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_SITE_URL: str = os.getenv("OPENROUTER_SITE_URL", "")
OPENROUTER_APP_NAME: str = os.getenv("OPENROUTER_APP_NAME", "zoo_bot")
WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")
REDIS_URL: str = os.getenv("REDIS_URL", "")
BOT_TIMEZONE: str = os.getenv("BOT_TIMEZONE", "Europe/Moscow")
YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY: str = os.getenv("YOOKASSA_SECRET_KEY", "")
RECEIPT_EMAIL: str = os.getenv("RECEIPT_EMAIL", "")
PAYMENT_RETURN_URL: str = os.getenv("PAYMENT_RETURN_URL", "")

def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Пропущен некорректный %s value: %s", name, raw)
        return default


# Лимиты и cost-control
FREE_AI_LIMIT: int = _int_env("FREE_AI_LIMIT", 10)
FREE_PET_LIMIT: int = _int_env("FREE_PET_LIMIT", 2)
AI_MAX_TOKENS_VISION: int = _int_env("AI_MAX_TOKENS_VISION", 1600)
AI_MAX_TOKENS_TEXT: int = _int_env("AI_MAX_TOKENS_TEXT", 1800)

def _parse_admin_ids(raw: str) -> list[int]:
    admin_ids: list[int] = []
    for chunk in raw.split(","):
        value = chunk.strip()
        if not value:
            continue
        try:
            admin_ids.append(int(value))
        except ValueError:
            logger.warning("Пропущен некорректный ADMIN_IDS value: %s", value)
    return admin_ids


# Админы (могут выдавать премиум)
ADMIN_IDS: list[int] = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан! Укажите его в файле .env")
