"""Конфигурация проекта через Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True)

    # Required
    BOT_TOKEN: str = ""
    DATABASE_URL: str = "postgresql+asyncpg://zoo:changeme@postgres:5432/zoo_bot"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # AI Providers — единый провайдер OpenRouter (chat + vision + transcription)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "deepseek/deepseek-v4-flash"  # основная текстовая модель
    OPENROUTER_VISION_MODEL: str = "openai/gpt-4o-mini"  # модель для image_url-запросов
    OPENROUTER_TRANSCRIBE_MODEL: str = "openai/whisper-1"  # модель для /audio/transcriptions
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

    # Legal docs
    LEGAL_SELLER_NAME: str = ""
    LEGAL_SELLER_INN: str = ""
    LEGAL_SUPPORT_CONTACT: str = ""
    LEGAL_SUPPORT_EMAIL: str = ""

    # Internal
    BACKEND_URL: str = "http://backend:8000"
    INTERNAL_API_KEY: str = ""

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

    @property
    def legal_docs_configured(self) -> bool:
        return all(
            value.strip() for value in (self.LEGAL_SELLER_NAME, self.LEGAL_SELLER_INN, self.LEGAL_SUPPORT_CONTACT)
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
