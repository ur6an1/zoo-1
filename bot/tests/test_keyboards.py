"""Tests for bot/bot/keyboards/keyboards.py."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from bot.keyboards.keyboards import (
    _get,
    ai_hub_kb,
    allergy_action_kb,
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


class TestGetHelper:
    def test_dict_access(self):
        assert _get({"name": "Rex"}, "name") == "Rex"

    def test_dict_missing(self):
        assert _get({}, "name", "default") == "default"

    def test_obj_access(self):
        class Obj:
            name = "Rex"
        assert _get(Obj(), "name") == "Rex"

    def test_obj_missing(self):
        class Obj:
            pass
        assert _get(Obj(), "name", "default") == "default"


class TestStaticKeyboards:
    def test_main_menu_is_reply(self):
        assert isinstance(main_menu_kb, ReplyKeyboardMarkup)
        assert len(main_menu_kb.keyboard) == 2

    def test_quick_start_kb(self):
        assert isinstance(quick_start_kb, InlineKeyboardMarkup)
        assert any("pet:add" in b.callback_data for row in quick_start_kb.inline_keyboard for b in row)

    def test_pets_hub_kb(self):
        assert isinstance(pets_hub_kb, InlineKeyboardMarkup)
        assert any("pet:list" in b.callback_data for row in pets_hub_kb.inline_keyboard for b in row)

    def test_health_hub_kb(self):
        assert isinstance(health_hub_kb, InlineKeyboardMarkup)

    def test_ai_hub_kb(self):
        assert isinstance(ai_hub_kb, InlineKeyboardMarkup)

    def test_settings_hub_kb(self):
        assert isinstance(settings_hub_kb, InlineKeyboardMarkup)

    def test_species_kb(self):
        assert isinstance(species_kb, InlineKeyboardMarkup)
        texts = [b.text for row in species_kb.inline_keyboard for b in row]
        assert any("Кошка" in t for t in texts)
        assert any("Собака" in t for t in texts)

    def test_reminders_menu_kb(self):
        assert isinstance(reminders_menu_kb, InlineKeyboardMarkup)

    def test_reminder_category_kb(self):
        assert isinstance(reminder_category_kb, InlineKeyboardMarkup)

    def test_reminder_repeat_kb(self):
        assert isinstance(reminder_repeat_kb, InlineKeyboardMarkup)

    def test_medical_menu_kb(self):
        assert isinstance(medical_menu_kb, InlineKeyboardMarkup)

    def test_food_menu_kb(self):
        assert isinstance(food_menu_kb, InlineKeyboardMarkup)

    def test_food_analytics_kb(self):
        assert isinstance(food_analytics_kb, InlineKeyboardMarkup)

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

    def test_location_kb(self):
        assert isinstance(location_kb, ReplyKeyboardMarkup)

    def test_clinic_radius_kb(self):
        assert isinstance(clinic_radius_kb, InlineKeyboardMarkup)


class TestDynamicKeyboards:
    def test_pets_list_kb_empty(self):
        kb = pets_list_kb([], action="view")
        assert isinstance(kb, InlineKeyboardMarkup)
        texts = [b.text for row in kb.inline_keyboard for b in row]
        assert any("Добавить" in t for t in texts)

    def test_pets_list_kb_with_pets(self):
        pets = [
            {"id": 1, "name": "Rex", "species_emoji": "🐶"},
            {"id": 2, "name": "Whiskers", "species_emoji": "🐱"},
        ]
        kb = pets_list_kb(pets, action="view")
        texts = [b.text for row in kb.inline_keyboard for b in row]
        assert any("Rex" in t for t in texts)
        assert any("Whiskers" in t for t in texts)

    def test_pets_list_kb_select_action(self):
        pets = [{"id": 1, "name": "Rex", "species_emoji": "🐶"}]
        kb = pets_list_kb(pets, action="select")
        cb_data = [b.callback_data for row in kb.inline_keyboard for b in row]
        assert any("pet:select:1" in d for d in cb_data)
        assert not any("Добавить" in b.text for row in kb.inline_keyboard for b in row)

    def test_pet_profile_kb(self):
        kb = pet_profile_kb(42)
        assert isinstance(kb, InlineKeyboardMarkup)
        cb_data = [b.callback_data for row in kb.inline_keyboard for b in row]
        assert any("pet:stats:42" in d for d in cb_data)
        assert any("pet:edit:42" in d for d in cb_data)
        assert any("pet:confirm_delete:42" in d for d in cb_data)

    def test_post_pet_created_kb(self):
        kb = post_pet_created_kb(10)
        assert isinstance(kb, InlineKeyboardMarkup)
        cb_data = [b.callback_data for row in kb.inline_keyboard for b in row]
        assert any("pet:weight_goal:10" in d for d in cb_data)

    def test_pet_edit_kb(self):
        kb = pet_edit_kb(5)
        cb_data = [b.callback_data for row in kb.inline_keyboard for b in row]
        assert any("pet:edit_field:name:5" in d for d in cb_data)
        assert any("pet:edit_field:breed:5" in d for d in cb_data)

    def test_confirm_delete_kb(self):
        kb = confirm_delete_kb(7)
        cb_data = [b.callback_data for row in kb.inline_keyboard for b in row]
        assert any("pet:delete:7" in d for d in cb_data)

    def test_reminders_list_kb_empty(self):
        kb = reminders_list_kb([])
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_reminders_list_kb_with_items(self):
        reminders = [
            {"id": 1, "title": "Feed", "category_emoji": "🍽", "is_active": True},
            {"id": 2, "title": "Vet", "category_emoji": "🏥", "is_active": False},
        ]
        kb = reminders_list_kb(reminders)
        texts = [b.text for row in kb.inline_keyboard for b in row]
        assert any("Feed" in t for t in texts)
        assert any("⏸" in t for t in texts)

    def test_reminder_detail_kb_active(self):
        kb = reminder_detail_kb(3, is_active=True)
        texts = [b.text for row in kb.inline_keyboard for b in row]
        assert any("Приостановить" in t for t in texts)

    def test_reminder_detail_kb_paused(self):
        kb = reminder_detail_kb(3, is_active=False)
        texts = [b.text for row in kb.inline_keyboard for b in row]
        assert any("Возобновить" in t for t in texts)

    def test_med_section_kb_weight(self):
        kb = med_section_kb("weight")
        texts = [b.text for row in kb.inline_keyboard for b in row]
        assert any("График" in t for t in texts)

    def test_med_section_kb_vaccines(self):
        kb = med_section_kb("vaccines")
        texts = [b.text for row in kb.inline_keyboard for b in row]
        assert not any("График" in t for t in texts)

    def test_food_clear_confirm_kb(self):
        kb = food_clear_confirm_kb("meal")
        cb_data = [b.callback_data for row in kb.inline_keyboard for b in row]
        assert any("food:meal:clear" in d for d in cb_data)
