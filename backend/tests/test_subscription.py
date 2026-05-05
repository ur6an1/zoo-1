"""Tests for backend.services.subscription — pure function helpers."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")

from datetime import datetime, timedelta

from backend.services.subscription import (
    GRACE_DAYS,
    PLAN_AI_LIMITS,
    PLAN_BASIC,
    PLAN_FREE,
    PLAN_LABELS,
    PLAN_PET_LIMITS,
    PLAN_PRO,
    _ai_limit_for_plan,
    _is_subscription_active,
    _normalize_plan,
    _pet_limit_for_plan,
    format_subscription_info,
)
from zoo_shared.db.models import UserSettings


class TestNormalizePlan:
    def test_free(self):
        assert _normalize_plan("free", False) == PLAN_FREE

    def test_basic(self):
        assert _normalize_plan("basic", True) == PLAN_BASIC

    def test_pro(self):
        assert _normalize_plan("pro", True) == PLAN_PRO

    def test_empty_not_premium(self):
        assert _normalize_plan("", False) == PLAN_FREE

    def test_empty_is_premium(self):
        assert _normalize_plan("", True) == PLAN_PRO

    def test_none_not_premium(self):
        assert _normalize_plan(None, False) == PLAN_FREE

    def test_none_is_premium(self):
        assert _normalize_plan(None, True) == PLAN_PRO

    def test_garbage(self):
        assert _normalize_plan("xyz", False) == PLAN_FREE

    def test_whitespace(self):
        assert _normalize_plan("  pro  ", True) == PLAN_PRO

    def test_uppercase(self):
        assert _normalize_plan("PRO", True) == PLAN_PRO


class TestIsSubscriptionActive:
    def _make_settings(self, is_premium=True, premium_until=None):
        s = UserSettings(id=1, user_id=1)
        s.is_premium = is_premium
        s.premium_until = premium_until
        return s

    def test_not_premium(self):
        s = self._make_settings(is_premium=False)
        assert _is_subscription_active(s) is False

    def test_premium_no_expiry(self):
        s = self._make_settings(is_premium=True, premium_until=None)
        assert _is_subscription_active(s) is True

    def test_premium_future(self):
        future = datetime.utcnow() + timedelta(days=30)
        s = self._make_settings(is_premium=True, premium_until=future)
        assert _is_subscription_active(s) is True

    def test_premium_expired_within_grace(self):
        expired = datetime.utcnow() - timedelta(days=1)
        s = self._make_settings(is_premium=True, premium_until=expired)
        assert _is_subscription_active(s) is True

    def test_premium_expired_past_grace(self):
        expired = datetime.utcnow() - timedelta(days=GRACE_DAYS + 1)
        s = self._make_settings(is_premium=True, premium_until=expired)
        assert _is_subscription_active(s) is False


class TestPlanLimits:
    def test_free_ai_limit(self):
        limit = _ai_limit_for_plan(PLAN_FREE)
        assert isinstance(limit, int)
        assert limit > 0

    def test_basic_ai_limit(self):
        assert _ai_limit_for_plan(PLAN_BASIC) is None

    def test_pro_ai_limit(self):
        assert _ai_limit_for_plan(PLAN_PRO) is None

    def test_unknown_ai_limit(self):
        limit = _ai_limit_for_plan("unknown")
        assert isinstance(limit, int)

    def test_free_pet_limit(self):
        limit = _pet_limit_for_plan(PLAN_FREE)
        assert isinstance(limit, int)
        assert limit > 0

    def test_basic_pet_limit(self):
        assert _pet_limit_for_plan(PLAN_BASIC) == 5

    def test_pro_pet_limit(self):
        assert _pet_limit_for_plan(PLAN_PRO) is None


class TestFormatSubscriptionInfo:
    def _make_settings(self, is_premium=False, plan_tier="free", premium_until=None):
        s = UserSettings(id=1, user_id=1)
        s.is_premium = is_premium
        s.plan_tier = plan_tier
        s.premium_until = premium_until
        s.ai_requests_today = 0
        s.last_request_date = None
        return s

    def test_free_plan(self):
        s = self._make_settings()
        result = format_subscription_info(s)
        assert "Бесплатный" in result
        assert "AI-запросы" in result

    def test_basic_plan(self):
        future = datetime.utcnow() + timedelta(days=30)
        s = self._make_settings(is_premium=True, plan_tier="basic", premium_until=future)
        result = format_subscription_info(s)
        assert "Базовый" in result

    def test_pro_plan(self):
        future = datetime.utcnow() + timedelta(days=30)
        s = self._make_settings(is_premium=True, plan_tier="pro", premium_until=future)
        result = format_subscription_info(s)
        assert "PRO" in result

    def test_pro_no_expiry(self):
        s = self._make_settings(is_premium=True, plan_tier="pro", premium_until=None)
        result = format_subscription_info(s)
        assert "бессрочно" in result

    def test_free_with_used_requests(self):
        from datetime import date

        s = self._make_settings()
        s.ai_requests_today = 5
        s.last_request_date = date.today()
        result = format_subscription_info(s)
        assert "Бесплатный" in result


class TestPlanConstants:
    def test_plan_labels(self):
        assert PLAN_LABELS[PLAN_FREE] == "Бесплатный"
        assert PLAN_LABELS[PLAN_BASIC] == "Базовый"
        assert PLAN_LABELS[PLAN_PRO] == "PRO"

    def test_plan_ai_limits_keys(self):
        assert PLAN_FREE in PLAN_AI_LIMITS
        assert PLAN_BASIC in PLAN_AI_LIMITS
        assert PLAN_PRO in PLAN_AI_LIMITS

    def test_plan_pet_limits_keys(self):
        assert PLAN_FREE in PLAN_PET_LIMITS
        assert PLAN_BASIC in PLAN_PET_LIMITS
        assert PLAN_PRO in PLAN_PET_LIMITS

    def test_grace_days(self):
        assert GRACE_DAYS == 2
