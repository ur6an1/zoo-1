"""Food and water schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FoodEntryCreate(BaseModel):
    pet_id: int
    food_name: str
    portion: str = ""
    portion_grams: float | None = None
    notes: str = ""


class FoodEntryRead(BaseModel):
    id: int
    pet_id: int
    food_name: str
    portion: str
    portion_grams: float | None
    meal_time: datetime
    notes: str

    model_config = {"from_attributes": True}


class WaterEntryCreate(BaseModel):
    pet_id: int
    amount_ml: int


class WaterEntryRead(BaseModel):
    id: int
    pet_id: int
    amount_ml: int
    recorded_at: datetime

    model_config = {"from_attributes": True}


class AllergyCreate(BaseModel):
    pet_id: int
    allergen: str
    reaction: str = ""
    notes: str = ""


class AllergyRead(BaseModel):
    id: int
    pet_id: int
    allergen: str
    reaction: str
    notes: str

    model_config = {"from_attributes": True}
