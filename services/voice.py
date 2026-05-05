"""Сервис распознавания голосовых сообщений через OpenAI Whisper API."""

import logging
import aiohttp
from config import OPENAI_API_KEY, OPENAI_TRANSCRIBE_MODEL

logger = logging.getLogger(__name__)

WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
WHISPER_MODEL = OPENAI_TRANSCRIBE_MODEL


async def transcribe_voice(voice_data: bytes) -> str | None:
    """Распознаёт голосовое сообщение (OGG) через OpenAI Whisper API.

    Args:
        voice_data: Байты аудиофайла (OGG от Telegram).

    Returns:
        Распознанный текст или None при ошибке.
    """
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY не задан — распознавание голоса недоступно")
        return None

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    form = aiohttp.FormData()
    form.add_field(
        "file",
        voice_data,
        filename="voice.ogg",
        content_type="audio/ogg",
    )
    form.add_field("model", WHISPER_MODEL)
    form.add_field("language", "ru")
    form.add_field("response_format", "text")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WHISPER_URL,
                headers=headers,
                data=form,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.error(f"Whisper API error {resp.status}: {err[:400]}")
                    return None
                text = await resp.text()
                return text.strip() if text.strip() else None
    except Exception as e:
        logger.error(f"Whisper API exception: {e}")
        return None
