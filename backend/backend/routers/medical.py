"""Medical REST API (vaccinations, vet visits, weight records, documents)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from zoo_shared.db.models import Document, Pet, Vaccination, VetVisit, WeightRecord
from zoo_shared.schemas.medical import (
    VaccinationCreate,
    VaccinationRead,
    VetVisitCreate,
    VetVisitRead,
    WeightRecordCreate,
    WeightRecordRead,
)

from backend.deps import get_session

router = APIRouter(prefix="/medical", tags=["medical"])


# ── helpers ──


async def _check_pet_ownership(session: AsyncSession, user_id: int, pet_id: int) -> Pet:
    result = await session.execute(select(Pet).where(Pet.id == pet_id, Pet.user_id == user_id))
    pet = result.scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


# ══════════════ VACCINATIONS ══════════════


@router.get("/vaccinations/{pet_id}", response_model=list[VaccinationRead])
async def list_vaccinations(pet_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    await _check_pet_ownership(session, user_id, pet_id)
    result = await session.execute(
        select(Vaccination).where(Vaccination.pet_id == pet_id).order_by(Vaccination.date_done.desc())
    )
    return result.scalars().all()


@router.post("/vaccinations", response_model=VaccinationRead, status_code=201)
async def create_vaccination(
    user_id: int,
    body: VaccinationCreate,
    session: AsyncSession = Depends(get_session),
):
    await _check_pet_ownership(session, user_id, body.pet_id)
    vac = Vaccination(
        pet_id=body.pet_id,
        name=body.name,
        date_done=body.date_done,
        next_date=body.next_date,
        notes=body.notes,
    )
    session.add(vac)
    await session.commit()
    await session.refresh(vac)
    return vac


@router.delete("/vaccinations/{vac_id}", status_code=204)
async def delete_vaccination(vac_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Vaccination).where(Vaccination.id == vac_id))
    vac = result.scalar_one_or_none()
    if not vac:
        raise HTTPException(status_code=404, detail="Vaccination not found")
    await _check_pet_ownership(session, user_id, vac.pet_id)
    await session.delete(vac)
    await session.commit()


# ══════════════ VET VISITS ══════════════


@router.get("/vet_visits/{pet_id}", response_model=list[VetVisitRead])
async def list_vet_visits(pet_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    await _check_pet_ownership(session, user_id, pet_id)
    result = await session.execute(
        select(VetVisit).where(VetVisit.pet_id == pet_id).order_by(VetVisit.visit_date.desc())
    )
    return result.scalars().all()


@router.post("/vet_visits", response_model=VetVisitRead, status_code=201)
async def create_vet_visit(
    user_id: int,
    body: VetVisitCreate,
    session: AsyncSession = Depends(get_session),
):
    await _check_pet_ownership(session, user_id, body.pet_id)
    visit = VetVisit(
        pet_id=body.pet_id,
        visit_date=body.visit_date,
        diagnosis=body.diagnosis,
        treatment=body.treatment,
        notes=body.notes,
    )
    session.add(visit)
    await session.commit()
    await session.refresh(visit)
    return visit


@router.delete("/vet_visits/{visit_id}", status_code=204)
async def delete_vet_visit(visit_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(VetVisit).where(VetVisit.id == visit_id))
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail="Vet visit not found")
    await _check_pet_ownership(session, user_id, visit.pet_id)
    await session.delete(visit)
    await session.commit()


# ══════════════ WEIGHT RECORDS ══════════════


@router.get("/weight/{pet_id}", response_model=list[WeightRecordRead])
async def list_weight_records(pet_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    await _check_pet_ownership(session, user_id, pet_id)
    result = await session.execute(
        select(WeightRecord).where(WeightRecord.pet_id == pet_id).order_by(WeightRecord.recorded_at.desc())
    )
    return result.scalars().all()


@router.post("/weight", response_model=WeightRecordRead, status_code=201)
async def create_weight_record(
    user_id: int,
    body: WeightRecordCreate,
    session: AsyncSession = Depends(get_session),
):
    await _check_pet_ownership(session, user_id, body.pet_id)
    record = WeightRecord(pet_id=body.pet_id, weight=body.weight)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


# ══════════════ DOCUMENTS ══════════════


@router.get("/documents/{pet_id}")
async def list_documents(pet_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    await _check_pet_ownership(session, user_id, pet_id)
    result = await session.execute(
        select(Document).where(Document.pet_id == pet_id).order_by(Document.uploaded_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "pet_id": d.pet_id,
            "doc_type": d.doc_type,
            "file_id": d.file_id,
            "description": d.description,
            "uploaded_at": d.uploaded_at.isoformat(),
        }
        for d in docs
    ]


@router.post("/documents", status_code=201)
async def create_document(
    user_id: int,
    pet_id: int,
    doc_type: str,
    file_id: str,
    description: str = "",
    session: AsyncSession = Depends(get_session),
):
    await _check_pet_ownership(session, user_id, pet_id)
    doc = Document(
        pet_id=pet_id,
        doc_type=doc_type,
        file_id=file_id,
        description=description,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return {
        "id": doc.id,
        "pet_id": doc.pet_id,
        "doc_type": doc.doc_type,
        "file_id": doc.file_id,
        "description": doc.description,
        "uploaded_at": doc.uploaded_at.isoformat(),
    }


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(doc_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await _check_pet_ownership(session, user_id, doc.pet_id)
    await session.delete(doc)
    await session.commit()


# ══════════════ CALENDAR ══════════════


@router.get("/calendar/{user_id}")
async def calendar_events(user_id: int, session: AsyncSession = Depends(get_session)):
    """All upcoming events (reminders, vaccinations, vet visits) for a user."""
    from zoo_shared.db.models import Reminder

    pets_result = await session.execute(select(Pet).where(Pet.user_id == user_id))
    pets = pets_result.scalars().all()
    pet_ids = [p.id for p in pets]
    pet_map = {p.id: p.name for p in pets}

    if not pet_ids:
        return {"pets": [], "reminders": [], "vaccinations": [], "vet_visits": []}

    reminders_result = await session.execute(
        select(Reminder)
        .where(
            Reminder.user_id == user_id,
            Reminder.is_active == True,  # noqa: E712
        )
        .order_by(Reminder.remind_at)
    )
    reminders = reminders_result.scalars().all()

    vac_result = await session.execute(
        select(Vaccination).where(Vaccination.pet_id.in_(pet_ids)).order_by(Vaccination.date_done.desc())
    )
    vaccinations = vac_result.scalars().all()

    visit_result = await session.execute(
        select(VetVisit).where(VetVisit.pet_id.in_(pet_ids)).order_by(VetVisit.visit_date.desc())
    )
    visits = visit_result.scalars().all()

    return {
        "pets": [{"id": p.id, "name": p.name} for p in pets],
        "reminders": [
            {
                "id": r.id,
                "pet_id": r.pet_id,
                "pet_name": pet_map.get(r.pet_id, ""),
                "title": r.title,
                "category_emoji": r.category_emoji,
                "remind_at": r.remind_at.isoformat(),
                "repeat_text": r.repeat_text,
            }
            for r in reminders
        ],
        "vaccinations": [
            {
                "id": v.id,
                "pet_id": v.pet_id,
                "pet_name": pet_map.get(v.pet_id, ""),
                "name": v.name,
                "date_done": v.date_done.isoformat(),
                "next_date": v.next_date.isoformat() if v.next_date else None,
            }
            for v in vaccinations
        ],
        "vet_visits": [
            {
                "id": vv.id,
                "pet_id": vv.pet_id,
                "pet_name": pet_map.get(vv.pet_id, ""),
                "visit_date": vv.visit_date.isoformat(),
                "diagnosis": vv.diagnosis,
            }
            for vv in visits
        ],
    }
