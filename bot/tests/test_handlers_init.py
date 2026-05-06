"""Tests for bot.handlers — router registration."""

from aiogram import Router

from bot.handlers import get_all_routers


class TestGetAllRouters:
    def test_returns_list(self):
        routers = get_all_routers()
        assert isinstance(routers, list)
        assert len(routers) > 0

    def test_all_are_routers(self):
        for r in get_all_routers():
            assert isinstance(r, Router)

    def test_expected_count(self):
        routers = get_all_routers()
        assert len(routers) == 17

    def test_unique_names(self):
        names = [r.name for r in get_all_routers()]
        assert len(names) == len(set(names))

    def test_expected_names(self):
        names = {r.name for r in get_all_routers()}
        expected = {
            "common", "pets", "reminders", "medical", "food",
            "tips", "emergency", "analysis", "photo", "norms",
            "compare", "voice", "calendar", "weight_goal",
            "subscription", "payment", "weather_handler",
        }
        assert expected == names
