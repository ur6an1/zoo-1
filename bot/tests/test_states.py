"""Tests for bot.states.states — FSM state groups and their states."""

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


class TestStateGroupsExist:
    """All FSM state groups must be valid StatesGroup subclasses."""

    def test_pet_form(self):
        assert issubclass(PetForm, StatesGroup)
        assert isinstance(PetForm.name, State)
        assert isinstance(PetForm.species, State)
        assert isinstance(PetForm.breed, State)
        assert isinstance(PetForm.birth_date, State)
        assert isinstance(PetForm.weight, State)
        assert isinstance(PetForm.photo, State)

    def test_edit_pet_form(self):
        assert issubclass(EditPetForm, StatesGroup)
        assert isinstance(EditPetForm.choosing_field, State)
        assert isinstance(EditPetForm.editing_name, State)
        assert isinstance(EditPetForm.editing_weight, State)

    def test_reminder_form(self):
        assert issubclass(ReminderForm, StatesGroup)
        assert isinstance(ReminderForm.choosing_pet, State)
        assert isinstance(ReminderForm.category, State)
        assert isinstance(ReminderForm.title, State)
        assert isinstance(ReminderForm.date, State)
        assert isinstance(ReminderForm.time, State)
        assert isinstance(ReminderForm.repeat, State)

    def test_vaccination_form(self):
        assert issubclass(VaccinationForm, StatesGroup)
        assert isinstance(VaccinationForm.choosing_pet, State)
        assert isinstance(VaccinationForm.name, State)
        assert isinstance(VaccinationForm.date_done, State)
        assert isinstance(VaccinationForm.next_date, State)

    def test_vet_visit_form(self):
        assert issubclass(VetVisitForm, StatesGroup)
        assert isinstance(VetVisitForm.visit_date, State)
        assert isinstance(VetVisitForm.diagnosis, State)

    def test_weight_form(self):
        assert issubclass(WeightForm, StatesGroup)
        assert isinstance(WeightForm.choosing_pet, State)
        assert isinstance(WeightForm.weight, State)

    def test_food_form(self):
        assert issubclass(FoodForm, StatesGroup)
        assert isinstance(FoodForm.choosing_pet, State)
        assert isinstance(FoodForm.food_name, State)
        assert isinstance(FoodForm.portion, State)

    def test_water_form(self):
        assert issubclass(WaterForm, StatesGroup)
        assert isinstance(WaterForm.choosing_pet, State)
        assert isinstance(WaterForm.amount, State)

    def test_allergy_form(self):
        assert issubclass(AllergyForm, StatesGroup)
        assert isinstance(AllergyForm.allergen, State)

    def test_document_form(self):
        assert issubclass(DocumentForm, StatesGroup)
        assert isinstance(DocumentForm.doc_type, State)
        assert isinstance(DocumentForm.photo, State)

    def test_nutrition_form(self):
        assert issubclass(NutritionForm, StatesGroup)
        assert isinstance(NutritionForm.waiting_photo, State)

    def test_symptoms_form(self):
        assert issubclass(SymptomsForm, StatesGroup)
        assert isinstance(SymptomsForm.waiting_text, State)

    def test_compare_form(self):
        assert issubclass(CompareForm, StatesGroup)
        assert isinstance(CompareForm.waiting_photo_1, State)
        assert isinstance(CompareForm.waiting_photo_2, State)

    def test_weight_goal_form(self):
        assert issubclass(WeightGoalForm, StatesGroup)
        assert isinstance(WeightGoalForm.target, State)

    def test_voice_note_form(self):
        assert issubclass(VoiceNoteForm, StatesGroup)
        assert isinstance(VoiceNoteForm.waiting_voice, State)

    def test_weather_city_form(self):
        assert issubclass(WeatherCityForm, StatesGroup)
        assert isinstance(WeatherCityForm.waiting_city, State)

    def test_medical_test_form(self):
        assert issubclass(MedicalTestForm, StatesGroup)
        assert isinstance(MedicalTestForm.choosing_pet, State)
        assert isinstance(MedicalTestForm.waiting_photo, State)

    def test_clinic_search_form(self):
        assert issubclass(ClinicSearchForm, StatesGroup)
        assert isinstance(ClinicSearchForm.waiting_location, State)
        assert isinstance(ClinicSearchForm.waiting_filters, State)


class TestStateNames:
    """State names must follow the convention GroupName:state_name."""

    def test_pet_form_state_names(self):
        assert PetForm.name.state == "PetForm:name"
        assert PetForm.species.state == "PetForm:species"

    def test_reminder_form_state_names(self):
        assert ReminderForm.choosing_pet.state == "ReminderForm:choosing_pet"
        assert ReminderForm.repeat.state == "ReminderForm:repeat"

    def test_compare_form_state_names(self):
        assert CompareForm.waiting_photo_1.state == "CompareForm:waiting_photo_1"
        assert CompareForm.waiting_photo_2.state == "CompareForm:waiting_photo_2"
