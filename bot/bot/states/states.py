"""FSM-состояния для диалогов бота."""

from aiogram.fsm.state import State, StatesGroup


class PetForm(StatesGroup):
    name = State()
    species = State()
    breed = State()
    birth_date = State()
    weight = State()
    photo = State()


class EditPetForm(StatesGroup):
    choosing_field = State()
    editing_name = State()
    editing_breed = State()
    editing_birth_date = State()
    editing_weight = State()
    editing_photo = State()


class ReminderForm(StatesGroup):
    choosing_pet = State()
    category = State()
    title = State()
    description = State()
    date = State()
    time = State()
    repeat = State()


class VaccinationForm(StatesGroup):
    choosing_pet = State()
    name = State()
    date_done = State()
    next_date = State()
    notes = State()


class VetVisitForm(StatesGroup):
    choosing_pet = State()
    visit_date = State()
    diagnosis = State()
    treatment = State()
    notes = State()


class WeightForm(StatesGroup):
    choosing_pet = State()
    weight = State()


class FoodForm(StatesGroup):
    choosing_pet = State()
    food_name = State()
    portion = State()
    notes = State()


class WaterForm(StatesGroup):
    choosing_pet = State()
    amount = State()


class AllergyForm(StatesGroup):
    choosing_pet = State()
    allergen = State()
    reaction = State()
    notes = State()


class DocumentForm(StatesGroup):
    choosing_pet = State()
    doc_type = State()
    photo = State()
    description = State()


class NutritionForm(StatesGroup):
    choosing_pet = State()
    waiting_photo = State()


class SymptomsForm(StatesGroup):
    choosing_pet = State()
    waiting_text = State()


# ── Новые состояния ──

class CompareForm(StatesGroup):
    """Сравнение двух кормов."""
    waiting_photo_1 = State()
    waiting_photo_2 = State()


class WeightGoalForm(StatesGroup):
    """Установка целевого веса."""
    choosing_pet = State()
    target = State()


class VoiceNoteForm(StatesGroup):
    """Голосовая заметка."""
    choosing_pet = State()
    waiting_voice = State()


class WeatherCityForm(StatesGroup):
    """Настройка города для погоды."""
    waiting_city = State()


class MedicalTestForm(StatesGroup):
    """AI-анализ медицинских анализов."""
    choosing_pet = State()
    waiting_photo = State()


class ClinicSearchForm(StatesGroup):
    """Поиск ветклиник."""
    waiting_location = State()
    waiting_filters = State()
