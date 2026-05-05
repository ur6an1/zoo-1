"""Pet schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class PetCreate(BaseModel):
    user_id: int
    name: str
    species: str
    breed: str = ""
    birth_date: date | None = None
    weight: float | None = None
    photo_file_id: str | None = None


class PetUpdate(BaseModel):
    name: str | None = None
    breed: str | None = None
    birth_date: date | None = None
    weight: float | None = None
    target_weight: float | None = None
    photo_file_id: str | None = None


class PetRead(BaseModel):
    id: int
    user_id: int
    name: str
    species: str
    breed: str
    birth_date: date | None
    weight: float | None
    target_weight: float | None
    photo_file_id: str | None
    created_at: datetime
    age_str: str = ""
    species_emoji: str = "🐾"

    model_config = {"from_attributes": True}
