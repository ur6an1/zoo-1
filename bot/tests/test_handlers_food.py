"""Tests for bot.handlers.food — food diary, water, allergies, analytics."""

from unittest.mock import AsyncMock, patch

from bot.handlers.food import (
    allergy_allergen,
    allergy_notes,
    allergy_reaction,
    cb_allergy_add,
    cb_allergy_delete,
    cb_allergy_list,
    cb_allergy_pet,
    cb_food_allergies,
    cb_food_analytics,
    cb_food_meal,
    cb_food_menu,
    cb_food_today,
    cb_food_water,
    cb_meal_add,
    cb_meal_clear,
    cb_meal_clear_confirm,
    cb_meal_list,
    cb_meal_pet,
    cb_water_add,
    cb_water_clear,
    cb_water_clear_confirm,
    cb_water_list,
    cb_water_pet,
    food_menu,
    meal_name,
    meal_notes,
    meal_portion,
    water_amount,
)
from bot.states.states import AllergyForm, FoodForm, WaterForm


class TestFoodMenu:
    async def test_message(self, mock_message):
        await food_menu(mock_message)
        text = mock_message.answer.call_args[0][0]
        assert "Дневник питания" in text

    async def test_callback(self, mock_callback):
        await cb_food_menu(mock_callback)
        mock_callback.message.edit_text.assert_awaited_once()


class TestFoodSubmenus:
    async def test_meal(self, mock_callback):
        await cb_food_meal(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Приёмы пищи" in text

    async def test_water(self, mock_callback):
        await cb_food_water(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "воды" in text.lower()

    async def test_allergies(self, mock_callback):
        await cb_food_allergies(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Аллергии" in text

    async def test_analytics(self, mock_callback):
        await cb_food_analytics(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Аналитика" in text


class TestMealAdd:
    @patch("bot.handlers.food.api_client")
    async def test_no_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_meal_add(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "добавьте питомца" in text.lower()

    @patch("bot.handlers.food.api_client")
    async def test_with_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        await cb_meal_add(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == FoodForm.choosing_pet.state


class TestMealPet:
    @patch("bot.handlers.food.api_client")
    async def test_valid(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_food:1"
        mock_api.get_pet = AsyncMock(return_value={"id": 1, "name": "Рекс"})
        await fsm_context.set_state(FoodForm.choosing_pet)
        await cb_meal_pet(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == FoodForm.food_name.state

    @patch("bot.handlers.food.api_client")
    async def test_not_found(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_food:999"
        mock_api.get_pet = AsyncMock(return_value=None)
        await fsm_context.set_state(FoodForm.choosing_pet)
        await cb_meal_pet(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()

    async def test_invalid_id(self, mock_callback, fsm_context):
        mock_callback.data = "pet:select_food:abc"
        await fsm_context.set_state(FoodForm.choosing_pet)
        await cb_meal_pet(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()


class TestMealName:
    async def test_valid(self, mock_message, fsm_context):
        mock_message.text = "Роял Канин"
        await fsm_context.set_state(FoodForm.food_name)
        await meal_name(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == FoodForm.portion.state

    async def test_empty(self, mock_message, fsm_context):
        mock_message.text = ""
        await fsm_context.set_state(FoodForm.food_name)
        await meal_name(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == FoodForm.food_name.state

    async def test_too_long(self, mock_message, fsm_context):
        mock_message.text = "X" * 201
        await fsm_context.set_state(FoodForm.food_name)
        await meal_name(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == FoodForm.food_name.state


class TestMealPortion:
    async def test_valid(self, mock_message, fsm_context):
        mock_message.text = "100 г"
        await fsm_context.set_state(FoodForm.portion)
        await meal_portion(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == FoodForm.notes.state

    async def test_skip(self, mock_message, fsm_context):
        mock_message.text = "-"
        await fsm_context.set_state(FoodForm.portion)
        await meal_portion(mock_message, fsm_context)
        data = await fsm_context.get_data()
        assert data["portion"] == ""


class TestMealNotes:
    @patch("bot.handlers.food.api_client")
    async def test_save(self, mock_api, mock_message, fsm_context):
        mock_api.create_food_entry = AsyncMock(return_value={"id": 1, "meal_time": None})
        mock_message.text = "Утром"
        await fsm_context.set_state(FoodForm.notes)
        await fsm_context.update_data(pet_id=1, food_name="Корм", portion="100 г")
        await meal_notes(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None
        mock_api.create_food_entry.assert_awaited_once()

    @patch("bot.handlers.food.api_client")
    async def test_skip_notes(self, mock_api, mock_message, fsm_context):
        mock_api.create_food_entry = AsyncMock(return_value={"id": 1, "meal_time": None})
        mock_message.text = "-"
        await fsm_context.set_state(FoodForm.notes)
        await fsm_context.update_data(pet_id=1, food_name="Корм")
        await meal_notes(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None


class TestMealList:
    @patch("bot.handlers.food.api_client")
    async def test_no_pets(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_meal_list(mock_callback)

    @patch("bot.handlers.food.api_client")
    async def test_empty(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.list_food_entries = AsyncMock(return_value=[])
        await cb_meal_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "нет" in text.lower()

    @patch("bot.handlers.food.api_client")
    async def test_with_entries(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.list_food_entries = AsyncMock(return_value=[
            {"food_name": "Корм", "pet_id": 1, "portion": "100г", "meal_time": None},
        ])
        await cb_meal_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Корм" in text


class TestWaterAdd:
    @patch("bot.handlers.food.api_client")
    async def test_no_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_water_add(mock_callback, fsm_context)

    @patch("bot.handlers.food.api_client")
    async def test_with_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        await cb_water_add(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == WaterForm.choosing_pet.state


class TestWaterPet:
    @patch("bot.handlers.food.api_client")
    async def test_valid(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_water:1"
        mock_api.get_pet = AsyncMock(return_value={"id": 1, "name": "Рекс"})
        await fsm_context.set_state(WaterForm.choosing_pet)
        await cb_water_pet(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == WaterForm.amount.state


class TestWaterAmount:
    @patch("bot.handlers.food.api_client")
    async def test_valid(self, mock_api, mock_message, fsm_context):
        mock_api.create_water_entry = AsyncMock(return_value={"id": 1, "recorded_at": None})
        mock_message.text = "200"
        await fsm_context.set_state(WaterForm.amount)
        await fsm_context.update_data(pet_id=1)
        await water_amount(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None

    async def test_invalid(self, mock_message, fsm_context):
        mock_message.text = "abc"
        await fsm_context.set_state(WaterForm.amount)
        await water_amount(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == WaterForm.amount.state


class TestWaterList:
    @patch("bot.handlers.food.api_client")
    async def test_empty(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.list_water_entries = AsyncMock(return_value=[])
        await cb_water_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "нет" in text.lower()

    @patch("bot.handlers.food.api_client")
    async def test_with_entries(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.list_water_entries = AsyncMock(return_value=[
            {"pet_id": 1, "amount_ml": 200, "recorded_at": None},
        ])
        await cb_water_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "200" in text


class TestAllergyAdd:
    @patch("bot.handlers.food.api_client")
    async def test_no_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_allergy_add(mock_callback, fsm_context)

    @patch("bot.handlers.food.api_client")
    async def test_with_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        await cb_allergy_add(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == AllergyForm.choosing_pet.state


class TestAllergyPet:
    @patch("bot.handlers.food.api_client")
    async def test_valid(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_allergy:1"
        mock_api.get_pet = AsyncMock(return_value={"id": 1, "name": "Рекс"})
        await fsm_context.set_state(AllergyForm.choosing_pet)
        await cb_allergy_pet(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == AllergyForm.allergen.state


class TestAllergySteps:
    async def test_allergen_valid(self, mock_message, fsm_context):
        mock_message.text = "Курица"
        await fsm_context.set_state(AllergyForm.allergen)
        await allergy_allergen(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == AllergyForm.reaction.state

    async def test_allergen_empty(self, mock_message, fsm_context):
        mock_message.text = ""
        await fsm_context.set_state(AllergyForm.allergen)
        await allergy_allergen(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == AllergyForm.allergen.state

    async def test_reaction(self, mock_message, fsm_context):
        mock_message.text = "Сыпь"
        await fsm_context.set_state(AllergyForm.reaction)
        await allergy_reaction(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == AllergyForm.notes.state

    async def test_reaction_skip(self, mock_message, fsm_context):
        mock_message.text = "-"
        await fsm_context.set_state(AllergyForm.reaction)
        await allergy_reaction(mock_message, fsm_context)
        data = await fsm_context.get_data()
        assert data["reaction"] == ""

    @patch("bot.handlers.food.api_client")
    async def test_notes_save(self, mock_api, mock_message, fsm_context):
        mock_api.create_allergy = AsyncMock()
        mock_message.text = "Замечена вчера"
        await fsm_context.set_state(AllergyForm.notes)
        await fsm_context.update_data(pet_id=1, allergen="Курица", reaction="Сыпь")
        await allergy_notes(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None
        mock_api.create_allergy.assert_awaited_once()

    @patch("bot.handlers.food.api_client")
    async def test_notes_skip(self, mock_api, mock_message, fsm_context):
        mock_api.create_allergy = AsyncMock()
        mock_message.text = "-"
        await fsm_context.set_state(AllergyForm.notes)
        await fsm_context.update_data(pet_id=1, allergen="Курица")
        await allergy_notes(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None


class TestAllergyList:
    @patch("bot.handlers.food.api_client")
    async def test_empty(self, mock_api, mock_callback):
        mock_api.list_allergies_by_user = AsyncMock(return_value=[])
        await cb_allergy_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "не зарегистрировано" in text

    @patch("bot.handlers.food.api_client")
    async def test_with_data(self, mock_api, mock_callback):
        mock_api.list_allergies_by_user = AsyncMock(return_value=[
            {"id": 1, "allergen": "Курица", "reaction": "Сыпь"},
        ])
        await cb_allergy_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Курица" in text


class TestAllergyDelete:
    @patch("bot.handlers.food.api_client")
    async def test_success(self, mock_api, mock_callback):
        mock_callback.data = "food:allergy:del:1"
        mock_api.delete_allergy = AsyncMock(return_value=True)
        mock_api.list_allergies_by_user = AsyncMock(return_value=[])
        await cb_allergy_delete(mock_callback)

    async def test_invalid_id(self, mock_callback):
        mock_callback.data = "food:allergy:del:abc"
        await cb_allergy_delete(mock_callback)
        mock_callback.answer.assert_awaited_once()


class TestMealClear:
    async def test_confirm_prompt(self, mock_callback):
        await cb_meal_clear_confirm(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "уверены" in text.lower()

    @patch("bot.handlers.food.api_client")
    async def test_clear(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.clear_food_entries = AsyncMock()
        await cb_meal_clear(mock_callback)
        mock_api.clear_food_entries.assert_awaited_once()


class TestWaterClear:
    async def test_confirm_prompt(self, mock_callback):
        await cb_water_clear_confirm(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "уверены" in text.lower()

    @patch("bot.handlers.food.api_client")
    async def test_clear(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.clear_water_entries = AsyncMock()
        await cb_water_clear(mock_callback)
        mock_api.clear_water_entries.assert_awaited_once()


class TestFoodToday:
    @patch("bot.handlers.food.api_client")
    async def test_no_pets(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_food_today(mock_callback)

    @patch("bot.handlers.food.api_client")
    async def test_with_data(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.get_daily_summary = AsyncMock(return_value={
            "food_entries": [{"food_name": "Корм", "portion": "100г", "meal_time": "2024-01-01T09:00:00"}],
            "water_entries": [{"amount_ml": 200}],
            "total_ml": 200,
        })
        await cb_food_today(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Корм" in text

    @patch("bot.handlers.food.api_client")
    async def test_no_entries(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.get_daily_summary = AsyncMock(return_value={
            "food_entries": [],
            "water_entries": [],
            "total_ml": 0,
        })
        await cb_food_today(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "не записано" in text
