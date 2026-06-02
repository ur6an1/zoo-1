"""Tests for subscription async DB functions (grant/revoke/check limits)."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from backend.services.subscription import (
    GRACE_DAYS,
    PLAN_BASIC,
    PLAN_FREE,
    PLAN_PRO,
    can_use_pdf_export,
    can_use_voice_notes,
    can_use_weather_notifications,
    check_ai_limit,
    check_pet_limit,
    get_or_create_settings,
    get_plan_tier,
    grant_premium,
    is_premium,
    refund_ai_limit,
    revoke_premium,
)
from zoo_shared.db.models import Pet, UserSettings

_MOD = "backend.services.subscription"


@pytest.fixture
def sub_db(db_session):
    @asynccontextmanager
    async def _session():
        yield db_session

    with patch(f"{_MOD}.async_session", _session):
        yield db_session


# ── grant_premium ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_grant_premium_creates_new_user(sub_db):
    ok = await grant_premium(20001, days=30)
    assert ok is True
    s = await sub_db.get(UserSettings, None)
    result = await get_or_create_settings(20001)
    assert result.is_premium is True
    assert result.plan_tier == PLAN_PRO


@pytest.mark.asyncio
async def test_grant_premium_extends_active(sub_db):
    await grant_premium(20002, days=10)
    await grant_premium(20002, days=20)
    s = await get_or_create_settings(20002)
    assert s.premium_until is not None
    assert s.premium_until > datetime.utcnow() + timedelta(days=25)


@pytest.mark.asyncio
async def test_grant_premium_zero_days_returns_false(sub_db):
    result = await grant_premium(20003, days=0)
    assert result is False


@pytest.mark.asyncio
async def test_grant_premium_invalid_tier_defaults_to_pro(sub_db):
    await grant_premium(20004, days=30, plan_tier="garbage")
    s = await get_or_create_settings(20004)
    assert s.plan_tier == PLAN_PRO


@pytest.mark.asyncio
async def test_grant_premium_basic_tier(sub_db):
    await grant_premium(20005, days=30, plan_tier=PLAN_BASIC)
    s = await get_or_create_settings(20005)
    assert s.plan_tier == PLAN_BASIC


# ── revoke_premium ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_premium(sub_db):
    await grant_premium(20010, days=30)
    result = await revoke_premium(20010)
    assert result is True
    s = await get_or_create_settings(20010)
    assert s.is_premium is False
    assert s.plan_tier == PLAN_FREE


@pytest.mark.asyncio
async def test_revoke_premium_nonexistent_user(sub_db):
    result = await revoke_premium(29999)
    assert result is True


# ── get_or_create_settings ───────────────────────────────────


@pytest.mark.asyncio
async def test_get_or_create_settings_new_user(sub_db):
    s = await get_or_create_settings(20020)
    assert s.user_id == 20020
    assert s.plan_tier == PLAN_FREE
    assert s.is_premium is False


@pytest.mark.asyncio
async def test_get_or_create_settings_existing_user(sub_db):
    s1 = await get_or_create_settings(20021)
    s2 = await get_or_create_settings(20021)
    assert s1.user_id == s2.user_id


@pytest.mark.asyncio
async def test_get_or_create_expires_overdue_premium(sub_db):
    sub_db.add(
        UserSettings(
            user_id=20022,
            is_premium=True,
            plan_tier=PLAN_PRO,
            premium_until=datetime.utcnow() - timedelta(days=GRACE_DAYS + 5),
        )
    )
    await sub_db.flush()
    s = await get_or_create_settings(20022)
    assert s.is_premium is False
    assert s.plan_tier == PLAN_FREE


# ── get_plan_tier / is_premium ───────────────────────────────


@pytest.mark.asyncio
async def test_get_plan_tier_free_user(sub_db):
    tier = await get_plan_tier(20030)
    assert tier == PLAN_FREE


@pytest.mark.asyncio
async def test_get_plan_tier_premium_user(sub_db):
    await grant_premium(20031, days=30)
    tier = await get_plan_tier(20031)
    assert tier == PLAN_PRO


@pytest.mark.asyncio
async def test_is_premium_false_for_new(sub_db):
    assert await is_premium(20032) is False


@pytest.mark.asyncio
async def test_is_premium_true_after_grant(sub_db):
    await grant_premium(20033, days=30)
    assert await is_premium(20033) is True


# ── check_ai_limit ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_ai_limit_allows_first_request(sub_db):
    allowed, remaining = await check_ai_limit(20040)
    assert allowed is True
    assert remaining >= 0


@pytest.mark.asyncio
async def test_check_ai_limit_decrements_counter(sub_db):
    _, r1 = await check_ai_limit(20041)
    _, r2 = await check_ai_limit(20041)
    assert r2 == r1 - 1


@pytest.mark.asyncio
async def test_check_ai_limit_exhausted(sub_db):
    uid = 20042
    from zoo_shared.config import get_settings

    limit = get_settings().FREE_AI_LIMIT
    for _ in range(limit):
        await check_ai_limit(uid)
    allowed, remaining = await check_ai_limit(uid)
    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_check_ai_limit_premium_unlimited(sub_db):
    await grant_premium(20043, days=30)
    allowed, remaining = await check_ai_limit(20043)
    assert allowed is True
    assert remaining == 999


# ── refund_ai_limit ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_refund_ai_limit_decrements(sub_db):
    await check_ai_limit(20050)
    await check_ai_limit(20050)
    s_before = await get_or_create_settings(20050)
    count_before = s_before.ai_requests_today
    await refund_ai_limit(20050)
    s_after = await get_or_create_settings(20050)
    assert s_after.ai_requests_today == count_before - 1


@pytest.mark.asyncio
async def test_refund_ai_limit_nonexistent_user(sub_db):
    await refund_ai_limit(29998)


# ── check_pet_limit ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_pet_limit_under_limit(sub_db):
    allowed, remaining = await check_pet_limit(20060)
    assert allowed is True
    assert remaining > 0


@pytest.mark.asyncio
async def test_check_pet_limit_at_limit(sub_db):
    uid = 20061
    from zoo_shared.config import get_settings

    limit = get_settings().FREE_PET_LIMIT
    for i in range(limit):
        sub_db.add(Pet(user_id=uid, name=f"Pet{i}", species="кот"))
    await sub_db.flush()
    allowed, remaining = await check_pet_limit(uid)
    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_check_pet_limit_pro_unlimited(sub_db):
    await grant_premium(20062, days=30, plan_tier=PLAN_PRO)
    allowed, remaining = await check_pet_limit(20062)
    assert allowed is True
    assert remaining == 999


# ── capability checks ────────────────────────────────────────


@pytest.mark.asyncio
async def test_can_use_pdf_export_free_false(sub_db):
    assert await can_use_pdf_export(20070) is False


@pytest.mark.asyncio
async def test_can_use_pdf_export_pro_true(sub_db):
    await grant_premium(20071, days=30)
    assert await can_use_pdf_export(20071) is True


@pytest.mark.asyncio
async def test_can_use_weather_notifications_pro(sub_db):
    await grant_premium(20072, days=30)
    assert await can_use_weather_notifications(20072) is True


@pytest.mark.asyncio
async def test_can_use_voice_notes_pro(sub_db):
    await grant_premium(20073, days=30)
    assert await can_use_voice_notes(20073) is True
