"""Проверка доступности внешних провайдеров (GPT/оплата) с кэшированием."""

import asyncio
import base64
import logging
from datetime import datetime, timedelta

import aiohttp
from zoo_shared.config import get_settings

_settings = get_settings()

logger = logging.getLogger(__name__)

_TTL = timedelta(minutes=10)
_TIMEOUT = aiohttp.ClientTimeout(total=6)

_CACHE: dict[str, dict[str, datetime | bool | None]] = {
    "ai": {"status": None, "checked_at": None},
    "yookassa": {"status": None, "checked_at": None},
}


def _is_fresh(name: str) -> bool:
    checked_at = _CACHE[name]["checked_at"]
    if not checked_at:
        return False
    return (datetime.utcnow() - checked_at) < _TTL


async def _check_ai() -> bool | None:
    if _settings.OPENROUTER_API_KEY:
        headers = {
            "Authorization": f"Bearer {_settings.OPENROUTER_API_KEY}",
        }
        if _settings.OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = _settings.OPENROUTER_SITE_URL
        if _settings.OPENROUTER_APP_NAME:
            headers["X-Title"] = _settings.OPENROUTER_APP_NAME
        url = f"{_settings.OPENROUTER_BASE_URL.rstrip('/')}/models"
    elif _settings.OPENAI_API_KEY:
        headers = {"Authorization": f"Bearer {_settings.OPENAI_API_KEY}"}
        url = "https://api.openai.com/v1/models"
    else:
        return False

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    return True
                if resp.status in (400, 401, 403, 404):
                    return False
                return None
    except Exception as e:
        logger.warning("AI provider health-check failed: %s", e)
        return None


async def _check_yookassa() -> bool | None:
    if not _settings.YOOKASSA_SHOP_ID or not _settings.YOOKASSA_SECRET_KEY:
        return False

    creds = f"{_settings.YOOKASSA_SHOP_ID}:{_settings.YOOKASSA_SECRET_KEY}"
    auth = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
    headers = {"Authorization": f"Basic {auth}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.yookassa.ru/v3/payments?limit=1",
                headers=headers,
                timeout=_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    return True
                if resp.status in (400, 401, 403, 404):
                    return False
                return None
    except Exception as e:
        logger.warning("YooKassa health-check failed: %s", e)
        return None


async def refresh_provider_health(force: bool = False) -> None:
    """Обновляет кэш доступности провайдеров."""
    tasks: dict[str, asyncio.Task] = {}

    if force or not _is_fresh("ai"):
        tasks["ai"] = asyncio.create_task(_check_ai())
    if force or not _is_fresh("yookassa"):
        tasks["yookassa"] = asyncio.create_task(_check_yookassa())

    if not tasks:
        return

    now = datetime.utcnow()
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for name, result in zip(tasks.keys(), results, strict=False):
        status: bool | None
        if isinstance(result, Exception):
            logger.warning("Provider health-check task error (%s): %s", name, result)
            status = None
        else:
            status = result
        _CACHE[name]["status"] = status
        _CACHE[name]["checked_at"] = now


async def is_ai_operational(force: bool = False) -> bool:
    """True, если активный AI-провайдер доступен.

    При сетевой неопределённости не блокируем функциональность жёстко.
    """
    if not _settings.OPENAI_API_KEY and not _settings.OPENROUTER_API_KEY:
        return False

    await refresh_provider_health(force=force)
    status = _CACHE["ai"]["status"]
    if status is False:
        return False
    return True


async def is_card_payment_operational(force: bool = False) -> bool:
    """True, если карточная оплата в YooKassa доступна.

    При сетевой неопределённости не блокируем оплату жёстко.
    """
    if not _settings.YOOKASSA_SHOP_ID or not _settings.YOOKASSA_SECRET_KEY:
        return False

    await refresh_provider_health(force=force)
    status = _CACHE["yookassa"]["status"]
    return status is True
