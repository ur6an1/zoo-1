"""Medical schemas (vaccination, vet visit, weight, document)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class VaccinationCreate(BaseModel):
    pet_id: int
    name: str
    date_done: date
    next_date: date | None = None
    notes: str = ""


class VaccinationRead(BaseModel):
    id: int
    pet_id: int
    name: str
    date_done: date
    next_date: date | None
    notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class VetVisitCreate(BaseModel):
    pet_id: int
    visit_date: date
    diagnosis: str = ""
    treatment: str = ""
    notes: str = ""


class VetVisitRead(BaseModel):
    id: int
    pet_id: int
    visit_date: date
    diagnosis: str
    treatment: str
    notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WeightRecordCreate(BaseModel):
    pet_id: int
    weight: float


class WeightRecordRead(BaseModel):
    id: int
    pet_id: int
    weight: float
    recorded_at: datetime

    model_config = {"from_attributes": True}
