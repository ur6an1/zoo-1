"""Tests for backend.services.provider_health — cache logic."""

import os
from datetime import datetime, timedelta

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")

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
