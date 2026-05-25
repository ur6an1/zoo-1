"""Tests for backend.services.analytics — constants and structure."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")

from backend.services.analytics import FUNNEL_EVENTS, RETURN_GAP


class TestAnalyticsConstants:
    def test_funnel_events_is_tuple(self):
        assert isinstance(FUNNEL_EVENTS, tuple)

    def test_funnel_events_contains_start(self):
        assert "start" in FUNNEL_EVENTS

    def test_funnel_events_contains_payment(self):
        assert "payment_succeeded" in FUNNEL_EVENTS

    def test_return_gap_positive(self):
        assert RETURN_GAP.total_seconds() > 0

    def test_funnel_order(self):
        assert FUNNEL_EVENTS.index("start") < FUNNEL_EVENTS.index("pet_created")
        assert FUNNEL_EVENTS.index("pet_created") < FUNNEL_EVENTS.index("payment_succeeded")

    def test_funnel_events_not_empty(self):
        assert len(FUNNEL_EVENTS) > 0

    def test_funnel_events_all_strings(self):
        for event in FUNNEL_EVENTS:
            assert isinstance(event, str)

    def test_return_gap_12_hours(self):
        assert RETURN_GAP.total_seconds() == 12 * 3600

    def test_onboarding_event(self):
        assert "onboarding_started" in FUNNEL_EVENTS

    def test_payment_events(self):
        for e in ("payment_started", "payment_pending", "payment_succeeded", "payment_failed"):
            assert e in FUNNEL_EVENTS

    def test_user_returned_event(self):
        assert "user_returned" in FUNNEL_EVENTS


# ── DB tests ─────────────────────────────────────────────────

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest

_MOD = "backend.services.analytics"


@pytest.fixture
def analytics_db(db_session):
    @asynccontextmanager
    async def _session():
        yield db_session

    with patch(f"{_MOD}.async_session", _session):
        yield db_session


@pytest.mark.asyncio
async def test_track_event_persists(analytics_db):
    from sqlalchemy import select
    from zoo_shared.db.models import AnalyticsEvent

    from backend.services.analytics import track_event

    await track_event(30001, "start", source="bot")
    result = await analytics_db.execute(
        select(AnalyticsEvent).where(AnalyticsEvent.user_id == 30001)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].event_name == "start"


@pytest.mark.asyncio
async def test_track_event_with_payload(analytics_db):
    from sqlalchemy import select
    from zoo_shared.db.models import AnalyticsEvent

    from backend.services.analytics import track_event

    await track_event(30002, "payment_succeeded", payload={"amount": 299})
    result = await analytics_db.execute(
        select(AnalyticsEvent).where(AnalyticsEvent.user_id == 30002)
    )
    row = result.scalars().first()
    assert row is not None
    assert "299" in row.payload_json


@pytest.mark.asyncio
async def test_build_funnel_report_returns_string(analytics_db):
    from backend.services.analytics import build_funnel_report

    report = await build_funnel_report(days=7)
    assert isinstance(report, str)
    assert "Воронка" in report
    assert "start" in report


@pytest.mark.asyncio
async def test_track_user_activity_first_visit_no_return_event(analytics_db):
    from sqlalchemy import select
    from zoo_shared.db.models import AnalyticsEvent

    from backend.services.analytics import track_user_activity

    await track_user_activity(30003, source="bot")
    result = await analytics_db.execute(
        select(AnalyticsEvent).where(
            AnalyticsEvent.user_id == 30003,
            AnalyticsEvent.event_name == "user_returned",
        )
    )
    assert result.scalars().first() is None
