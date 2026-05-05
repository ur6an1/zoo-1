"""Tests for backend.services.vision — pure function helpers and prompts."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")

from backend.services.vision import (
    FOOD_ANALYSIS_PROMPT,
    OPENAI_URL,
    PET_ANALYSIS_PROMPT,
    _chat_headers,
    _chat_model,
    _chat_url,
    _make_nutrition_prompt,
    _make_symptoms_prompt,
    _provider,
    has_any_ai,
)


class TestHasAnyAi:
    def test_returns_bool(self):
        result = has_any_ai()
        assert isinstance(result, bool)


class TestProvider:
    def test_returns_string_or_none(self):
        result = _provider()
        assert result in (None, "openrouter", "openai")


class TestChatUrl:
    def test_returns_url(self):
        url = _chat_url()
        assert isinstance(url, str)
        assert "http" in url or url == OPENAI_URL


class TestChatModel:
    def test_returns_model_string(self):
        model = _chat_model()
        assert isinstance(model, str)
        assert len(model) > 0


class TestChatHeaders:
    def test_returns_dict_or_none(self):
        headers = _chat_headers()
        assert headers is None or isinstance(headers, dict)


class TestPrompts:
    def test_pet_analysis_prompt(self):
        assert "ветеринар" in PET_ANALYSIS_PROMPT.lower()
        assert len(PET_ANALYSIS_PROMPT) > 100

    def test_food_analysis_prompt(self):
        assert "питани" in FOOD_ANALYSIS_PROMPT.lower()
        assert len(FOOD_ANALYSIS_PROMPT) > 100

    def test_make_nutrition_prompt(self):
        prompt = _make_nutrition_prompt("Собака, Лабрадор, 3 года, 30 кг")
        assert "Лабрадор" in prompt
        assert "граммах" in prompt.lower() or "грамм" in prompt.lower()

    def test_make_symptoms_prompt(self):
        prompt = _make_symptoms_prompt("Кошка, Перс, 5 лет, 4 кг")
        assert "Перс" in prompt
        assert "ветеринар" in prompt.lower()

    def test_openai_url(self):
        assert "openai.com" in OPENAI_URL
