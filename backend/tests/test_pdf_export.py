"""Smoke tests for backend.services.pdf_export."""

import os

from backend.services.pdf_export import generate_pet_pdf


class TestGeneratePetPdf:
    def _pet_data(self):
        return {
            "name": "Rex",
            "species": "собака",
            "breed": "Лабрадор",
            "birth_date": "15.03.2020",
            "age": "4 года",
            "weight": 30.0,
            "target_weight": 28.0,
        }

    def test_returns_bytes(self):
        if not os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            return  # skip if font not available
        result = generate_pet_pdf(self._pet_data(), [], [], [], [])
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_with_all_data(self):
        if not os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            return
        vaccinations = [{"name": "Бешенство", "date_done": "01.01.2024", "next_date": "01.01.2025", "notes": ""}]
        vet_visits = [{"visit_date": "15.06.2024", "diagnosis": "Здоров", "treatment": "Не требуется"}]
        weight_records = [{"weight": 30.5, "recorded_at": "01.01.2024"}]
        allergies = [{"allergen": "Курица", "reaction": "Зуд"}]
        result = generate_pet_pdf(self._pet_data(), vaccinations, vet_visits, weight_records, allergies)
        assert isinstance(result, bytes)

    def test_empty_pet_data(self):
        if not os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            return
        result = generate_pet_pdf({"name": "X"}, [], [], [], [])
        assert isinstance(result, bytes)
