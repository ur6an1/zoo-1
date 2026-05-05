"""Tests for backend.services.voice — constants and transcription logic."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")


import pytest
from backend.services.voice import WHISPER_MODEL, WHISPER_URL, transcribe_voice


class TestVoiceConstants:
    def test_whisper_url(self):
        assert "openai.com" in WHISPER_URL

    def test_whisper_model(self):
        assert WHISPER_MODEL == "whisper-1"


class TestTranscribeVoice:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_none(self):
        from zoo_shared.config import get_settings
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            result = await transcribe_voice(b"fake-audio-data")
            assert result is None
