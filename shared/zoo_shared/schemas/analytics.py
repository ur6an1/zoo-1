"""Analytics schemas."""

from __future__ import annotations

from pydantic import BaseModel


class AnalyticsEventCreate(BaseModel):
    user_id: int
    event_name: str
    source: str = ""
    payload: dict | None = None
