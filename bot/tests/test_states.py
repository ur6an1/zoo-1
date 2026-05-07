"""Tests for bot/bot/states/states.py — verify FSM state groups are correctly defined."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup
from bot.states.states import (
    AllergyForm,
    ClinicSearchForm,
    CompareForm,
    DocumentForm,
    EditPetForm,
    FoodForm,
    MedicalTestForm,
    NutritionForm,
    PetForm,
    ReminderForm,
    SymptomsForm,
    VaccinationForm,
    VetVisitForm,
    VoiceNoteForm,
    WaterForm,
    WeatherCityForm,
    WeightForm,
    WeightGoalForm,
)


def _assert_states_group(cls: type, expected_states: list[str]):
    assert issubclass(cls, StatesGroup)
    actual = [s for s in dir(cls) if not s.startswith("_") and isinstance(getattr(cls, s), State)]
    for name in expected_states:
        assert name in actual, f"State {name!r} missing from {cls.__name__}"


class TestPetForm:
    def test_is_states_group(self):
        _assert_states_group(PetForm, ["name", "species", "breed", "birth_date", "weight", "photo"])

    def test_state_count(self):
        states = [s for s in dir(PetForm) if not s.startswith("_") and isinstance(getattr(PetForm, s), State)]
        assert len(states) == 6


class TestEditPetForm:
    def test_states(self):
        _assert_states_group(EditPetForm, [
            "choosing_field", "editing_name", "editing_breed",
            "editing_birth_date", "editing_weight", "editing_photo",
        ])


class TestReminderForm:
    def test_states(self):
        _assert_states_group(ReminderForm, [
            "choosing_pet", "category", "title", "description", "date", "time", "repeat",
        ])


class TestVaccinationForm:
    def test_states(self):
        _assert_states_group(VaccinationForm, [
            "choosing_pet", "name", "date_done", "next_date", "notes",
        ])


class TestVetVisitForm:
    def test_states(self):
        _assert_states_group(VetVisitForm, [
            "choosing_pet", "visit_date", "diagnosis", "treatment", "notes",
        ])


class TestWeightForm:
    def test_states(self):
        _assert_states_group(WeightForm, ["choosing_pet", "weight"])


class TestFoodForm:
    def test_states(self):
        _assert_states_group(FoodForm, ["choosing_pet", "food_name", "portion", "notes"])


class TestWaterForm:
    def test_states(self):
        _assert_states_group(WaterForm, ["choosing_pet", "amount"])


class TestAllergyForm:
    def test_states(self):
        _assert_states_group(AllergyForm, ["choosing_pet", "allergen", "reaction", "notes"])


class TestDocumentForm:
    def test_states(self):
        _assert_states_group(DocumentForm, ["choosing_pet", "doc_type", "photo", "description"])


class TestNutritionForm:
    def test_states(self):
        _assert_states_group(NutritionForm, ["choosing_pet", "waiting_photo"])


class TestSymptomsForm:
    def test_states(self):
        _assert_states_group(SymptomsForm, ["choosing_pet", "waiting_text"])


class TestCompareForm:
    def test_states(self):
        _assert_states_group(CompareForm, ["waiting_photo_1", "waiting_photo_2"])


class TestWeightGoalForm:
    def test_states(self):
        _assert_states_group(WeightGoalForm, ["choosing_pet", "target"])


class TestVoiceNoteForm:
    def test_states(self):
        _assert_states_group(VoiceNoteForm, ["choosing_pet", "waiting_voice"])


class TestWeatherCityForm:
    def test_states(self):
        _assert_states_group(WeatherCityForm, ["waiting_city"])


class TestMedicalTestForm:
    def test_states(self):
        _assert_states_group(MedicalTestForm, ["choosing_pet", "waiting_photo"])


class TestClinicSearchForm:
    def test_states(self):
        _assert_states_group(ClinicSearchForm, ["waiting_location", "waiting_filters"])
