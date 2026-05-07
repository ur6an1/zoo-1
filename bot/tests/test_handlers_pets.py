"""Tests for bot.handlers.pets — pet profiles CRUD, stats, export."""

from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.pets import (
    _save_pet,
    cb_confirm_delete,
    cb_delete_pet,
    cb_pet_add,
    cb_pet_edit,
    cb_pet_export,
    cb_pet_export_pdf,
    cb_pet_list,
    cb_pet_stats,
    cb_pet_view,
    cb_edit_field,
    edit_birth,
    edit_breed,
    edit_name,
    edit_photo,
    edit_weight,
    my_pets,
    pet_birth_date,
    pet_birth_skip,
    pet_breed,
    pet_breed_skip,
    pet_name,
    pet_photo,
    pet_photo_invalid,
    pet_photo_skip,
    pet_species,
    pet_weight,
    pet_weight_skip,
)
from bot.states.states import EditPetForm, PetForm


SAMPLE_PET = {
    "id": 1, "name": "Рекс", "species": "собака", "breed": "овчарка",
    "species_emoji": "🐶", "birth_date": None, "age_str": "5 лет",
    "weight": 30, "photo_file_id": None,
}


class TestMyPets:
    @patch("bot.handlers.pets.api_client")
    async def test_no_pets(self, mock_api, mock_message):
        mock_api.track_user_activity = AsyncMock()
        mock_api.list_pets = AsyncMock(return_value=[])
        await my_pets(mock_message)
        text = mock_message.answer.call_args[0][0]
        assert "нет питомцев" in text

    @patch("bot.handlers.pets.api_client")
    async def test_with_pets(self, mock_api, mock_message):
        mock_api.track_user_activity = AsyncMock()
        mock_api.list_pets = AsyncMock(return_value=[SAMPLE_PET])
        await my_pets(mock_message)
        text = mock_message.answer.call_args[0][0]
        assert "Ваши питомцы" in text


class TestCbPetList:
    @patch("bot.handlers.pets.api_client")
    async def test_no_pets(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_pet_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "нет питомцев" in text

    @patch("bot.handlers.pets.api_client")
    async def test_with_pets(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[SAMPLE_PET])
        await cb_pet_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Ваши питомцы" in text


class TestCbPetView:
    @patch("bot.handlers.pets.api_client")
    async def test_invalid_id(self, mock_api, mock_callback):
        mock_callback.data = "pet:view:abc"
        await cb_pet_view(mock_callback)
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.pets.api_client")
    async def test_not_found(self, mock_api, mock_callback):
        mock_callback.data = "pet:view:999"
        mock_api.get_pet = AsyncMock(return_value=None)
        await cb_pet_view(mock_callback)
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.pets.api_client")
    async def test_view_no_photo(self, mock_api, mock_callback):
        mock_callback.data = "pet:view:1"
        mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
        await cb_pet_view(mock_callback)
        mock_callback.message.edit_text.assert_awaited_once()
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Рекс" in text

    @patch("bot.handlers.pets.api_client")
    async def test_view_with_photo(self, mock_api, mock_callback):
        mock_callback.data = "pet:view:1"
        pet = {**SAMPLE_PET, "photo_file_id": "photo_123"}
        mock_api.get_pet = AsyncMock(return_value=pet)
        mock_callback.message.answer_photo = AsyncMock()
        mock_callback.message.delete = AsyncMock()
        await cb_pet_view(mock_callback)
        mock_callback.message.answer_photo.assert_awaited_once()


class TestCbPetAdd:
    @patch("bot.handlers.pets.api_client")
    async def test_limit_reached(self, mock_api, mock_callback, fsm_context):
        mock_api.check_pet_limit = AsyncMock(return_value=(False, 0))
        mock_api.get_plan_tier = AsyncMock(return_value="free")
        await cb_pet_add(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "лимит" in text.lower()

    @patch("bot.handlers.pets.api_client")
    async def test_start_add(self, mock_api, mock_callback, fsm_context):
        mock_api.check_pet_limit = AsyncMock(return_value=(True, 3))
        mock_api.track_event = AsyncMock()
        await cb_pet_add(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.name.state
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "имя" in text.lower() or "Как зовут" in text


class TestPetNameStep:
    async def test_valid_name(self, mock_message, fsm_context):
        mock_message.text = "Рекс"
        await fsm_context.set_state(PetForm.name)
        await pet_name(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.species.state

    async def test_empty_name(self, mock_message, fsm_context):
        mock_message.text = ""
        await fsm_context.set_state(PetForm.name)
        await pet_name(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.name.state

    async def test_long_name(self, mock_message, fsm_context):
        mock_message.text = "X" * 101
        await fsm_context.set_state(PetForm.name)
        await pet_name(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.name.state


class TestPetSpeciesStep:
    async def test_select_species(self, mock_callback, fsm_context):
        mock_callback.data = "species:собака"
        await fsm_context.set_state(PetForm.species)
        await pet_species(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.breed.state
        data = await fsm_context.get_data()
        assert data["species"] == "собака"


class TestPetBreedStep:
    async def test_enter_breed(self, mock_message, fsm_context):
        mock_message.text = "Овчарка"
        await fsm_context.set_state(PetForm.breed)
        await pet_breed(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.birth_date.state

    async def test_skip_breed(self, mock_callback, fsm_context):
        await fsm_context.set_state(PetForm.breed)
        await pet_breed_skip(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.birth_date.state
        data = await fsm_context.get_data()
        assert data["breed"] == ""

    async def test_breed_too_long(self, mock_message, fsm_context):
        mock_message.text = "X" * 101
        await fsm_context.set_state(PetForm.breed)
        await pet_breed(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.breed.state


class TestPetBirthDateStep:
    async def test_valid_date(self, mock_message, fsm_context):
        mock_message.text = "15.03.2020"
        await fsm_context.set_state(PetForm.birth_date)
        await pet_birth_date(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.weight.state

    async def test_invalid_date(self, mock_message, fsm_context):
        mock_message.text = "invalid"
        await fsm_context.set_state(PetForm.birth_date)
        await pet_birth_date(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.birth_date.state

    async def test_skip_date(self, mock_callback, fsm_context):
        await fsm_context.set_state(PetForm.birth_date)
        await pet_birth_skip(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.weight.state


class TestPetWeightStep:
    async def test_valid_weight(self, mock_message, fsm_context):
        mock_message.text = "4.5"
        await fsm_context.set_state(PetForm.weight)
        await pet_weight(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.photo.state

    async def test_invalid_weight(self, mock_message, fsm_context):
        mock_message.text = "abc"
        await fsm_context.set_state(PetForm.weight)
        await pet_weight(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.weight.state

    async def test_skip_weight(self, mock_callback, fsm_context):
        await fsm_context.set_state(PetForm.weight)
        await pet_weight_skip(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == PetForm.photo.state


class TestPetPhotoStep:
    @patch("bot.handlers.pets.api_client")
    async def test_skip_photo(self, mock_api, mock_callback, fsm_context):
        mock_api.create_pet = AsyncMock(return_value=SAMPLE_PET)
        mock_api.get_pet_count = AsyncMock(return_value=1)
        mock_api.track_event = AsyncMock()
        await fsm_context.set_state(PetForm.photo)
        await fsm_context.update_data(name="Рекс", species="собака", breed="", photo_file_id=None)
        await pet_photo_skip(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state is None

    @patch("bot.handlers.pets.api_client")
    async def test_upload_photo(self, mock_api, mock_message, fsm_context):
        mock_api.create_pet = AsyncMock(return_value=SAMPLE_PET)
        mock_api.get_pet_count = AsyncMock(return_value=2)
        mock_api.track_event = AsyncMock()
        photo = MagicMock()
        photo.file_id = "photo_abc"
        mock_message.photo = [photo]
        await fsm_context.set_state(PetForm.photo)
        await fsm_context.update_data(name="Рекс", species="собака", breed="")
        await pet_photo(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None

    async def test_invalid_input(self, mock_message):
        await pet_photo_invalid(mock_message)
        text = mock_message.answer.call_args[0][0]
        assert "фото" in text


class TestSavePet:
    @patch("bot.handlers.pets.api_client")
    async def test_first_pet(self, mock_api, mock_message, fsm_context):
        mock_api.create_pet = AsyncMock(return_value=SAMPLE_PET)
        mock_api.get_pet_count = AsyncMock(return_value=1)
        mock_api.track_event = AsyncMock()

        await fsm_context.update_data(name="Рекс", species="собака", breed="овчарка", birth_date="2020-01-15", weight=30.0)
        await _save_pet(mock_message, fsm_context, 12345)

        assert mock_api.track_event.await_count == 2
        assert mock_message.answer.await_count == 2

    @patch("bot.handlers.pets.api_client")
    async def test_subsequent_pet(self, mock_api, mock_message, fsm_context):
        mock_api.create_pet = AsyncMock(return_value=SAMPLE_PET)
        mock_api.get_pet_count = AsyncMock(return_value=3)
        mock_api.track_event = AsyncMock()

        await fsm_context.update_data(name="Мурка", species="кошка", breed="")
        await _save_pet(mock_message, fsm_context, 12345)

        assert mock_api.track_event.await_count == 1


class TestPetEdit:
    @patch("bot.handlers.pets.api_client")
    async def test_edit_menu(self, mock_api, mock_callback):
        mock_callback.data = "pet:edit:1"
        mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
        await cb_pet_edit(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Редактирование" in text

    @patch("bot.handlers.pets.api_client")
    async def test_edit_not_found(self, mock_api, mock_callback):
        mock_callback.data = "pet:edit:999"
        mock_api.get_pet = AsyncMock(return_value=None)
        await cb_pet_edit(mock_callback)
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.pets.api_client")
    async def test_edit_invalid_id(self, mock_api, mock_callback):
        mock_callback.data = "pet:edit:abc"
        await cb_pet_edit(mock_callback)
        mock_callback.answer.assert_awaited_once()


class TestEditField:
    @patch("bot.handlers.pets.api_client")
    async def test_edit_name_field(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:edit_field:name:1"
        mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
        await cb_edit_field(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == EditPetForm.editing_name.state

    @patch("bot.handlers.pets.api_client")
    async def test_edit_weight_field(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:edit_field:weight:1"
        mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
        await cb_edit_field(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == EditPetForm.editing_weight.state

    @patch("bot.handlers.pets.api_client")
    async def test_pet_not_found(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:edit_field:name:999"
        mock_api.get_pet = AsyncMock(return_value=None)
        await cb_edit_field(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.pets.api_client")
    async def test_invalid_params(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:edit_field:"
        await cb_edit_field(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()


class TestEditName:
    @patch("bot.handlers.pets.api_client")
    async def test_valid_name(self, mock_api, mock_message, fsm_context):
        mock_api.update_pet = AsyncMock(return_value=SAMPLE_PET)
        mock_message.text = "Рексик"
        await fsm_context.set_state(EditPetForm.editing_name)
        await fsm_context.update_data(edit_pet_id=1)
        await edit_name(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "Рексик" in text

    @patch("bot.handlers.pets.api_client")
    async def test_pet_deleted(self, mock_api, mock_message, fsm_context):
        mock_api.update_pet = AsyncMock(return_value=None)
        mock_message.text = "Рексик"
        await fsm_context.set_state(EditPetForm.editing_name)
        await fsm_context.update_data(edit_pet_id=1)
        await edit_name(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "не найден" in text

    async def test_empty_name(self, mock_message, fsm_context):
        mock_message.text = ""
        await fsm_context.set_state(EditPetForm.editing_name)
        await edit_name(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == EditPetForm.editing_name.state

    async def test_long_name(self, mock_message, fsm_context):
        mock_message.text = "X" * 101
        await fsm_context.set_state(EditPetForm.editing_name)
        await edit_name(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == EditPetForm.editing_name.state


class TestEditBreed:
    @patch("bot.handlers.pets.api_client")
    async def test_valid(self, mock_api, mock_message, fsm_context):
        mock_api.update_pet = AsyncMock(return_value=SAMPLE_PET)
        mock_message.text = "Хаски"
        await fsm_context.set_state(EditPetForm.editing_breed)
        await fsm_context.update_data(edit_pet_id=1)
        await edit_breed(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "Хаски" in text

    @patch("bot.handlers.pets.api_client")
    async def test_not_found(self, mock_api, mock_message, fsm_context):
        mock_api.update_pet = AsyncMock(return_value=None)
        mock_message.text = "Хаски"
        await fsm_context.set_state(EditPetForm.editing_breed)
        await fsm_context.update_data(edit_pet_id=1)
        await edit_breed(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "не найден" in text


class TestEditBirth:
    @patch("bot.handlers.pets.api_client")
    async def test_valid(self, mock_api, mock_message, fsm_context):
        mock_api.update_pet = AsyncMock(return_value=SAMPLE_PET)
        mock_message.text = "01.06.2021"
        await fsm_context.set_state(EditPetForm.editing_birth_date)
        await fsm_context.update_data(edit_pet_id=1)
        await edit_birth(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "01.06.2021" in text

    async def test_invalid(self, mock_message, fsm_context):
        mock_message.text = "invalid"
        await fsm_context.set_state(EditPetForm.editing_birth_date)
        await edit_birth(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == EditPetForm.editing_birth_date.state

    @patch("bot.handlers.pets.api_client")
    async def test_not_found(self, mock_api, mock_message, fsm_context):
        mock_api.update_pet = AsyncMock(return_value=None)
        mock_message.text = "01.06.2021"
        await fsm_context.set_state(EditPetForm.editing_birth_date)
        await fsm_context.update_data(edit_pet_id=1)
        await edit_birth(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "не найден" in text


class TestEditWeight:
    @patch("bot.handlers.pets.api_client")
    async def test_valid(self, mock_api, mock_message, fsm_context):
        mock_api.update_pet = AsyncMock(return_value=SAMPLE_PET)
        mock_message.text = "5.5"
        await fsm_context.set_state(EditPetForm.editing_weight)
        await fsm_context.update_data(edit_pet_id=1)
        await edit_weight(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "5.5" in text

    async def test_invalid(self, mock_message, fsm_context):
        mock_message.text = "abc"
        await fsm_context.set_state(EditPetForm.editing_weight)
        await edit_weight(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == EditPetForm.editing_weight.state


class TestEditPhoto:
    @patch("bot.handlers.pets.api_client")
    async def test_valid(self, mock_api, mock_message, fsm_context):
        mock_api.update_pet = AsyncMock(return_value=SAMPLE_PET)
        photo = MagicMock()
        photo.file_id = "new_photo_id"
        mock_message.photo = [photo]
        await fsm_context.set_state(EditPetForm.editing_photo)
        await fsm_context.update_data(edit_pet_id=1)
        await edit_photo(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "обновлено" in text

    @patch("bot.handlers.pets.api_client")
    async def test_not_found(self, mock_api, mock_message, fsm_context):
        mock_api.update_pet = AsyncMock(return_value=None)
        photo = MagicMock()
        photo.file_id = "photo_id"
        mock_message.photo = [photo]
        await fsm_context.set_state(EditPetForm.editing_photo)
        await fsm_context.update_data(edit_pet_id=1)
        await edit_photo(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "не найден" in text


class TestDeletePet:
    @patch("bot.handlers.pets.api_client")
    async def test_confirm_delete(self, mock_api, mock_callback):
        mock_callback.data = "pet:confirm_delete:1"
        mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
        await cb_confirm_delete(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Рекс" in text
        assert "удалить" in text.lower()

    @patch("bot.handlers.pets.api_client")
    async def test_confirm_not_found(self, mock_api, mock_callback):
        mock_callback.data = "pet:confirm_delete:999"
        mock_api.get_pet = AsyncMock(return_value=None)
        await cb_confirm_delete(mock_callback)
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.pets.api_client")
    async def test_delete_success(self, mock_api, mock_callback):
        mock_callback.data = "pet:delete:1"
        mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
        mock_api.delete_pet = AsyncMock(return_value=True)
        await cb_delete_pet(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "удалён" in text

    @patch("bot.handlers.pets.api_client")
    async def test_delete_not_found(self, mock_api, mock_callback):
        mock_callback.data = "pet:delete:999"
        mock_api.get_pet = AsyncMock(return_value=None)
        await cb_delete_pet(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "не найден" in text

    @patch("bot.handlers.pets.api_client")
    async def test_delete_failed(self, mock_api, mock_callback):
        mock_callback.data = "pet:delete:1"
        mock_api.get_pet = AsyncMock(return_value=SAMPLE_PET)
        mock_api.delete_pet = AsyncMock(return_value=False)
        await cb_delete_pet(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "не найден" in text


class TestPetStats:
    @patch("bot.handlers.pets.api_client")
    async def test_with_stats(self, mock_api, mock_callback):
        mock_callback.data = "pet:stats:1"
        mock_api.get_pet_stats = AsyncMock(return_value={
            "pet": SAMPLE_PET,
            "counts": {
                "vaccinations": 2, "vet_visits": 1, "weight_records": 5,
                "food_entries": 10, "water_entries": 7, "allergies": 0,
                "documents": 1, "active_reminders": 3,
            },
            "last_vaccination": {"date_done": None, "name": "Бешенство"},
            "next_vaccination": {"next_date": None, "name": "Бешенство"},
            "last_visit": {"visit_date": None},
            "last_weight": {"weight": 31, "recorded_at": None},
        })
        await cb_pet_stats(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Статистика" in text
        assert "Бешенство" in text
        assert "31" in text

    @patch("bot.handlers.pets.api_client")
    async def test_empty_stats(self, mock_api, mock_callback):
        mock_callback.data = "pet:stats:1"
        mock_api.get_pet_stats = AsyncMock(return_value={
            "pet": SAMPLE_PET,
            "counts": {
                "vaccinations": 0, "vet_visits": 0, "weight_records": 0,
                "food_entries": 0, "water_entries": 0, "allergies": 0,
                "documents": 0, "active_reminders": 0,
            },
        })
        await cb_pet_stats(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Пока нет записей" in text

    @patch("bot.handlers.pets.api_client")
    async def test_not_found(self, mock_api, mock_callback):
        mock_callback.data = "pet:stats:999"
        mock_api.get_pet_stats = AsyncMock(return_value=None)
        await cb_pet_stats(mock_callback)
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.pets.api_client")
    async def test_invalid_id(self, mock_api, mock_callback):
        mock_callback.data = "pet:stats:abc"
        await cb_pet_stats(mock_callback)
        mock_callback.answer.assert_awaited_once()


class TestPetExport:
    @patch("bot.handlers.pets.api_client")
    async def test_export_txt(self, mock_api, mock_callback):
        mock_callback.data = "pet:export:1"
        mock_api.get_pet_export = AsyncMock(return_value={
            "pet": SAMPLE_PET,
            "vaccinations": [{"date_done": None, "name": "Бешенство", "next_date": None, "notes": "ок"}],
            "vet_visits": [{"visit_date": None, "diagnosis": "Осмотр", "treatment": "Витамины"}],
            "weight_records": [{"recorded_at": None, "weight": 31}],
            "allergies": [{"allergen": "Курица", "reaction": "Сыпь"}],
        })
        mock_callback.message.answer_document = AsyncMock()
        await cb_pet_export(mock_callback)
        mock_callback.message.answer_document.assert_awaited_once()

    @patch("bot.handlers.pets.api_client")
    async def test_export_not_found(self, mock_api, mock_callback):
        mock_callback.data = "pet:export:999"
        mock_api.get_pet_export = AsyncMock(return_value=None)
        await cb_pet_export(mock_callback)
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.pets.api_client")
    async def test_export_empty_data(self, mock_api, mock_callback):
        mock_callback.data = "pet:export:1"
        mock_api.get_pet_export = AsyncMock(return_value={
            "pet": SAMPLE_PET,
        })
        mock_callback.message.answer_document = AsyncMock()
        await cb_pet_export(mock_callback)
        mock_callback.message.answer_document.assert_awaited_once()


class TestPetExportPdf:
    @patch("bot.handlers.pets.api_client")
    async def test_no_permission(self, mock_api, mock_callback):
        mock_callback.data = "pet:export_pdf:1"
        mock_api.can_use_pdf_export = AsyncMock(return_value=False)
        await cb_pet_export_pdf(mock_callback)
        mock_callback.message.answer.assert_awaited_once()
        text = mock_callback.message.answer.call_args[0][0]
        assert "PRO" in text

    @patch("bot.handlers.pets.api_client")
    async def test_invalid_id(self, mock_api, mock_callback):
        mock_callback.data = "pet:export_pdf:abc"
        mock_api.can_use_pdf_export = AsyncMock(return_value=True)
        await cb_pet_export_pdf(mock_callback)
        mock_callback.answer.assert_awaited_once()

    @patch("bot.handlers.pets.api_client")
    async def test_not_found(self, mock_api, mock_callback):
        mock_callback.data = "pet:export_pdf:999"
        mock_api.can_use_pdf_export = AsyncMock(return_value=True)
        mock_api.get_pet_export = AsyncMock(return_value=None)
        await cb_pet_export_pdf(mock_callback)
        mock_callback.answer.assert_awaited_once()

    @patch("backend.backend.services.pdf_export.generate_pet_pdf")
    @patch("bot.handlers.pets.api_client")
    async def test_pdf_success(self, mock_api, mock_pdf, mock_callback):
        mock_callback.data = "pet:export_pdf:1"
        mock_api.can_use_pdf_export = AsyncMock(return_value=True)
        mock_api.get_pet_export = AsyncMock(return_value={
            "pet": SAMPLE_PET, "vaccinations": [], "vet_visits": [],
            "weight_records": [], "allergies": [],
        })
        mock_api.track_event = AsyncMock()
        mock_pdf.return_value = b"PDF_DATA"
        mock_callback.message.answer_document = AsyncMock()
        await cb_pet_export_pdf(mock_callback)
        mock_callback.message.answer_document.assert_awaited_once()

    @patch("backend.backend.services.pdf_export.generate_pet_pdf")
    @patch("bot.handlers.pets.api_client")
    async def test_pdf_generation_failed(self, mock_api, mock_pdf, mock_callback):
        mock_callback.data = "pet:export_pdf:1"
        mock_api.can_use_pdf_export = AsyncMock(return_value=True)
        mock_api.get_pet_export = AsyncMock(return_value={
            "pet": SAMPLE_PET, "vaccinations": [], "vet_visits": [],
            "weight_records": [], "allergies": [],
        })
        mock_pdf.return_value = None
        await cb_pet_export_pdf(mock_callback)
        mock_callback.answer.assert_awaited()
