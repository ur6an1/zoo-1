"""Tests for backend.services.voice — OpenRouter /audio/transcriptions."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")


from unittest.mock import AsyncMock, MagicMock, patch

import backend.services.voice as voice_mod
import pytest
from backend.services.voice import (
    _transcribe_headers,
    _transcribe_url,
    transcribe_voice,
)


class TestTranscribeEndpoint:
    def test_url_points_to_openrouter(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        url = _transcribe_url()
        assert "openrouter.ai" in url
        assert url.endswith("/audio/transcriptions")
        assert "api.openai.com" not in url

    def test_headers_none_without_key(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_API_KEY", "")
        assert _transcribe_headers() is None

    def test_headers_include_bearer(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_SITE_URL", "")
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_APP_NAME", "")
        h = _transcribe_headers()
        assert h is not None
        assert h["Authorization"] == "Bearer sk-or"
        assert h["Content-Type"] == "application/json"


def _mock_session(*, status: int, payload_json: dict | None = None, text: str = ""):
    """Builds a mocked aiohttp.ClientSession returning the given response."""
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=payload_json or {})
    mock_resp.text = AsyncMock(return_value=text)

    mock_post_ctx = MagicMock()
    mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_post_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = MagicMock(return_value=mock_post_ctx)
    return mock_client, mock_post_ctx


class TestTranscribeVoice:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_none(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_API_KEY", "")
        assert await transcribe_voice(b"fake-audio-data") is None

    @pytest.mark.asyncio
    async def test_empty_audio_returns_none(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        assert await transcribe_voice(b"") is None

    @pytest.mark.asyncio
    async def test_success_returns_text(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        client, _ = _mock_session(status=200, payload_json={"text": "привет мир"})
        with patch("aiohttp.ClientSession", return_value=client):
            result = await transcribe_voice(b"fake audio")
        assert result == "привет мир"

    @pytest.mark.asyncio
    async def test_payload_uses_base64_and_configured_model(self, monkeypatch):
        """Проверяем, что отправляется JSON c base64 audio и нужным slug-ом модели."""
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_TRANSCRIBE_MODEL", "openai/whisper-1")

        captured: dict = {}

        class _Resp:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return None

            async def json(self, content_type=None):
                return {"text": "ok"}

            async def text(self):
                return ""

        class _Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return None

            def post(self, url, headers=None, json=None, timeout=None):
                captured["url"] = url
                captured["headers"] = headers
                captured["json"] = json
                return _Resp()

        with patch("aiohttp.ClientSession", _Session):
            result = await transcribe_voice(b"abc")

        assert result == "ok"
        assert captured["url"].endswith("/audio/transcriptions")
        assert "openrouter.ai" in captured["url"]
        assert captured["headers"]["Authorization"] == "Bearer sk-or"
        assert captured["json"]["model"] == "openai/whisper-1"
        assert captured["json"]["input_audio"]["format"] == "ogg"
        # base64 of b"abc"
        import base64

        assert captured["json"]["input_audio"]["data"] == base64.b64encode(b"abc").decode("ascii")
        assert captured["json"]["language"] == "ru"

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        client, _ = _mock_session(status=400, text="Bad Request")
        with patch("aiohttp.ClientSession", return_value=client):
            result = await transcribe_voice(b"fake audio")
        assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        with patch("aiohttp.ClientSession", side_effect=Exception("network error")):
            assert await transcribe_voice(b"fake audio") is None

    @pytest.mark.asyncio
    async def test_empty_text_in_response_returns_none(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        client, _ = _mock_session(status=200, payload_json={"text": "   "})
        with patch("aiohttp.ClientSession", return_value=client):
            result = await transcribe_voice(b"fake audio")
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_text_field_returns_none(self, monkeypatch):
        monkeypatch.setattr(voice_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        client, _ = _mock_session(status=200, payload_json={})
        with patch("aiohttp.ClientSession", return_value=client):
            result = await transcribe_voice(b"fake audio")
        assert result is None
