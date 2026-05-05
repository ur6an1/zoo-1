"""Tests for backend.services.clinics — haversine, address builder, formatting."""

from backend.services.clinics import (
    _build_address,
    _haversine,
    _radius_label,
    format_clinic_card,
)


class TestHaversine:
    def test_same_point(self):
        assert _haversine(55.75, 37.62, 55.75, 37.62) == 0.0

    def test_known_distance(self):
        # Moscow to Saint Petersburg ~ 634 km
        dist = _haversine(55.7558, 37.6173, 59.9343, 30.3351)
        assert 630_000 < dist < 640_000

    def test_short_distance(self):
        dist = _haversine(55.75, 37.62, 55.751, 37.621)
        assert 50 < dist < 200


class TestBuildAddress:
    def test_full_address(self):
        tags = {"addr:street": "Ленина", "addr:housenumber": "42", "addr:city": "Москва"}
        assert _build_address(tags) == "Ленина 42, Москва"

    def test_street_only(self):
        tags = {"addr:street": "Ленина"}
        assert _build_address(tags) == "Ленина"

    def test_city_only(self):
        tags = {"addr:city": "Москва"}
        assert _build_address(tags) == "Москва"

    def test_empty(self):
        assert _build_address({}) == ""


class TestRadiusLabel:
    def test_integer_km(self):
        assert _radius_label(5000) == "5 км"

    def test_fractional_km(self):
        assert _radius_label(2500) == "2.5 км"

    def test_1km(self):
        assert _radius_label(1000) == "1 км"


class TestFormatClinicCard:
    def test_full_card(self):
        clinic = {
            "name": "ВетДоктор",
            "lat": 55.75,
            "lon": 37.62,
            "distance_m": 1500,
            "phone": "+7-999-123-45-67",
            "website": "https://vetdoctor.ru",
            "opening_hours": "09:00-21:00",
            "address": "Ленина 42, Москва",
        }
        result = format_clinic_card(clinic, 1)
        assert "ВетДоктор" in result
        assert "1.5 км" in result
        assert "Ленина 42" in result
        assert "+7-999-123-45-67" in result

    def test_minimal_card(self):
        clinic = {
            "name": "Клиника",
            "lat": 55.75,
            "lon": 37.62,
            "distance_m": 500,
            "phone": "",
            "website": "",
            "opening_hours": "",
            "address": "",
        }
        result = format_clinic_card(clinic, 1)
        assert "Клиника" in result
        assert "0.5 км" in result
