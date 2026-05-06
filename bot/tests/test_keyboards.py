"""Tests for bot.keyboards.keyboards — keyboard builders and static keyboards."""

from types import SimpleNamespace

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from bot.keyboards.keyboards import (
    _get,
    add_pet_cta_kb,
    ai_hub_kb,
    allergy_action_kb,
    allergy_list_kb,
    back_to_menu_kb,
    cancel_kb,
    clinic_radius_kb,
    confirm_delete_kb,
    doc_type_kb,
    emergency_kb,
    food_action_kb,
    food_analytics_kb,
    food_clear_confirm_kb,
    food_menu_kb,
    health_hub_kb,
    location_kb,
    main_menu_kb,
    med_section_kb,
    medical_menu_kb,
    pet_edit_kb,
    pet_profile_kb,
    pets_hub_kb,
    pets_list_kb,
    photo_menu_kb,
    post_pet_created_kb,
    quick_start_kb,
    reminder_category_kb,
    reminder_detail_kb,
    reminder_repeat_kb,
    reminders_list_kb,
    reminders_menu_kb,
    settings_hub_kb,
    settings_menu_kb,
    skip_kb,
    species_kb,
    tips_menu_kb,
    water_action_kb,
)


# ── Helpers ──


class TestGetHelper:
    def test_dict_access(self):
        assert _get({"name": "Рекс"}, "name") == "Рекс"

    def test_dict_default(self):
        assert _get({}, "name", "default") == "default"

    def test_object_access(self):
        obj = SimpleNamespace(name="Рекс")
        assert _get(obj, "name") == "Рекс"

    def test_object_default(self):
        obj = SimpleNamespace()
        assert _get(obj, "name", "default") == "default"


# ── Static keyboards existence & type ──


class TestStaticKeyboards:
    def test_main_menu_kb_is_reply(self):
        assert isinstance(main_menu_kb, ReplyKeyboardMarkup)
        assert main_menu_kb.resize_keyboard is True

    def test_quick_start_kb(self):
        assert isinstance(quick_start_kb, InlineKeyboardMarkup)
        buttons = [b.text for row in quick_start_kb.inline_keyboard for b in row]
        assert "➕ Добавить питомца" in buttons

    def test_add_pet_cta_kb(self):
        assert isinstance(add_pet_cta_kb, InlineKeyboardMarkup)

    def test_pets_hub_kb(self):
        assert isinstance(pets_hub_kb, InlineKeyboardMarkup)
        callbacks = [b.callback_data for row in pets_hub_kb.inline_keyboard for b in row]
        assert "pet:list" in callbacks

    def test_health_hub_kb(self):
        assert isinstance(health_hub_kb, InlineKeyboardMarkup)
        callbacks = [b.callback_data for row in health_hub_kb.inline_keyboard for b in row]
        assert "weather:show" in callbacks

    def test_ai_hub_kb(self):
        assert isinstance(ai_hub_kb, InlineKeyboardMarkup)
        callbacks = [b.callback_data for row in ai_hub_kb.inline_keyboard for b in row]
        assert "photo:menu" in callbacks

    def test_settings_hub_kb(self):
        assert isinstance(settings_hub_kb, InlineKeyboardMarkup)
        callbacks = [b.callback_data for row in settings_hub_kb.inline_keyboard for b in row]
        assert "settings:subscription" in callbacks

    def test_species_kb(self):
        assert isinstance(species_kb, InlineKeyboardMarkup)
        callbacks = [b.callback_data for row in species_kb.inline_keyboard for b in row]
        assert "species:кошка" in callbacks
        assert "species:собака" in callbacks

    def test_reminders_menu_kb(self):
        assert isinstance(reminders_menu_kb, InlineKeyboardMarkup)

    def test_reminder_category_kb(self):
        assert isinstance(reminder_category_kb, InlineKeyboardMarkup)
        callbacks = [b.callback_data for row in reminder_category_kb.inline_keyboard for b in row]
        assert "rem_cat:feeding" in callbacks

    def test_reminder_repeat_kb(self):
        assert isinstance(reminder_repeat_kb, InlineKeyboardMarkup)
        callbacks = [b.callback_data for row in reminder_repeat_kb.inline_keyboard for b in row]
        assert "repeat:daily" in callbacks

    def test_medical_menu_kb(self):
        assert isinstance(medical_menu_kb, InlineKeyboardMarkup)

    def test_food_menu_kb(self):
        assert isinstance(food_menu_kb, InlineKeyboardMarkup)

    def test_food_analytics_kb(self):
        assert isinstance(food_analytics_kb, InlineKeyboardMarkup)
        callbacks = [b.callback_data for row in food_analytics_kb.inline_keyboard for b in row]
        assert "food:norms" in callbacks

    def test_photo_menu_kb(self):
        assert isinstance(photo_menu_kb, InlineKeyboardMarkup)

    def test_food_action_kb(self):
        assert isinstance(food_action_kb, InlineKeyboardMarkup)

    def test_water_action_kb(self):
        assert isinstance(water_action_kb, InlineKeyboardMarkup)

    def test_allergy_action_kb(self):
        assert isinstance(allergy_action_kb, InlineKeyboardMarkup)

    def test_settings_menu_kb(self):
        assert isinstance(settings_menu_kb, InlineKeyboardMarkup)

    def test_emergency_kb(self):
        assert isinstance(emergency_kb, InlineKeyboardMarkup)
        callbacks = [b.callback_data for row in emergency_kb.inline_keyboard for b in row]
        assert "sos:clinic" in callbacks

    def test_location_kb(self):
        assert isinstance(location_kb, ReplyKeyboardMarkup)

    def test_tips_menu_kb(self):
        assert isinstance(tips_menu_kb, InlineKeyboardMarkup)

    def test_skip_kb(self):
        assert isinstance(skip_kb, InlineKeyboardMarkup)
        assert skip_kb.inline_keyboard[0][0].callback_data == "skip"

    def test_cancel_kb(self):
        assert isinstance(cancel_kb, InlineKeyboardMarkup)
        assert cancel_kb.inline_keyboard[0][0].callback_data == "cancel"

    def test_back_to_menu_kb(self):
        assert isinstance(back_to_menu_kb, InlineKeyboardMarkup)
        assert back_to_menu_kb.inline_keyboard[0][0].callback_data == "menu:main"

    def test_doc_type_kb(self):
        assert isinstance(doc_type_kb, InlineKeyboardMarkup)

    def test_clinic_radius_kb(self):
        assert isinstance(clinic_radius_kb, InlineKeyboardMarkup)


# ── Dynamic keyboard builders ──


class TestPetsListKb:
    def test_empty_list(self):
        kb = pets_list_kb([], action="view")
        buttons = [b for row in kb.inline_keyboard for b in row]
        texts = [b.text for b in buttons]
        assert "➕ Добавить питомца" in texts
        assert "◀️ Назад" in texts

    def test_with_pets_dicts(self):
        pets = [
            {"id": 1, "name": "Рекс", "species_emoji": "🐶"},
            {"id": 2, "name": "Мурка", "species_emoji": "🐱"},
        ]
        kb = pets_list_kb(pets, action="view")
        buttons = [b for row in kb.inline_keyboard for b in row]
        texts = [b.text for b in buttons]
        assert "🐶 Рекс" in texts
        assert "🐱 Мурка" in texts
        callbacks = [b.callback_data for b in buttons]
        assert "pet:view:1" in callbacks
        assert "pet:view:2" in callbacks

    def test_with_pets_objects(self):
        pets = [SimpleNamespace(id=5, name="Чарли", species_emoji="🐾")]
        kb = pets_list_kb(pets, action="select")
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "pet:select:5" in callbacks

    def test_no_add_button_for_non_view(self):
        kb = pets_list_kb([{"id": 1, "name": "X", "species_emoji": "🐾"}], action="select")
        buttons = [b for row in kb.inline_keyboard for b in row]
        texts = [b.text for b in buttons]
        assert "➕ Добавить питомца" not in texts


class TestPetProfileKb:
    def test_buttons_present(self):
        kb = pet_profile_kb(42)
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "pet:stats:42" in callbacks
        assert "pet:edit:42" in callbacks
        assert "pet:weight_goal:42" in callbacks
        assert "pet:export_pdf:42" in callbacks
        assert "pet:export:42" in callbacks
        assert "pet:confirm_delete:42" in callbacks
        assert "pet:list" in callbacks


class TestPostPetCreatedKb:
    def test_buttons_present(self):
        kb = post_pet_created_kb(7)
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "reminder:add" in callbacks
        assert "pet:weight_goal:7" in callbacks


class TestPetEditKb:
    def test_buttons_present(self):
        kb = pet_edit_kb(10)
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "pet:edit_field:name:10" in callbacks
        assert "pet:edit_field:breed:10" in callbacks
        assert "pet:edit_field:weight:10" in callbacks
        assert "pet:edit_field:photo:10" in callbacks
        assert "pet:view:10" in callbacks


class TestConfirmDeleteKb:
    def test_buttons_present(self):
        kb = confirm_delete_kb(3)
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "pet:delete:3" in callbacks
        assert "pet:view:3" in callbacks


class TestRemindersListKb:
    def test_empty(self):
        kb = reminders_list_kb([])
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "reminder:menu" in callbacks

    def test_with_reminders(self):
        rems = [
            {"id": 1, "title": "Кормление", "category_emoji": "🍽", "is_active": True},
            {"id": 2, "title": "Прививка", "category_emoji": "💉", "is_active": False},
        ]
        kb = reminders_list_kb(rems)
        buttons = [b for row in kb.inline_keyboard for b in row]
        texts = [b.text for b in buttons]
        assert any("Кормление" in t for t in texts)
        assert any("⏸" in t for t in texts)  # paused indicator


class TestReminderDetailKb:
    def test_active(self):
        kb = reminder_detail_kb(5, is_active=True)
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "reminder:pause:5" in callbacks
        assert "reminder:delete:5" in callbacks

    def test_inactive(self):
        kb = reminder_detail_kb(5, is_active=False)
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "reminder:resume:5" in callbacks
        assert "reminder:delete:5" in callbacks


class TestMedSectionKb:
    def test_vaccines_section(self):
        kb = med_section_kb("vaccines")
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "med:vaccines:add" in callbacks
        assert "med:vaccines:list" in callbacks
        assert "med:menu" in callbacks

    def test_weight_section_has_chart(self):
        kb = med_section_kb("weight")
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "med:weight:chart" in callbacks

    def test_vetvisits_section_no_chart(self):
        kb = med_section_kb("vetvisits")
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert all("chart" not in cb for cb in callbacks)


class TestAllergyListKb:
    def test_empty(self):
        kb = allergy_list_kb([])
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "food:allergies" in callbacks

    def test_with_allergies(self):
        allergies = [
            SimpleNamespace(id=1, allergen="Курица"),
            SimpleNamespace(id=2, allergen="Молоко"),
        ]
        kb = allergy_list_kb(allergies)
        buttons = [b for row in kb.inline_keyboard for b in row]
        texts = [b.text for b in buttons]
        callbacks = [b.callback_data for b in buttons]
        assert "🗑 Курица" in texts
        assert "food:allergy:del:1" in callbacks
        assert "food:allergy:del:2" in callbacks


class TestFoodClearConfirmKb:
    def test_meal(self):
        kb = food_clear_confirm_kb("meal")
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "food:meal:clear" in callbacks
        assert "food:meal" in callbacks

    def test_water(self):
        kb = food_clear_confirm_kb("water")
        buttons = [b for row in kb.inline_keyboard for b in row]
        callbacks = [b.callback_data for b in buttons]
        assert "food:water:clear" in callbacks
