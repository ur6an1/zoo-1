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
