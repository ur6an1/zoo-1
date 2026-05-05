"""Проверки владения сущностями для callback-сценариев."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from zoo_shared.db.models import Allergy, Pet, Reminder


async def get_owned_pet(session: AsyncSession, user_id: int, pet_id: int) -> Pet | None:
    result = await session.execute(
        select(Pet).where(Pet.id == pet_id, Pet.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_owned_reminder(
    session: AsyncSession,
    user_id: int,
    reminder_id: int,
) -> Reminder | None:
    result = await session.execute(
        select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_owned_allergy(
    session: AsyncSession,
    user_id: int,
    allergy_id: int,
) -> Allergy | None:
    result = await session.execute(
        select(Allergy)
        .join(Pet, Pet.id == Allergy.pet_id)
        .where(Allergy.id == allergy_id, Pet.user_id == user_id)
    )
    return result.scalar_one_or_none()
