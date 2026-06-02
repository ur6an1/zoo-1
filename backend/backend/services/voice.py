"""Сервис распознавания голосовых сообщений через OpenRouter /audio/transcriptions."""

import base64
import logging

import aiohttp
from zoo_shared.config import get_settings

_settings = get_settings()

logger = logging.getLogger(__name__)


def _transcribe_url() -> str:
    return f"{_settings.OPENROUTER_BASE_URL.rstrip('/')}/audio/transcriptions"


def _transcribe_headers() -> dict[str, str] | None:
    if not _settings.OPENROUTER_API_KEY:
        return None
    headers = {
        "Authorization": f"Bearer {_settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    if _settings.OPENROUTER_SITE_URL:
        headers["HTTP-Referer"] = _settings.OPENROUTER_SITE_URL
    if _settings.OPENROUTER_APP_NAME:
        headers["X-Title"] = _settings.OPENROUTER_APP_NAME
    return headers


async def transcribe_voice(voice_data: bytes) -> str | None:
    """Распознаёт голосовое (Telegram OGG/Opus) через OpenRouter /audio/transcriptions.

    Используется JSON-формат с base64 (OpenRouter не поддерживает multipart, как OpenAI).
    """
    headers = _transcribe_headers()
    if headers is None:
        logger.warning("OPENROUTER_API_KEY не задан — распознавание голоса недоступно")
        return None
    if not voice_data:
        return None

    payload = {
        "model": _settings.OPENROUTER_TRANSCRIBE_MODEL,
        "input_audio": {
            "data": base64.b64encode(voice_data).decode("ascii"),
            "format": "ogg",
        },
        "language": "ru",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                _transcribe_url(),
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.error(f"OpenRouter transcription error {resp.status}: {err[:400]}")
                    return None
                data = await resp.json(content_type=None)
                text = (data or {}).get("text") or ""
                text = text.strip()
                return text if text else None
    except Exception as e:
        logger.error(f"OpenRouter transcription exception: {e}")
        return None
