"""Tests for zoo_shared.db.models — Pet, Reminder, UserSettings methods."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "fake:token")
os.environ.setdefault("REDIS_URL", "")

from datetime import date, timedelta

from zoo_shared.db.models import Pet, Reminder, UserSettings


class TestPetAgeStr:
    def _make_pet(self, birth_date=None):
        return Pet(id=1, user_id=1, name="Rex", species="собака", birth_date=birth_date)

    def test_no_birth_date(self):
        pet = self._make_pet(None)
        assert pet.age_str() == "не указан"

    def test_years_singular(self):
        today = date.today()
        birth = today.replace(year=today.year - 1)
        pet = self._make_pet(birth)
        assert "1 год" in pet.age_str()

    def test_years_plural_2_4(self):
        today = date.today()
        birth = today.replace(year=today.year - 3)
        pet = self._make_pet(birth)
        assert "3 года" in pet.age_str()

    def test_years_plural_5_plus(self):
        today = date.today()
        birth = today.replace(year=today.year - 5)
        pet = self._make_pet(birth)
        assert "5 лет" in pet.age_str()

    def test_years_11(self):
        today = date.today()
        birth = today.replace(year=today.year - 11)
        pet = self._make_pet(birth)
        assert "11 лет" in pet.age_str()

    def test_months(self):
        today = date.today()
        if today.month > 3:
            birth = today.replace(month=today.month - 3)
        else:
            birth = today.replace(year=today.year - 1, month=today.month + 9)
        pet = self._make_pet(birth)
        result = pet.age_str()
        assert "мес." in result

    def test_days(self):
        today = date.today()
        birth = today - timedelta(days=5)
        pet = self._make_pet(birth)
        result = pet.age_str()
        # Within same month -> days; crossing month -> months
        assert "дн." in result or "мес." in result


class TestPetAgeMonths:
    def test_no_birth_date(self):
        pet = Pet(id=1, user_id=1, name="Rex", species="собака", birth_date=None)
        assert pet.age_months() is None

    def test_with_birth_date(self):
        today = date.today()
        birth = today.replace(year=today.year - 2)
        pet = Pet(id=1, user_id=1, name="Rex", species="собака", birth_date=birth)
        assert pet.age_months() == 24


class TestPetSpeciesEmoji:
    def test_cat(self):
        pet = Pet(id=1, user_id=1, name="Мурка", species="кошка")
        assert pet.species_emoji == "🐱"

    def test_dog(self):
        pet = Pet(id=1, user_id=1, name="Rex", species="собака")
        assert pet.species_emoji == "🐶"

    def test_bird(self):
        pet = Pet(id=1, user_id=1, name="Кеша", species="птица")
        assert pet.species_emoji == "🐦"

    def test_rodent(self):
        pet = Pet(id=1, user_id=1, name="Хомяк", species="грызун")
        assert pet.species_emoji == "🐹"

    def test_unknown(self):
        pet = Pet(id=1, user_id=1, name="Рыбка", species="рыба")
        assert pet.species_emoji == "🐾"


class TestReminderProperties:
    def _make_reminder(self, category="feeding", repeat="once"):
        return Reminder(
            id=1, pet_id=1, user_id=1,
            category=category, title="Test", remind_at=None,
            repeat=repeat,
        )

    def test_category_emoji_feeding(self):
        assert self._make_reminder("feeding").category_emoji == "🍽"

    def test_category_emoji_vaccine(self):
        assert self._make_reminder("vaccine").category_emoji == "💉"

    def test_category_emoji_vet(self):
        assert self._make_reminder("vet").category_emoji == "🏥"

    def test_category_emoji_grooming(self):
        assert self._make_reminder("grooming").category_emoji == "✂️"

    def test_category_emoji_custom(self):
        assert self._make_reminder("custom").category_emoji == "📌"

    def test_category_emoji_unknown(self):
        assert self._make_reminder("other").category_emoji == "⏰"

    def test_repeat_text_once(self):
        assert self._make_reminder(repeat="once").repeat_text == "разово"

    def test_repeat_text_daily(self):
        assert self._make_reminder(repeat="daily").repeat_text == "ежедневно"

    def test_repeat_text_weekly(self):
        assert self._make_reminder(repeat="weekly").repeat_text == "еженедельно"

    def test_repeat_text_monthly(self):
        assert self._make_reminder(repeat="monthly").repeat_text == "ежемесячно"

    def test_repeat_text_yearly(self):
        assert self._make_reminder(repeat="yearly").repeat_text == "ежегодно"

    def test_repeat_text_unknown(self):
        r = self._make_reminder(repeat="biweekly")
        assert r.repeat_text == "biweekly"


class TestUserSettingsDefaults:
    def test_defaults(self):
        s = UserSettings(id=1, user_id=123, plan_tier="free", is_premium=False)
        assert s.is_premium is False
        assert s.plan_tier == "free"
