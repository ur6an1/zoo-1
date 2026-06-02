"""Tests for backend.services.provider_health — cache logic."""

import os
from datetime import datetime, timedelta

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")

import backend.services.provider_health as ph
import pytest
from backend.services.provider_health import _CACHE, _TTL, _is_fresh, mark_ai_unavailable


class TestIsFresh:
    def test_not_checked(self):
        _CACHE["ai"]["checked_at"] = None
        assert _is_fresh("ai") is False

    def test_fresh(self):
        _CACHE["ai"]["checked_at"] = datetime.utcnow()
        assert _is_fresh("ai") is True

    def test_stale(self):
        _CACHE["ai"]["checked_at"] = datetime.utcnow() - _TTL - timedelta(seconds=1)
        assert _is_fresh("ai") is False

    def test_yookassa_not_checked(self):
        _CACHE["yookassa"]["checked_at"] = None
        assert _is_fresh("yookassa") is False

    def test_yookassa_fresh(self):
        _CACHE["yookassa"]["checked_at"] = datetime.utcnow()
        assert _is_fresh("yookassa") is True


class TestCacheStructure:
    def test_ai_key_exists(self):
        assert "ai" in _CACHE
        assert "status" in _CACHE["ai"]
        assert "checked_at" in _CACHE["ai"]

    def test_yookassa_key_exists(self):
        assert "yookassa" in _CACHE

    def test_ttl_positive(self):
        assert _TTL.total_seconds() > 0

    def test_mark_ai_unavailable_sets_cache(self):
        _CACHE["ai"]["status"] = True
        _CACHE["ai"]["checked_at"] = None

        mark_ai_unavailable()

        assert _CACHE["ai"]["status"] is False
        assert _CACHE["ai"]["checked_at"] is not None


class TestCheckAiOpenRouterOnly:
    @pytest.mark.asyncio
    async def test_check_ai_returns_false_without_openrouter_key(self, monkeypatch):
        monkeypatch.setattr(ph._settings, "OPENROUTER_API_KEY", "")
        result = await ph._check_ai()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_ai_uses_openrouter_url(self, monkeypatch):
        monkeypatch.setattr(ph._settings, "OPENROUTER_API_KEY", "sk-test")
        monkeypatch.setattr(ph._settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        monkeypatch.setattr(ph._settings, "OPENROUTER_MODEL", "openai/gpt-4o-mini")
        monkeypatch.setattr(ph._settings, "OPENROUTER_SITE_URL", "")
        monkeypatch.setattr(ph._settings, "OPENROUTER_APP_NAME", "")

        captured: dict = {}

        class _Resp:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        class _Sess:
            def post(self, url, **kwargs):
                captured["url"] = url
                return _Resp()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        monkeypatch.setattr(ph.aiohttp, "ClientSession", lambda: _Sess())
        result = await ph._check_ai()
        assert result is True
        assert "openrouter.ai" in captured.get("url", "")
