"""Tests for zoo_shared.schemas — Pydantic model validation."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")

from datetime import date, datetime

from zoo_shared.schemas.analytics import AnalyticsEventCreate
from zoo_shared.schemas.food import (
    AllergyCreate,
    AllergyRead,
    FoodEntryCreate,
    FoodEntryRead,
    WaterEntryCreate,
    WaterEntryRead,
)
from zoo_shared.schemas.medical import (
    VaccinationCreate,
    VaccinationRead,
    VetVisitCreate,
    VetVisitRead,
    WeightRecordCreate,
    WeightRecordRead,
)
from zoo_shared.schemas.payment import PaymentCreate, PaymentStatus
from zoo_shared.schemas.pet import PetCreate, PetRead, PetUpdate
from zoo_shared.schemas.reminder import ReminderCreate, ReminderRead
from zoo_shared.schemas.subscription import SubscriptionGrant, SubscriptionStatus


class TestPetSchemas:
    def test_pet_create_minimal(self):
        p = PetCreate(user_id=1, name="Rex", species="собака")
        assert p.breed == ""
        assert p.birth_date is None
        assert p.weight is None

    def test_pet_create_full(self):
        p = PetCreate(
            user_id=1, name="Rex", species="собака",
            breed="Лабрадор", birth_date=date(2020, 1, 1), weight=30.0,
        )
        assert p.breed == "Лабрадор"
        assert p.weight == 30.0

    def test_pet_update_partial(self):
        p = PetUpdate(name="Rex2")
        assert p.name == "Rex2"
        assert p.breed is None

    def test_pet_read(self):
        p = PetRead(
            id=1, user_id=1, name="Rex", species="собака",
            breed="", birth_date=None, weight=None, target_weight=None,
            photo_file_id=None, created_at=datetime.now(),
        )
        assert p.species_emoji == "🐾"


class TestReminderSchemas:
    def test_reminder_create(self):
        r = ReminderCreate(
            user_id=1, pet_id=1, title="Feed",
            remind_at=datetime(2024, 6, 1, 8, 0),
        )
        assert r.category == "custom"
        assert r.repeat == "once"

    def test_reminder_read(self):
        r = ReminderRead(
            id=1, user_id=1, pet_id=1, title="Feed", description="",
            category="feeding", remind_at=datetime.now(), repeat="daily",
            is_active=True, created_at=datetime.now(),
        )
        assert r.is_active is True


class TestMedicalSchemas:
    def test_vaccination_create(self):
        v = VaccinationCreate(pet_id=1, name="Бешенство", date_done=date(2024, 1, 1))
        assert v.notes == ""

    def test_vaccination_read(self):
        v = VaccinationRead(
            id=1, pet_id=1, name="Бешенство",
            date_done=date(2024, 1, 1), next_date=date(2025, 1, 1),
            notes="", created_at=datetime.now(),
        )
        assert v.next_date == date(2025, 1, 1)

    def test_vet_visit_create(self):
        v = VetVisitCreate(pet_id=1, visit_date=date(2024, 6, 1))
        assert v.diagnosis == ""

    def test_vet_visit_read(self):
        v = VetVisitRead(
            id=1, pet_id=1, visit_date=date(2024, 6, 1),
            diagnosis="Здоров", treatment="", notes="",
            created_at=datetime.now(),
        )
        assert v.diagnosis == "Здоров"

    def test_weight_record_create(self):
        w = WeightRecordCreate(pet_id=1, weight=5.5)
        assert w.weight == 5.5

    def test_weight_record_read(self):
        w = WeightRecordRead(id=1, pet_id=1, weight=5.5, recorded_at=datetime.now())
        assert w.weight == 5.5


class TestFoodSchemas:
    def test_food_entry_create(self):
        f = FoodEntryCreate(pet_id=1, food_name="Корм")
        assert f.portion == ""
        assert f.portion_grams is None

    def test_food_entry_read(self):
        f = FoodEntryRead(
            id=1, pet_id=1, food_name="Корм",
            portion="100г", portion_grams=100.0,
            meal_time=datetime.now(), notes="",
        )
        assert f.food_name == "Корм"

    def test_water_entry_create(self):
        w = WaterEntryCreate(pet_id=1, amount_ml=200)
        assert w.amount_ml == 200

    def test_water_entry_read(self):
        w = WaterEntryRead(id=1, pet_id=1, amount_ml=200, recorded_at=datetime.now())
        assert w.amount_ml == 200

    def test_allergy_create(self):
        a = AllergyCreate(pet_id=1, allergen="Курица")
        assert a.reaction == ""

    def test_allergy_read(self):
        a = AllergyRead(id=1, pet_id=1, allergen="Курица", reaction="Зуд", notes="")
        assert a.allergen == "Курица"


class TestPaymentSchemas:
    def test_payment_create(self):
        p = PaymentCreate(user_id=1, plan_key="pro")
        assert p.provider == "yookassa"

    def test_payment_status(self):
        p = PaymentStatus(payment_id="abc", status="succeeded", provider="yookassa")
        assert p.status == "succeeded"


class TestSubscriptionSchemas:
    def test_subscription_status(self):
        s = SubscriptionStatus(
            user_id=1, plan_tier="pro", is_premium=True,
            premium_until=datetime.now(), ai_requests_today=5, weather_notify=True,
        )
        assert s.is_premium is True

    def test_subscription_grant(self):
        g = SubscriptionGrant(user_id=1, days=30)
        assert g.plan_tier == "pro"


class TestAnalyticsSchemas:
    def test_analytics_event_create(self):
        e = AnalyticsEventCreate(user_id=1, event_name="start")
        assert e.source == ""
        assert e.payload is None

    def test_analytics_event_with_payload(self):
        e = AnalyticsEventCreate(user_id=1, event_name="test", payload={"key": "value"})
        assert e.payload == {"key": "value"}
