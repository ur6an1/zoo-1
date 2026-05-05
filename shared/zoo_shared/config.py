"""Конфигурация проекта через Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Required
    BOT_TOKEN: str = ""
    DATABASE_URL: str = "postgresql+asyncpg://zoo:changeme@postgres:5432/zoo_bot"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # AI Providers
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TRANSCRIBE_MODEL: str = "whisper-1"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_SITE_URL: str = ""
    OPENROUTER_APP_NAME: str = "zoo_bot"

    # Features
    BOT_TIMEZONE: str = "Europe/Moscow"
    WEATHER_API_KEY: str = ""

    # Payments
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    RECEIPT_EMAIL: str = ""
    PAYMENT_RETURN_URL: str = ""

    # Limits
    FREE_AI_LIMIT: int = 10
    FREE_PET_LIMIT: int = 2
    AI_MAX_TOKENS_VISION: int = 1600
    AI_MAX_TOKENS_TEXT: int = 1800

    # Admin
    ADMIN_IDS: list[int] = []

    # Internal
    BACKEND_URL: str = "http://backend:8000"

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: str | list) -> list[int]:
        if isinstance(v, list):
            return v
        if not v or not isinstance(v, str):
            return []
        ids = []
        for chunk in v.split(","):
            chunk = chunk.strip()
            if chunk.isdigit():
                ids.append(int(chunk))
        return ids


@lru_cache
def get_settings() -> Settings:
    return Settings()
