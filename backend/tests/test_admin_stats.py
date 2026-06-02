"""Тесты агрегаций админ-панели (backend.services.admin_stats).

Изолированная in-memory БД на каждый тест — иначе count-ассерты ловят данные
из других тестов в session-scoped движке.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")

from contextlib import asynccontextmanager  # noqa: E402
from datetime import datetime  # noqa: E402
from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from backend.services import admin_stats  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from zoo_shared.db.models import (  # noqa: E402
    AnalyticsEvent,
    Base,
    PendingPayment,
    Pet,
    ProcessedPayment,
    UserSettings,
)

_MOD = "backend.services.admin_stats"


@pytest_asyncio.fixture
async def admin_db():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def _session():
        async with factory() as session:
            yield session

    now = datetime.utcnow()
    async with factory() as session:
        session.add_all(
            [
                UserSettings(
                    user_id=1001,
                    plan_tier="pro",
                    is_premium=True,
                    premium_until=now.replace(year=now.year + 1),
                    ai_requests_today=3,
                    last_request_date=now.date(),
                ),
                UserSettings(user_id=1002, plan_tier="free", is_premium=False),
                Pet(user_id=1001, name="Рекс", species="собака"),
                AnalyticsEvent(user_id=1001, event_name="start"),
                PendingPayment(
                    provider="yookassa",
                    payment_id="pay-1",
                    user_id=1001,
                    plan_key="pro",
                    amount_value="299.00",
                    currency="RUB",
                    status="succeeded",
                ),
                ProcessedPayment(provider="yookassa", payment_id="pay-1", user_id=1001, plan_key="pro"),
            ]
        )
        await session.commit()

    with patch(f"{_MOD}.async_session", _session):
        yield factory
    await eng.dispose()


@pytest.mark.asyncio
async def test_overview(admin_db):
    d = await admin_stats.get_overview()
    assert d["users_total"] == 2
    assert d["premium_active"] == 1
    assert d["by_tier"] == {"pro": 1, "free": 1}
    assert d["pets_total"] == 1
    assert d["by_species"] == {"собака": 1}
    assert d["active_today"] >= 1
    assert d["ai_requests_today"] == 3


@pytest.mark.asyncio
async def test_finance(admin_db):
    d = await admin_stats.get_finance()
    assert d["revenue_total"] == 299.0
    assert d["paid_count"] == 1
    assert d["paying_users"] == 1
    assert d["by_plan"]["pro"] == {"count": 1, "amount": 299.0}
    assert d["by_status"] == {"succeeded": 1}
    assert d["processed_total"] == 1
    assert len(d["recent"]) == 1
    assert d["recent"][0]["user_id"] == 1001


@pytest.mark.asyncio
async def test_list_users(admin_db):
    page = await admin_stats.list_users(limit=10, offset=0)
    assert page["total"] == 2
    assert len(page["items"]) == 2

    filtered = await admin_stats.list_users(query="1001")
    assert filtered["total"] == 1
    assert filtered["items"][0]["user_id"] == 1001
    assert filtered["items"][0]["pets"] == 1


@pytest.mark.asyncio
async def test_user_detail(admin_db):
    d = await admin_stats.get_user_detail(1001)
    assert d is not None
    assert d["pets"] == 1
    assert d["payments"] == 1
    assert d["events"] == 1
    assert await admin_stats.get_user_detail(99999) is None


@pytest.mark.asyncio
async def test_broadcast_targets(admin_db):
    targets = await admin_stats.get_broadcast_targets()
    assert set(targets) == {1001, 1002}
