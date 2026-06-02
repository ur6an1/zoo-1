"""Tests for backend.services.vision — pure function helpers and prompts."""

import asyncio
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")

import backend.services.vision as vision_mod
from backend.services.vision import (
    FOOD_ANALYSIS_PROMPT,
    PET_ANALYSIS_PROMPT,
    _chat_headers,
    _chat_model,
    _chat_url,
    _gpt_photo,
    _gpt_text,
    _make_nutrition_prompt,
    _make_symptoms_prompt,
    _provider,
    analyze_food_for_pet,
    analyze_food_photo,
    analyze_medical_test,
    analyze_pet_photo,
    compare_two_foods,
    consult_symptoms,
    has_any_ai,
    transcribe_voice,
)


class TestHasAnyAi:
    def test_returns_bool(self):
        result = has_any_ai()
        assert isinstance(result, bool)

    def test_true_with_openrouter_key(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-test")
        assert has_any_ai() is True

    def test_false_with_no_keys(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "")
        assert has_any_ai() is False


class TestProvider:
    def test_returns_string_or_none(self):
        result = _provider()
        assert result in (None, "openrouter")

    def test_openrouter_wins(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        assert _provider() == "openrouter"

    def test_none_when_no_keys(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "")
        assert _provider() is None


class TestChatUrl:
    def test_returns_url(self):
        url = _chat_url()
        assert isinstance(url, str)
        assert url.startswith("http")

    def test_openrouter_url(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        assert "openrouter.ai" in _chat_url()


class TestChatModel:
    def test_returns_model_string(self):
        model = _chat_model()
        assert isinstance(model, str)
        assert len(model) > 0

    def test_openrouter_model(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_MODEL", "openai/gpt-4o")
        assert _chat_model() == "openai/gpt-4o"

    def test_text_and_vision_models_split(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_VISION_MODEL", "openai/gpt-4o-mini")
        assert _chat_model() == "deepseek/deepseek-v4-flash"
        assert _chat_model(for_vision=False) == "deepseek/deepseek-v4-flash"
        assert _chat_model(for_vision=True) == "openai/gpt-4o-mini"


class TestChatHeaders:
    def test_returns_dict_or_none(self):
        headers = _chat_headers()
        assert headers is None or isinstance(headers, dict)

    def test_openrouter_headers(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_SITE_URL", "")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_APP_NAME", "")
        h = _chat_headers()
        assert h is not None
        assert "Authorization" in h
        assert "sk-or" in h["Authorization"]

    def test_openrouter_headers_with_site_url(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-or")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_SITE_URL", "https://example.com")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_APP_NAME", "myapp")
        h = _chat_headers()
        assert h is not None
        assert h.get("HTTP-Referer") == "https://example.com"
        assert h.get("X-Title") == "myapp"

    def test_no_keys_returns_none(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "")
        assert _chat_headers() is None


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


# ── async functions: early return when no AI keys ─────────────────────────────

import pytest
from backend.services.vision import (
    _gpt_photo,
    _gpt_text,
    analyze_food_for_pet,
    analyze_food_photo,
    analyze_medical_test,
    analyze_pet_photo,
    compare_two_foods,
    consult_symptoms,
    transcribe_voice,
)


@pytest.fixture(autouse=False)
def no_ai_keys(monkeypatch):
    monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "")


class TestAsyncNoAiKeys:
    @pytest.mark.asyncio
    async def test_gpt_photo_returns_none(self, no_ai_keys):
        result = await _gpt_photo("abc123", "prompt")
        assert result is None

    @pytest.mark.asyncio
    async def test_gpt_text_returns_none(self, no_ai_keys):
        result = await _gpt_text("question", "system")
        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_pet_photo_returns_none(self, no_ai_keys):
        assert await analyze_pet_photo(b"fake") is None

    @pytest.mark.asyncio
    async def test_analyze_food_photo_returns_none(self, no_ai_keys):
        assert await analyze_food_photo(b"fake") is None

    @pytest.mark.asyncio
    async def test_analyze_food_for_pet_returns_none(self, no_ai_keys):
        assert await analyze_food_for_pet(b"fake", "кот 3кг") is None

    @pytest.mark.asyncio
    async def test_consult_symptoms_returns_none(self, no_ai_keys):
        assert await consult_symptoms("кашель", "кот 3кг") is None

    @pytest.mark.asyncio
    async def test_compare_two_foods_returns_none(self, no_ai_keys):
        assert await compare_two_foods(b"img1", b"img2") is None

    @pytest.mark.asyncio
    async def test_analyze_medical_test_returns_none(self, no_ai_keys):
        assert await analyze_medical_test(b"fake", "кот 3кг") is None

    @pytest.mark.asyncio
    async def test_transcribe_voice_wrapper_returns_none(self, no_ai_keys):
        result = await transcribe_voice(b"fake audio")
        assert result is None


class TestOpenRouterOnly:
    """Guards confirming only OpenRouter is used for chat/vision."""

    def test_no_openrouter_key_headers_none(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "")
        assert _chat_headers() is None

    def test_no_openai_url_in_chat_url(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        assert "api.openai.com" not in _chat_url()

    @pytest.mark.asyncio
    async def test_no_openrouter_key_request_returns_none(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "")
        result = await vision_mod._request_chat_completion([{"role": "user", "content": "hi"}], 10)
        assert result is None

    @pytest.mark.asyncio
    async def test_request_uses_openrouter_url_and_model(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-test")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_MODEL", "openai/gpt-4o-mini")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_SITE_URL", "")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_APP_NAME", "")

        captured: dict = {}

        class _Resp:
            status = 200

            async def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        class _Sess:
            def post(self, url, **kwargs):
                captured["url"] = url
                captured["model"] = (kwargs.get("json") or {}).get("model")
                return _Resp()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        monkeypatch.setattr(vision_mod.aiohttp, "ClientSession", lambda: _Sess())
        result = await vision_mod._request_chat_completion([{"role": "user", "content": "hi"}], 10)
        assert result == "ok"
        assert "openrouter.ai" in captured["url"]
        assert captured["model"] == "openai/gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_openrouter_headers_attached(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-mykey")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_MODEL", "openai/gpt-4o-mini")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_SITE_URL", "https://zoo.example")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_APP_NAME", "zoobuddy")

        captured_headers: dict = {}

        class _Resp:
            status = 200

            async def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        class _Sess:
            def post(self, url, *, headers=None, **kwargs):
                if headers:
                    captured_headers.update(headers)
                return _Resp()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        monkeypatch.setattr(vision_mod.aiohttp, "ClientSession", lambda: _Sess())
        await vision_mod._request_chat_completion([{"role": "user", "content": "hi"}], 10)
        assert "Bearer sk-mykey" in captured_headers.get("Authorization", "")
        assert captured_headers.get("HTTP-Referer") == "https://zoo.example"
        assert captured_headers.get("X-Title") == "zoobuddy"

    @pytest.mark.asyncio
    async def test_http_401_marks_ai_unavailable(self, monkeypatch):
        import backend.services.provider_health as ph

        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-test")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_MODEL", "openai/gpt-4o-mini")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_SITE_URL", "")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_APP_NAME", "")
        ph._CACHE["ai"]["status"] = True

        class _Resp:
            status = 401

            async def text(self):
                return "Unauthorized"

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        class _Sess:
            def post(self, *a, **kw):
                return _Resp()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        monkeypatch.setattr(vision_mod.aiohttp, "ClientSession", lambda: _Sess())
        result = await vision_mod._request_chat_completion([{"role": "user", "content": "hi"}], 10)
        assert result is None
        assert ph._CACHE["ai"]["status"] is False

    @pytest.mark.asyncio
    async def test_http_5xx_returns_none_without_marking(self, monkeypatch):
        import backend.services.provider_health as ph

        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-test")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_MODEL", "openai/gpt-4o-mini")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_SITE_URL", "")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_APP_NAME", "")
        ph._CACHE["ai"]["status"] = True

        class _Resp:
            status = 500

            async def text(self):
                return "Server Error"

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        class _Sess:
            def post(self, *a, **kw):
                return _Resp()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        monkeypatch.setattr(vision_mod.aiohttp, "ClientSession", lambda: _Sess())
        result = await vision_mod._request_chat_completion([{"role": "user", "content": "hi"}], 10)
        assert result is None
        assert ph._CACHE["ai"]["status"] is True

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self, monkeypatch):
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-test")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_MODEL", "openai/gpt-4o-mini")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_SITE_URL", "")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_APP_NAME", "")

        class _Resp:
            async def __aenter__(self):
                raise asyncio.TimeoutError()

            async def __aexit__(self, *a):
                pass

        class _Sess:
            def post(self, *a, **kw):
                return _Resp()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        monkeypatch.setattr(vision_mod.aiohttp, "ClientSession", lambda: _Sess())
        result = await vision_mod._request_chat_completion([{"role": "user", "content": "hi"}], 10)
        assert result is None

    @pytest.mark.asyncio
    async def test_gpt_photo_uses_vision_model(self, monkeypatch):
        """_gpt_photo должен слать OPENROUTER_VISION_MODEL, а не основную текстовую."""
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-test")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_VISION_MODEL", "openai/gpt-4o-mini")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_SITE_URL", "")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_APP_NAME", "")

        captured: dict = {}

        class _Resp:
            status = 200

            async def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        class _Sess:
            def post(self, url, **kwargs):
                captured["model"] = (kwargs.get("json") or {}).get("model")
                return _Resp()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        monkeypatch.setattr(vision_mod.aiohttp, "ClientSession", lambda: _Sess())
        result = await vision_mod._gpt_photo("dGVzdA==", "describe")
        assert result == "ok"
        assert captured["model"] == "openai/gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_gpt_text_uses_text_model(self, monkeypatch):
        """_gpt_text должен слать OPENROUTER_MODEL (основная текстовая)."""
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_API_KEY", "sk-test")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_VISION_MODEL", "openai/gpt-4o-mini")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_SITE_URL", "")
        monkeypatch.setattr(vision_mod._settings, "OPENROUTER_APP_NAME", "")

        captured: dict = {}

        class _Resp:
            status = 200

            async def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        class _Sess:
            def post(self, url, **kwargs):
                captured["model"] = (kwargs.get("json") or {}).get("model")
                return _Resp()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        monkeypatch.setattr(vision_mod.aiohttp, "ClientSession", lambda: _Sess())
        result = await vision_mod._gpt_text("hi", "you are vet")
        assert result == "ok"
        assert captured["model"] == "deepseek/deepseek-v4-flash"
