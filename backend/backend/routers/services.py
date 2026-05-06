"""AI services & utilities proxy endpoints."""

from __future__ import annotations

import base64
from types import SimpleNamespace

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.charts import generate_daily_timeline, generate_feeding_chart
from backend.services.norms import calc_food_norm, calc_progress_bar
from backend.services.provider_health import is_ai_operational, is_card_payment_operational
from backend.services.weather import generate_pet_weather_alert, get_weather

router = APIRouter(prefix="/services", tags=["services"])


# ══════════════ PROVIDER HEALTH ══════════════


@router.get("/health/ai")
async def ai_health():
    return {"operational": await is_ai_operational()}


@router.get("/health/card_payment")
async def card_payment_health():
    return {"operational": await is_card_payment_operational()}


# ══════════════ WEATHER ══════════════


@router.get("/weather/{city}")
async def weather(city: str):
    data = await get_weather(city)
    return {"data": data}


class WeatherAlertRequest(BaseModel):
    weather_data: dict
    species: str
    pet_name: str = ""


@router.post("/weather/alert")
async def weather_alert(body: WeatherAlertRequest):
    result = generate_pet_weather_alert(body.weather_data, body.species)
    return {"alert": result}


# ══════════════ NORMS ══════════════


class NormRequest(BaseModel):
    species: str
    weight_kg: float | None = None
    age_months: int | None = None


@router.post("/norms/food")
async def food_norm(body: NormRequest):
    result = calc_food_norm(body.species, body.weight_kg, body.age_months)
    return result


class ProgressBarRequest(BaseModel):
    current: float
    target: float
    width: int = 10


@router.post("/norms/progress_bar")
async def progress_bar(body: ProgressBarRequest):
    bar = calc_progress_bar(body.current, body.target, body.width)
    return {"bar": bar}


# ══════════════ CHARTS ══════════════


class ChartRequest(BaseModel):
    pet_name: str
    entries: list[dict]


def _entries_to_objects(entries: list[dict]) -> list:
    """Convert dicts to SimpleNamespace objects for chart functions."""
    return [SimpleNamespace(**e) for e in entries]


@router.post("/charts/feeding")
async def feeding_chart(body: ChartRequest):
    entry_objects = _entries_to_objects(body.entries)
    img_bytes = generate_feeding_chart(entry_objects, [], {0: body.pet_name})
    if img_bytes:
        return {"image": base64.b64encode(img_bytes).decode()}
    return {"image": None}


@router.post("/charts/timeline")
async def timeline_chart(body: ChartRequest):
    entry_objects = _entries_to_objects(body.entries)
    img_bytes = generate_daily_timeline(entry_objects, [], {0: body.pet_name})
    if img_bytes:
        return {"image": base64.b64encode(img_bytes).decode()}
    return {"image": None}


# ══════════════ VOICE NOTES ══════════════


@router.get("/norms/{user_id}")
async def user_norms(user_id: int):
    from datetime import date, datetime

    from sqlalchemy import and_, select
    from zoo_shared.db import async_session
    from zoo_shared.db.models import FoodEntry, Pet, WaterEntry

    async with async_session() as session:
        result = await session.execute(
            select(Pet).where(Pet.user_id == user_id)
        )
        pets = result.scalars().all()
        if not pets:
            return {"no_pets": True, "text": ""}

        today = date.today()
        today_start = datetime(today.year, today.month, today.day)
        today_end = datetime(today.year, today.month, today.day, 23, 59, 59)

        lines = [f"\U0001f4ca <b>Нормы еды и воды — {today.strftime('%d.%m.%Y')}</b>\n"]

        for pet in pets:
            norm = calc_food_norm(pet.species, pet.weight, pet.age_months())

            food_result = await session.execute(
                select(FoodEntry).where(
                    and_(
                        FoodEntry.pet_id == pet.id,
                        FoodEntry.meal_time >= today_start,
                        FoodEntry.meal_time <= today_end,
                    )
                )
            )
            food_entries = food_result.scalars().all()
            food_today_g = sum(e.portion_grams for e in food_entries if e.portion_grams)

            water_result = await session.execute(
                select(WaterEntry).where(
                    and_(
                        WaterEntry.pet_id == pet.id,
                        WaterEntry.recorded_at >= today_start,
                        WaterEntry.recorded_at <= today_end,
                    )
                )
            )
            water_entries = water_result.scalars().all()
            water_today_ml = sum(e.amount_ml for e in water_entries)

            meals_today = len(food_entries)

            lines.append(f"{pet.species_emoji} <b>{pet.name}</b>")

            if norm["food_g"] == 0:
                lines.append(f"  \u26a0\ufe0f {norm['description']}")
            else:
                lines.append(f"  \U0001f37d Норма еды: <b>{norm['food_g']} г/день</b>")
                lines.append(f"  \U0001f4a7 Норма воды: <b>{norm['water_ml']} мл/день</b>")
                lines.append(f"  \U0001f550 Кормлений в день: <b>{norm['meals_per_day']}</b>")

                lines.append("")
                lines.append("  <b>Прогресс за сегодня:</b>")

                food_bar = calc_progress_bar(food_today_g, norm["food_g"])
                lines.append(f"  \U0001f37d Еда: {food_today_g:.0f}/{norm['food_g']} г")
                lines.append(f"  {food_bar}")

                water_bar = calc_progress_bar(water_today_ml, norm["water_ml"])
                lines.append(f"  \U0001f4a7 Вода: {water_today_ml}/{norm['water_ml']} мл")
                lines.append(f"  {water_bar}")

                lines.append(f"  \U0001f37d Кормлений сегодня: {meals_today}/{norm['meals_per_day']}")

            lines.append("")

    return {"no_pets": False, "text": "\n".join(lines)}


@router.get("/voice_notes/by_user/{user_id}")
async def list_voice_notes_by_user(user_id: int):
    from sqlalchemy import select
    from zoo_shared.db import async_session
    from zoo_shared.db.models import Pet, VoiceNote

    async with async_session() as session:
        notes_result = await session.execute(
            select(VoiceNote).where(VoiceNote.user_id == user_id)
            .order_by(VoiceNote.created_at.desc())
            .limit(10)
        )
        notes = notes_result.scalars().all()

        pet_ids = {n.pet_id for n in notes}
        pet_map: dict[int, str] = {}
        if pet_ids:
            pets_result = await session.execute(
                select(Pet).where(Pet.id.in_(pet_ids))
            )
            for p in pets_result.scalars().all():
                pet_map[p.id] = f"{p.species_emoji} {p.name}"

    return [
        {
            "id": n.id,
            "pet_id": n.pet_id,
            "pet_label": pet_map.get(n.pet_id, "?"),
            "file_id": n.file_id,
            "transcription": n.transcription or "",
            "created_at": n.created_at.isoformat(),
            "created_at_str": n.created_at.strftime("%d.%m.%Y %H:%M"),
        }
        for n in notes
    ]


@router.get("/voice_notes/{pet_id}")
async def list_voice_notes(pet_id: int, user_id: int):
    from sqlalchemy import select
    from zoo_shared.db import async_session
    from zoo_shared.db.models import Pet, VoiceNote

    async with async_session() as session:
        result = await session.execute(
            select(Pet).where(Pet.id == pet_id, Pet.user_id == user_id)
        )
        pet = result.scalar_one_or_none()
        if not pet:
            return {"notes": [], "pet_name": ""}

        notes_result = await session.execute(
            select(VoiceNote).where(VoiceNote.pet_id == pet_id)
            .order_by(VoiceNote.created_at.desc())
        )
        notes = notes_result.scalars().all()

    return {
        "pet_name": pet.name,
        "notes": [
            {
                "id": n.id, "file_id": n.file_id,
                "transcription": n.transcription,
                "created_at": n.created_at.isoformat(),
            }
            for n in notes
        ],
    }


@router.post("/voice_notes")
async def create_voice_note(
    pet_id: int, user_id: int, file_id: str, transcription: str = "",
):
    from sqlalchemy import select
    from zoo_shared.db import async_session
    from zoo_shared.db.models import Pet, VoiceNote

    async with async_session() as session:
        pet_result = await session.execute(
            select(Pet).where(Pet.id == pet_id, Pet.user_id == user_id)
        )
        pet = pet_result.scalar_one_or_none()
        if not pet:
            return None

        note = VoiceNote(
            pet_id=pet_id, user_id=user_id,
            file_id=file_id, transcription=transcription,
        )
        session.add(note)
        await session.commit()
        await session.refresh(note)
    return {
        "id": note.id, "pet_id": note.pet_id,
        "pet_name": pet.name,
        "file_id": note.file_id, "transcription": note.transcription,
        "created_at": note.created_at.isoformat(),
    }


@router.delete("/voice_notes/{note_id}", status_code=204)
async def delete_voice_note(note_id: int, user_id: int):
    from sqlalchemy import select
    from zoo_shared.db import async_session
    from zoo_shared.db.models import VoiceNote

    async with async_session() as session:
        result = await session.execute(
            select(VoiceNote).where(VoiceNote.id == note_id, VoiceNote.user_id == user_id)
        )
        note = result.scalar_one_or_none()
        if note:
            await session.delete(note)
            await session.commit()
