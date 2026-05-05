"""Reminder schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReminderCreate(BaseModel):
    user_id: int
    pet_id: int
    title: str
    description: str = ""
    category: str = "custom"
    remind_at: datetime
    repeat: str = "once"


class ReminderRead(BaseModel):
    id: int
    user_id: int
    pet_id: int
    title: str
    description: str
    category: str
    remind_at: datetime
    repeat: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
