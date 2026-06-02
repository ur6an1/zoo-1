"""Tests for zoo_shared.config — Settings validation."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")

from zoo_shared.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings(BOT_TOKEN="t", DATABASE_URL="sqlite:///:memory:")
        assert s.FREE_AI_LIMIT == 10
        assert s.FREE_PET_LIMIT == 2
        assert s.BOT_TIMEZONE == "Europe/Moscow"
        assert s.OPENROUTER_MODEL == "deepseek/deepseek-v4-flash"
        assert s.OPENROUTER_VISION_MODEL == "openai/gpt-4o-mini"
        assert s.OPENROUTER_TRANSCRIBE_MODEL == "openai/whisper-1"

    def test_parse_admin_ids_empty(self):
        s = Settings(BOT_TOKEN="t", DATABASE_URL="x", ADMIN_IDS="")
        assert s.ADMIN_IDS == []

    def test_parse_admin_ids_csv(self):
        s = Settings(BOT_TOKEN="t", DATABASE_URL="x", ADMIN_IDS="123,456,789")
        assert s.ADMIN_IDS == [123, 456, 789]

    def test_parse_admin_ids_spaces(self):
        s = Settings(BOT_TOKEN="t", DATABASE_URL="x", ADMIN_IDS="  11 , 22 ")
        assert s.ADMIN_IDS == [11, 22]

    def test_parse_admin_ids_list(self):
        s = Settings(BOT_TOKEN="t", DATABASE_URL="x", ADMIN_IDS=[1, 2])
        assert s.ADMIN_IDS == [1, 2]

    def test_parse_admin_ids_non_numeric(self):
        s = Settings(BOT_TOKEN="t", DATABASE_URL="x", ADMIN_IDS="abc,123")
        assert s.ADMIN_IDS == [123]
