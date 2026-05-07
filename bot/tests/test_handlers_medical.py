"""Tests for bot.handlers.medical — vaccines, vet visits, weight, documents."""

from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.medical import (
    cb_doc_add,
    cb_doc_pet,
    cb_doc_type,
    cb_docs_list,
    cb_documents,
    cb_med_menu,
    cb_vaccine_add,
    cb_vaccine_pet,
    cb_vaccines,
    cb_vaccines_list,
    cb_vet_add,
    cb_vet_pet,
    cb_vetvisits,
    cb_vetvisits_list,
    cb_weight,
    cb_weight_add,
    cb_weight_chart,
    cb_weight_list,
    cb_weight_pet,
    doc_description,
    doc_photo,
    doc_photo_invalid,
    medical_menu,
    vaccine_date_done,
    vaccine_name,
    vaccine_next_date,
    vaccine_next_skip,
    vaccine_notes,
    vet_date,
    vet_diagnosis,
    vet_notes,
    vet_treatment,
    weight_value,
)
from bot.states.states import DocumentForm, VaccinationForm, VetVisitForm, WeightForm


class TestMedicalMenu:
    async def test_message(self, mock_message):
        await medical_menu(mock_message)
        text = mock_message.answer.call_args[0][0]
        assert "Медицинская карта" in text

    async def test_callback(self, mock_callback):
        await cb_med_menu(mock_callback)
        mock_callback.message.edit_text.assert_awaited_once()


class TestMedSubmenus:
    async def test_vaccines(self, mock_callback):
        await cb_vaccines(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Прививки" in text

    async def test_vetvisits(self, mock_callback):
        await cb_vetvisits(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Визиты" in text

    async def test_weight(self, mock_callback):
        await cb_weight(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "вес" in text.lower()

    async def test_documents(self, mock_callback):
        await cb_documents(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Документы" in text


class TestVaccineAdd:
    @patch("bot.handlers.medical.api_client")
    async def test_no_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_vaccine_add(mock_callback, fsm_context)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "добавьте питомца" in text.lower()

    @patch("bot.handlers.medical.api_client")
    async def test_with_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        await cb_vaccine_add(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == VaccinationForm.choosing_pet.state


class TestVaccinePet:
    @patch("bot.handlers.medical.api_client")
    async def test_valid(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_vaccine:1"
        mock_api.get_pet = AsyncMock(return_value={"id": 1, "name": "Рекс"})
        await fsm_context.set_state(VaccinationForm.choosing_pet)
        await cb_vaccine_pet(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == VaccinationForm.name.state

    @patch("bot.handlers.medical.api_client")
    async def test_not_found(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_vaccine:999"
        mock_api.get_pet = AsyncMock(return_value=None)
        await fsm_context.set_state(VaccinationForm.choosing_pet)
        await cb_vaccine_pet(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()

    async def test_invalid_id(self, mock_callback, fsm_context):
        mock_callback.data = "pet:select_vaccine:abc"
        await fsm_context.set_state(VaccinationForm.choosing_pet)
        await cb_vaccine_pet(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()


class TestVaccineSteps:
    async def test_name_valid(self, mock_message, fsm_context):
        mock_message.text = "Нобивак"
        await fsm_context.set_state(VaccinationForm.name)
        await vaccine_name(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == VaccinationForm.date_done.state

    async def test_name_empty(self, mock_message, fsm_context):
        mock_message.text = ""
        await fsm_context.set_state(VaccinationForm.name)
        await vaccine_name(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == VaccinationForm.name.state

    async def test_date_done_valid(self, mock_message, fsm_context):
        mock_message.text = "01.06.2024"
        await fsm_context.set_state(VaccinationForm.date_done)
        await vaccine_date_done(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == VaccinationForm.next_date.state

    async def test_date_done_invalid(self, mock_message, fsm_context):
        mock_message.text = "invalid"
        await fsm_context.set_state(VaccinationForm.date_done)
        await vaccine_date_done(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == VaccinationForm.date_done.state

    async def test_next_date_skip(self, mock_callback, fsm_context):
        await fsm_context.set_state(VaccinationForm.next_date)
        await vaccine_next_skip(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == VaccinationForm.notes.state

    async def test_next_date_valid(self, mock_message, fsm_context):
        mock_message.text = "01.06.2025"
        await fsm_context.set_state(VaccinationForm.next_date)
        await vaccine_next_date(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == VaccinationForm.notes.state

    async def test_next_date_invalid(self, mock_message, fsm_context):
        mock_message.text = "invalid"
        await fsm_context.set_state(VaccinationForm.next_date)
        await vaccine_next_date(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == VaccinationForm.next_date.state

    @patch("bot.handlers.medical.api_client")
    async def test_notes_save(self, mock_api, mock_message, fsm_context):
        mock_api.create_vaccination = AsyncMock()
        mock_message.text = "Всё ок"
        await fsm_context.set_state(VaccinationForm.notes)
        await fsm_context.update_data(pet_id=1, vac_name="Нобивак", date_done="2024-06-01")
        await vaccine_notes(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None
        mock_api.create_vaccination.assert_awaited_once()

    @patch("bot.handlers.medical.api_client")
    async def test_notes_skip(self, mock_api, mock_message, fsm_context):
        mock_api.create_vaccination = AsyncMock()
        mock_message.text = "-"
        await fsm_context.set_state(VaccinationForm.notes)
        await fsm_context.update_data(pet_id=1, vac_name="Нобивак", date_done="2024-06-01", next_date="2025-06-01")
        await vaccine_notes(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None


class TestVaccinesList:
    @patch("bot.handlers.medical.api_client")
    async def test_no_pets(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_vaccines_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Нет питомцев" in text

    @patch("bot.handlers.medical.api_client")
    async def test_empty(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.list_vaccinations = AsyncMock(return_value=[])
        await cb_vaccines_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "нет" in text.lower() or "пока нет" in text.lower()

    @patch("bot.handlers.medical.api_client")
    async def test_with_data(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.list_vaccinations = AsyncMock(return_value=[
            {"name": "Нобивак", "pet_id": 1, "date_done": None, "next_date": None},
        ])
        await cb_vaccines_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Нобивак" in text


class TestVetAdd:
    @patch("bot.handlers.medical.api_client")
    async def test_no_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_vet_add(mock_callback, fsm_context)

    @patch("bot.handlers.medical.api_client")
    async def test_with_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        await cb_vet_add(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == VetVisitForm.choosing_pet.state


class TestVetPet:
    @patch("bot.handlers.medical.api_client")
    async def test_valid(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_vetvisit:1"
        mock_api.get_pet = AsyncMock(return_value={"id": 1, "name": "Рекс"})
        await fsm_context.set_state(VetVisitForm.choosing_pet)
        await cb_vet_pet(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == VetVisitForm.visit_date.state


class TestVetSteps:
    async def test_date_valid(self, mock_message, fsm_context):
        mock_message.text = "01.06.2024"
        await fsm_context.set_state(VetVisitForm.visit_date)
        await vet_date(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == VetVisitForm.diagnosis.state

    async def test_date_invalid(self, mock_message, fsm_context):
        mock_message.text = "invalid"
        await fsm_context.set_state(VetVisitForm.visit_date)
        await vet_date(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == VetVisitForm.visit_date.state

    async def test_diagnosis(self, mock_message, fsm_context):
        mock_message.text = "Осмотр"
        await fsm_context.set_state(VetVisitForm.diagnosis)
        await vet_diagnosis(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == VetVisitForm.treatment.state

    async def test_diagnosis_skip(self, mock_message, fsm_context):
        mock_message.text = "-"
        await fsm_context.set_state(VetVisitForm.diagnosis)
        await vet_diagnosis(mock_message, fsm_context)
        data = await fsm_context.get_data()
        assert data["diagnosis"] == ""

    async def test_treatment(self, mock_message, fsm_context):
        mock_message.text = "Витамины"
        await fsm_context.set_state(VetVisitForm.treatment)
        await vet_treatment(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == VetVisitForm.notes.state

    @patch("bot.handlers.medical.api_client")
    async def test_notes_save(self, mock_api, mock_message, fsm_context):
        mock_api.create_vet_visit = AsyncMock()
        mock_message.text = "Всё хорошо"
        await fsm_context.set_state(VetVisitForm.notes)
        await fsm_context.update_data(pet_id=1, visit_date="2024-06-01", diagnosis="Осмотр", treatment="")
        await vet_notes(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None
        mock_api.create_vet_visit.assert_awaited_once()


class TestVetVisitsList:
    @patch("bot.handlers.medical.api_client")
    async def test_empty(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.list_vet_visits = AsyncMock(return_value=[])
        await cb_vetvisits_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "нет" in text.lower()

    @patch("bot.handlers.medical.api_client")
    async def test_with_data(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.list_vet_visits = AsyncMock(return_value=[
            {"pet_id": 1, "visit_date": None, "diagnosis": "Осмотр", "treatment": ""},
        ])
        await cb_vetvisits_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Осмотр" in text


class TestWeightAdd:
    @patch("bot.handlers.medical.api_client")
    async def test_no_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_weight_add(mock_callback, fsm_context)

    @patch("bot.handlers.medical.api_client")
    async def test_with_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        await cb_weight_add(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == WeightForm.choosing_pet.state


class TestWeightPet:
    @patch("bot.handlers.medical.api_client")
    async def test_valid(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_weight:1"
        mock_api.get_pet = AsyncMock(return_value={"id": 1, "name": "Рекс"})
        await fsm_context.set_state(WeightForm.choosing_pet)
        await cb_weight_pet(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == WeightForm.weight.state


class TestWeightValue:
    @patch("bot.handlers.medical.api_client")
    async def test_valid(self, mock_api, mock_message, fsm_context):
        mock_api.get_pet = AsyncMock(return_value={"id": 1, "name": "Рекс"})
        mock_api.create_weight_record = AsyncMock(return_value={"recorded_at": None})
        mock_api.update_pet = AsyncMock(return_value=True)
        mock_message.text = "4.5"
        await fsm_context.set_state(WeightForm.weight)
        await fsm_context.update_data(pet_id=1)
        await weight_value(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None

    async def test_invalid(self, mock_message, fsm_context):
        mock_message.text = "abc"
        await fsm_context.set_state(WeightForm.weight)
        await weight_value(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == WeightForm.weight.state

    @patch("bot.handlers.medical.api_client")
    async def test_pet_not_found(self, mock_api, mock_message, fsm_context):
        mock_api.get_pet = AsyncMock(return_value=None)
        mock_message.text = "5"
        await fsm_context.set_state(WeightForm.weight)
        await fsm_context.update_data(pet_id=999)
        await weight_value(mock_message, fsm_context)
        text = mock_message.answer.call_args[0][0]
        assert "не найден" in text


class TestWeightList:
    @patch("bot.handlers.medical.api_client")
    async def test_empty(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.list_weight_records = AsyncMock(return_value=[])
        await cb_weight_list(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "нет" in text.lower()


class TestWeightChart:
    @patch("bot.handlers.medical.api_client")
    async def test_no_pets(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_weight_chart(mock_callback)

    @patch("bot.handlers.medical.api_client")
    async def test_few_records(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.list_weight_records = AsyncMock(return_value=[
            {"weight": 5, "recorded_at": "2024-01-01"},
        ])
        await cb_weight_chart(mock_callback)
        mock_callback.answer.assert_awaited()


class TestDocAdd:
    @patch("bot.handlers.medical.api_client")
    async def test_no_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_doc_add(mock_callback, fsm_context)

    @patch("bot.handlers.medical.api_client")
    async def test_with_pets(self, mock_api, mock_callback, fsm_context):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        await cb_doc_add(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == DocumentForm.choosing_pet.state


class TestDocPet:
    @patch("bot.handlers.medical.api_client")
    async def test_valid(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_doc:1"
        mock_api.get_pet = AsyncMock(return_value={"id": 1, "name": "Рекс"})
        await fsm_context.set_state(DocumentForm.choosing_pet)
        await cb_doc_pet(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == DocumentForm.doc_type.state

    @patch("bot.handlers.medical.api_client")
    async def test_not_found(self, mock_api, mock_callback, fsm_context):
        mock_callback.data = "pet:select_doc:999"
        mock_api.get_pet = AsyncMock(return_value=None)
        await fsm_context.set_state(DocumentForm.choosing_pet)
        await cb_doc_pet(mock_callback, fsm_context)
        mock_callback.answer.assert_awaited_once()


class TestDocType:
    async def test_select(self, mock_callback, fsm_context):
        mock_callback.data = "doc_type:passport"
        await fsm_context.set_state(DocumentForm.doc_type)
        await cb_doc_type(mock_callback, fsm_context)
        state = await fsm_context.get_state()
        assert state == DocumentForm.photo.state


class TestDocPhoto:
    async def test_valid(self, mock_message, fsm_context):
        photo = MagicMock()
        photo.file_id = "photo_123"
        mock_message.photo = [photo]
        await fsm_context.set_state(DocumentForm.photo)
        await doc_photo(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state == DocumentForm.description.state

    async def test_invalid(self, mock_message):
        await doc_photo_invalid(mock_message)
        text = mock_message.answer.call_args[0][0]
        assert "фото" in text


class TestDocDescription:
    @patch("bot.handlers.medical.api_client")
    async def test_with_text(self, mock_api, mock_message, fsm_context):
        mock_api.create_document = AsyncMock()
        mock_message.text = "Ветпаспорт Рекса"
        await fsm_context.set_state(DocumentForm.description)
        await fsm_context.update_data(pet_id=1, doc_type="passport", file_id="photo_123")
        await doc_description(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None

    @patch("bot.handlers.medical.api_client")
    async def test_skip(self, mock_api, mock_message, fsm_context):
        mock_api.create_document = AsyncMock()
        mock_message.text = "-"
        await fsm_context.set_state(DocumentForm.description)
        await fsm_context.update_data(pet_id=1, doc_type="other", file_id="photo_456")
        await doc_description(mock_message, fsm_context)
        state = await fsm_context.get_state()
        assert state is None


class TestDocsList:
    @patch("bot.handlers.medical.api_client")
    async def test_no_pets(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[])
        await cb_docs_list(mock_callback)

    @patch("bot.handlers.medical.api_client")
    async def test_empty(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.list_documents = AsyncMock(return_value=[])
        await cb_docs_list(mock_callback)

    @patch("bot.handlers.medical.api_client")
    async def test_with_docs(self, mock_api, mock_callback):
        mock_api.list_pets = AsyncMock(return_value=[{"id": 1, "name": "Рекс"}])
        mock_api.list_documents = AsyncMock(return_value=[
            {"pet_id": 1, "doc_type": "passport", "file_id": "file_123", "description": "Паспорт"},
        ])
        mock_callback.message.answer_photo = AsyncMock()
        await cb_docs_list(mock_callback)
        mock_callback.message.answer_photo.assert_awaited_once()
