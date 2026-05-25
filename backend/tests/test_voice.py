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


from unittest.mock import AsyncMock, MagicMock, patch

import backend.backend.services.voice as voice_mod


class TestTranscribeVoice:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_none(self):
        from zoo_shared.config import get_settings
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            result = await transcribe_voice(b"fake-audio-data")
            assert result is None

    @pytest.mark.asyncio
    async def test_success_returns_text(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENAI_API_KEY", "sk-test")

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.text = AsyncMock(return_value="привет мир")

        mock_post = MagicMock()
        mock_post.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_post.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = MagicMock(return_value=mock_post)

        with patch("aiohttp.ClientSession", return_value=mock_client):
            result = await transcribe_voice(b"fake audio")

        assert result == "привет мир"

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENAI_API_KEY", "sk-test")

        mock_resp = AsyncMock()
        mock_resp.status = 400
        mock_resp.text = AsyncMock(return_value="Bad Request")

        mock_post = MagicMock()
        mock_post.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_post.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = MagicMock(return_value=mock_post)

        with patch("aiohttp.ClientSession", return_value=mock_client):
            result = await transcribe_voice(b"fake audio")

        assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENAI_API_KEY", "sk-test")

        with patch("aiohttp.ClientSession", side_effect=Exception("network error")):
            result = await transcribe_voice(b"fake audio")

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_response_returns_none(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENAI_API_KEY", "sk-test")

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.text = AsyncMock(return_value="   ")

        mock_post = MagicMock()
        mock_post.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_post.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = MagicMock(return_value=mock_post)

        with patch("aiohttp.ClientSession", return_value=mock_client):
            result = await transcribe_voice(b"fake audio")

        assert result is None
