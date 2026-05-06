"""Pets REST API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from zoo_shared.db.models import (
    Allergy,
    Document,
    FoodEntry,
    Pet,
    Reminder,
    Vaccination,
    VetVisit,
    WaterEntry,
    WeightRecord,
)
from zoo_shared.schemas.pet import PetCreate, PetRead, PetUpdate

from backend.deps import get_session

router = APIRouter(prefix="/pets", tags=["pets"])


def _pet_to_read(pet: Pet) -> dict:
    data = {
        "id": pet.id,
        "user_id": pet.user_id,
        "name": pet.name,
        "species": pet.species,
        "breed": pet.breed,
        "birth_date": pet.birth_date,
        "weight": pet.weight,
        "target_weight": pet.target_weight,
        "photo_file_id": pet.photo_file_id,
        "created_at": pet.created_at,
        "age_str": pet.age_str(),
        "species_emoji": pet.species_emoji,
    }
    return data


@router.get("/by_user/{user_id}", response_model=list[PetRead])
async def list_pets(user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Pet).where(Pet.user_id == user_id))
    pets = result.scalars().all()
    return [_pet_to_read(p) for p in pets]


@router.get("/{pet_id}", response_model=PetRead)
async def get_pet(pet_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Pet).where(Pet.id == pet_id, Pet.user_id == user_id)
    )
    pet = result.scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    return _pet_to_read(pet)


@router.post("/", response_model=PetRead, status_code=201)
async def create_pet(body: PetCreate, session: AsyncSession = Depends(get_session)):
    pet = Pet(
        user_id=body.user_id,
        name=body.name,
        species=body.species,
        breed=body.breed,
        birth_date=body.birth_date,
        weight=body.weight,
        photo_file_id=body.photo_file_id,
    )
    session.add(pet)
    await session.commit()
    await session.refresh(pet)
    return _pet_to_read(pet)


@router.patch("/{pet_id}", response_model=PetRead)
async def update_pet(
    pet_id: int,
    user_id: int,
    body: PetUpdate,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Pet).where(Pet.id == pet_id, Pet.user_id == user_id)
    )
    pet = result.scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(pet, field, value)
    await session.commit()
    await session.refresh(pet)
    return _pet_to_read(pet)


@router.delete("/{pet_id}", status_code=204)
async def delete_pet(pet_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Pet).where(Pet.id == pet_id, Pet.user_id == user_id)
    )
    pet = result.scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    await session.delete(pet)
    await session.commit()


@router.get("/{pet_id}/stats")
async def pet_stats(pet_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Pet).where(Pet.id == pet_id, Pet.user_id == user_id)
    )
    pet = result.scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    counts = {}
    for label, model in [
        ("vaccinations", Vaccination),
        ("vet_visits", VetVisit),
        ("weight_records", WeightRecord),
        ("food_entries", FoodEntry),
        ("water_entries", WaterEntry),
        ("allergies", Allergy),
        ("documents", Document),
    ]:
        r = await session.execute(
            select(func.count(model.id)).where(model.pet_id == pet_id)
        )
        counts[label] = int(r.scalar_one() or 0)

    r = await session.execute(
        select(func.count(Reminder.id)).where(
            Reminder.pet_id == pet_id, Reminder.is_active == True  # noqa: E712
        )
    )
    counts["active_reminders"] = int(r.scalar_one() or 0)

    last_vac = None
    r = await session.execute(
        select(Vaccination).where(Vaccination.pet_id == pet_id)
        .order_by(Vaccination.date_done.desc()).limit(1)
    )
    v = r.scalar_one_or_none()
    if v:
        last_vac = {"name": v.name, "date_done": v.date_done.isoformat()}

    next_vac = None
    r = await session.execute(
        select(Vaccination).where(
            Vaccination.pet_id == pet_id,
            Vaccination.next_date != None,  # noqa: E711
        ).order_by(Vaccination.next_date).limit(1)
    )
    v = r.scalar_one_or_none()
    if v and v.next_date:
        next_vac = {"name": v.name, "next_date": v.next_date.isoformat()}

    last_visit = None
    r = await session.execute(
        select(VetVisit).where(VetVisit.pet_id == pet_id)
        .order_by(VetVisit.visit_date.desc()).limit(1)
    )
    vv = r.scalar_one_or_none()
    if vv:
        last_visit = {"visit_date": vv.visit_date.isoformat()}

    last_weight = None
    r = await session.execute(
        select(WeightRecord).where(WeightRecord.pet_id == pet_id)
        .order_by(WeightRecord.recorded_at.desc()).limit(1)
    )
    w = r.scalar_one_or_none()
    if w:
        last_weight = {"weight": w.weight, "recorded_at": w.recorded_at.isoformat()}

    return {
        "pet": _pet_to_read(pet),
        "counts": counts,
        "last_vaccination": last_vac,
        "next_vaccination": next_vac,
        "last_visit": last_visit,
        "last_weight": last_weight,
    }


@router.get("/{pet_id}/export")
async def pet_export(pet_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Pet).where(Pet.id == pet_id, Pet.user_id == user_id)
    )
    pet = result.scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    vaccinations = (await session.execute(
        select(Vaccination).where(Vaccination.pet_id == pet_id)
        .order_by(Vaccination.date_done.desc())
    )).scalars().all()

    visits = (await session.execute(
        select(VetVisit).where(VetVisit.pet_id == pet_id)
        .order_by(VetVisit.visit_date.desc())
    )).scalars().all()

    weights = (await session.execute(
        select(WeightRecord).where(WeightRecord.pet_id == pet_id)
        .order_by(WeightRecord.recorded_at.desc())
    )).scalars().all()

    allergies = (await session.execute(
        select(Allergy).where(Allergy.pet_id == pet_id)
    )).scalars().all()

    return {
        "pet": _pet_to_read(pet),
        "vaccinations": [
            {"id": v.id, "name": v.name, "date_done": v.date_done.isoformat(),
             "next_date": v.next_date.isoformat() if v.next_date else None,
             "notes": v.notes}
            for v in vaccinations
        ],
        "vet_visits": [
            {"id": v.id, "visit_date": v.visit_date.isoformat(),
             "diagnosis": v.diagnosis, "treatment": v.treatment, "notes": v.notes}
            for v in visits
        ],
        "weight_records": [
            {"id": w.id, "weight": w.weight, "recorded_at": w.recorded_at.isoformat()}
            for w in weights
        ],
        "allergies": [
            {"id": a.id, "allergen": a.allergen, "reaction": a.reaction, "notes": a.notes}
            for a in allergies
        ],
    }


@router.get("/count/{user_id}")
async def pet_count(user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(func.count(Pet.id)).where(Pet.user_id == user_id)
    )
    return {"count": int(result.scalar_one() or 0)}
