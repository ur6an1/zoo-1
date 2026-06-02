"""Tests for backend.services.access — ownership checks with DB."""

import pytest
from backend.services.access import get_owned_allergy, get_owned_pet, get_owned_reminder
from zoo_shared.db.models import Allergy, Pet, Reminder


@pytest.mark.asyncio
async def test_get_owned_pet_found(db_session):
    pet = Pet(user_id=42, name="Rex", species="собака")
    db_session.add(pet)
    await db_session.flush()
    result = await get_owned_pet(db_session, 42, pet.id)
    assert result is not None
    assert result.name == "Rex"


@pytest.mark.asyncio
async def test_get_owned_pet_wrong_user(db_session):
    pet = Pet(user_id=42, name="Rex", species="собака")
    db_session.add(pet)
    await db_session.flush()
    result = await get_owned_pet(db_session, 999, pet.id)
    assert result is None


@pytest.mark.asyncio
async def test_get_owned_pet_not_exists(db_session):
    result = await get_owned_pet(db_session, 42, 99999)
    assert result is None


@pytest.mark.asyncio
async def test_get_owned_reminder_found(db_session):
    from datetime import datetime

    pet = Pet(user_id=42, name="Rex", species="собака")
    db_session.add(pet)
    await db_session.flush()
    reminder = Reminder(
        pet_id=pet.id,
        user_id=42,
        category="feeding",
        title="Feed",
        remind_at=datetime.now(),
        repeat="once",
    )
    db_session.add(reminder)
    await db_session.flush()
    result = await get_owned_reminder(db_session, 42, reminder.id)
    assert result is not None
    assert result.title == "Feed"


@pytest.mark.asyncio
async def test_get_owned_reminder_wrong_user(db_session):
    from datetime import datetime

    pet = Pet(user_id=42, name="Rex", species="собака")
    db_session.add(pet)
    await db_session.flush()
    reminder = Reminder(
        pet_id=pet.id,
        user_id=42,
        category="feeding",
        title="Feed",
        remind_at=datetime.now(),
        repeat="once",
    )
    db_session.add(reminder)
    await db_session.flush()
    result = await get_owned_reminder(db_session, 999, reminder.id)
    assert result is None


@pytest.mark.asyncio
async def test_get_owned_allergy_found(db_session):
    pet = Pet(user_id=42, name="Rex", species="собака")
    db_session.add(pet)
    await db_session.flush()
    allergy = Allergy(pet_id=pet.id, allergen="Курица", reaction="Зуд")
    db_session.add(allergy)
    await db_session.flush()
    result = await get_owned_allergy(db_session, 42, allergy.id)
    assert result is not None
    assert result.allergen == "Курица"


@pytest.mark.asyncio
async def test_get_owned_allergy_wrong_user(db_session):
    pet = Pet(user_id=42, name="Rex", species="собака")
    db_session.add(pet)
    await db_session.flush()
    allergy = Allergy(pet_id=pet.id, allergen="Курица")
    db_session.add(allergy)
    await db_session.flush()
    result = await get_owned_allergy(db_session, 999, allergy.id)
    assert result is None
