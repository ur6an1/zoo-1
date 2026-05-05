"""Tests for backend.services.content — tips, FAQ, emergency texts."""

from backend.services.content import (
    EMERGENCY_GENERAL,
    EMERGENCY_INJURY,
    EMERGENCY_OVERHEAT,
    EMERGENCY_POISONING,
    FAQ_TEXT,
    NUTRITION_TEXT,
    TIPS,
)


class TestTips:
    def test_cat_tips(self):
        assert "кошка" in TIPS
        assert "корм" in TIPS["кошка"].lower()

    def test_dog_tips(self):
        assert "собака" in TIPS
        assert "выгуливайте" in TIPS["собака"].lower()

    def test_bird_tips(self):
        assert "птица" in TIPS
        assert "клетка" in TIPS["птица"].lower()

    def test_rodent_tips(self):
        assert "грызун" in TIPS

    def test_other_tips(self):
        assert "другое" in TIPS

    def test_all_tips_not_empty(self):
        for species, text in TIPS.items():
            assert len(text) > 50, f"Tip for {species} is too short"


class TestFAQ:
    def test_faq_not_empty(self):
        assert len(FAQ_TEXT) > 100

    def test_faq_contains_key_info(self):
        assert "ветеринар" in FAQ_TEXT.lower()


class TestNutrition:
    def test_nutrition_text(self):
        assert len(NUTRITION_TEXT) > 100
        assert "кошки" in NUTRITION_TEXT.lower()
        assert "собаки" in NUTRITION_TEXT.lower()


class TestEmergency:
    def test_poisoning(self):
        assert len(EMERGENCY_POISONING) > 100
        assert "отравлен" in EMERGENCY_POISONING.lower()

    def test_injury(self):
        assert len(EMERGENCY_INJURY) > 100
        assert "травм" in EMERGENCY_INJURY.lower()

    def test_overheat(self):
        assert len(EMERGENCY_OVERHEAT) > 100
        assert "перегрев" in EMERGENCY_OVERHEAT.lower()

    def test_general(self):
        assert len(EMERGENCY_GENERAL) > 100
        assert "аптечка" in EMERGENCY_GENERAL.lower()
