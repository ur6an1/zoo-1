"""Subscription schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SubscriptionStatus(BaseModel):
    user_id: int
    plan_tier: str
    is_premium: bool
    premium_until: datetime | None
    ai_requests_today: int
    weather_notify: bool


class SubscriptionGrant(BaseModel):
    user_id: int
    days: int
    plan_tier: str = "pro"
