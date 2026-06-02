"""Food, water, and allergy REST API."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from zoo_shared.db.models import Allergy, FoodEntry, Pet, WaterEntry
from zoo_shared.schemas.food import (
    AllergyCreate,
    AllergyRead,
    FoodEntryCreate,
    FoodEntryRead,
    WaterEntryCreate,
    WaterEntryRead,
)

from backend.deps import get_session

router = APIRouter(prefix="/food", tags=["food"])


async def _check_pet_ownership(session: AsyncSession, user_id: int, pet_id: int) -> Pet:
    result = await session.execute(select(Pet).where(Pet.id == pet_id, Pet.user_id == user_id))
    pet = result.scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


# ══════════════ FOOD ENTRIES ══════════════


@router.get("/entries/{pet_id}", response_model=list[FoodEntryRead])
async def list_food_entries(
    pet_id: int,
    user_id: int,
    days: int = 7,
    session: AsyncSession = Depends(get_session),
):
    await _check_pet_ownership(session, user_id, pet_id)
    since = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(FoodEntry)
        .where(
            FoodEntry.pet_id == pet_id,
            FoodEntry.meal_time >= since,
        )
        .order_by(FoodEntry.meal_time.desc())
    )
    return result.scalars().all()


@router.post("/entries", response_model=FoodEntryRead, status_code=201)
async def create_food_entry(
    user_id: int,
    body: FoodEntryCreate,
    session: AsyncSession = Depends(get_session),
):
    await _check_pet_ownership(session, user_id, body.pet_id)
    entry = FoodEntry(
        pet_id=body.pet_id,
        food_name=body.food_name,
        portion=body.portion,
        portion_grams=body.portion_grams,
        notes=body.notes,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}", status_code=204)
async def delete_food_entry(entry_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(FoodEntry).where(FoodEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Food entry not found")
    await _check_pet_ownership(session, user_id, entry.pet_id)
    await session.delete(entry)
    await session.commit()


@router.delete("/entries/clear/{pet_id}", status_code=204)
async def clear_food_entries(pet_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    await _check_pet_ownership(session, user_id, pet_id)
    result = await session.execute(select(FoodEntry).where(FoodEntry.pet_id == pet_id))
    entries = result.scalars().all()
    for e in entries:
        await session.delete(e)
    await session.commit()


# ══════════════ WATER ENTRIES ══════════════


@router.get("/water/{pet_id}", response_model=list[WaterEntryRead])
async def list_water_entries(
    pet_id: int,
    user_id: int,
    days: int = 7,
    session: AsyncSession = Depends(get_session),
):
    await _check_pet_ownership(session, user_id, pet_id)
    since = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(WaterEntry)
        .where(
            WaterEntry.pet_id == pet_id,
            WaterEntry.recorded_at >= since,
        )
        .order_by(WaterEntry.recorded_at.desc())
    )
    return result.scalars().all()


@router.post("/water", response_model=WaterEntryRead, status_code=201)
async def create_water_entry(
    user_id: int,
    body: WaterEntryCreate,
    session: AsyncSession = Depends(get_session),
):
    await _check_pet_ownership(session, user_id, body.pet_id)
    entry = WaterEntry(pet_id=body.pet_id, amount_ml=body.amount_ml)
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


@router.delete("/water/{entry_id}", status_code=204)
async def delete_water_entry(entry_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WaterEntry).where(WaterEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Water entry not found")
    await _check_pet_ownership(session, user_id, entry.pet_id)
    await session.delete(entry)
    await session.commit()


@router.delete("/water/clear/{pet_id}", status_code=204)
async def clear_water_entries(pet_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    await _check_pet_ownership(session, user_id, pet_id)
    result = await session.execute(select(WaterEntry).where(WaterEntry.pet_id == pet_id))
    entries = result.scalars().all()
    for e in entries:
        await session.delete(e)
    await session.commit()


# ══════════════ ALLERGIES ══════════════


@router.get("/allergies/{pet_id}", response_model=list[AllergyRead])
async def list_allergies(pet_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    await _check_pet_ownership(session, user_id, pet_id)
    result = await session.execute(select(Allergy).where(Allergy.pet_id == pet_id))
    return result.scalars().all()


@router.get("/allergies/by_user/{user_id}")
async def list_allergies_by_user(user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Allergy).join(Pet, Pet.id == Allergy.pet_id).where(Pet.user_id == user_id))
    allergies = result.scalars().all()
    return [
        {
            "id": a.id,
            "pet_id": a.pet_id,
            "allergen": a.allergen,
            "reaction": a.reaction,
            "notes": a.notes,
        }
        for a in allergies
    ]


@router.post("/allergies", response_model=AllergyRead, status_code=201)
async def create_allergy(
    user_id: int,
    body: AllergyCreate,
    session: AsyncSession = Depends(get_session),
):
    await _check_pet_ownership(session, user_id, body.pet_id)
    allergy = Allergy(
        pet_id=body.pet_id,
        allergen=body.allergen,
        reaction=body.reaction,
        notes=body.notes,
    )
    session.add(allergy)
    await session.commit()
    await session.refresh(allergy)
    return allergy


@router.delete("/allergies/{allergy_id}", status_code=204)
async def delete_allergy(allergy_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Allergy).join(Pet, Pet.id == Allergy.pet_id).where(Allergy.id == allergy_id, Pet.user_id == user_id)
    )
    allergy = result.scalar_one_or_none()
    if not allergy:
        raise HTTPException(status_code=404, detail="Allergy not found")
    await session.delete(allergy)
    await session.commit()


# ══════════════ DAILY SUMMARY ══════════════


@router.get("/daily/{pet_id}")
async def daily_summary(pet_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    """Today's food and water totals for a pet."""
    await _check_pet_ownership(session, user_id, pet_id)
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)

    food_result = await session.execute(
        select(FoodEntry)
        .where(
            FoodEntry.pet_id == pet_id,
            and_(FoodEntry.meal_time >= today_start, FoodEntry.meal_time < today_end),
        )
        .order_by(FoodEntry.meal_time)
    )
    foods = food_result.scalars().all()

    water_result = await session.execute(
        select(WaterEntry)
        .where(
            WaterEntry.pet_id == pet_id,
            and_(WaterEntry.recorded_at >= today_start, WaterEntry.recorded_at < today_end),
        )
        .order_by(WaterEntry.recorded_at)
    )
    waters = water_result.scalars().all()

    total_grams = sum(f.portion_grams or 0 for f in foods)
    total_ml = sum(w.amount_ml for w in waters)

    return {
        "pet_id": pet_id,
        "food_entries": [
            {
                "id": f.id,
                "food_name": f.food_name,
                "portion": f.portion,
                "portion_grams": f.portion_grams,
                "meal_time": f.meal_time.isoformat(),
            }
            for f in foods
        ],
        "water_entries": [
            {"id": w.id, "amount_ml": w.amount_ml, "recorded_at": w.recorded_at.isoformat()} for w in waters
        ],
        "total_grams": total_grams,
        "total_ml": total_ml,
    }
