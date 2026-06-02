"""Reminders REST API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from zoo_shared.db.models import Pet, Reminder
from zoo_shared.schemas.reminder import ReminderCreate, ReminderRead

from backend.deps import get_session

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("/by_user/{user_id}", response_model=list[ReminderRead])
async def list_reminders(user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Reminder).where(Reminder.user_id == user_id).order_by(Reminder.is_active.desc(), Reminder.remind_at)
    )
    return result.scalars().all()


@router.get("/{reminder_id}")
async def get_reminder(reminder_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id))
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    pet = await session.get(Pet, reminder.pet_id)
    return {
        "id": reminder.id,
        "user_id": reminder.user_id,
        "pet_id": reminder.pet_id,
        "title": reminder.title,
        "description": reminder.description,
        "category": reminder.category,
        "remind_at": reminder.remind_at.isoformat(),
        "repeat": reminder.repeat,
        "is_active": reminder.is_active,
        "created_at": reminder.created_at.isoformat(),
        "category_emoji": reminder.category_emoji,
        "repeat_text": reminder.repeat_text,
        "pet_name": pet.name if pet else "",
    }


@router.post("/", response_model=ReminderRead, status_code=201)
async def create_reminder(body: ReminderCreate, session: AsyncSession = Depends(get_session)):
    reminder = Reminder(
        user_id=body.user_id,
        pet_id=body.pet_id,
        title=body.title,
        description=body.description,
        category=body.category,
        remind_at=body.remind_at,
        repeat=body.repeat,
        is_active=True,
    )
    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)
    return reminder


@router.patch("/{reminder_id}/pause")
async def pause_reminder(reminder_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id))
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    reminder.is_active = False
    await session.commit()
    return {"id": reminder.id, "is_active": False, "title": reminder.title}


@router.patch("/{reminder_id}/resume")
async def resume_reminder(reminder_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id))
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    reminder.is_active = True
    await session.commit()
    return {"id": reminder.id, "is_active": True, "title": reminder.title}


@router.delete("/{reminder_id}", status_code=204)
async def delete_reminder(reminder_id: int, user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id))
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    await session.delete(reminder)
    await session.commit()
