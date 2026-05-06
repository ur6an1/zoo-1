"""Tests for bot.api_client — HTTP client for backend API."""

import base64
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from bot import api_client


def _mock_response(status_code=200, json_data=None):
    """Create a mock httpx.Response."""
    resp = httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "http://testserver/"),
    )
    return resp


@pytest.fixture(autouse=True)
def _reset_client():
    """Reset the global client before each test."""
    api_client._client = None
    yield
    api_client._client = None


class TestClientLifecycle:
    async def test_get_client_creates_client(self):
        c = await api_client.get_client()
        assert isinstance(c, httpx.AsyncClient)

    async def test_init(self):
        await api_client.init()
        assert api_client._client is not None

    async def test_close(self):
        await api_client.init()
        await api_client.close()
        assert api_client._client is None

    async def test_close_client_when_none(self):
        await api_client.close_client()
        assert api_client._client is None


class TestPetsApi:
    @patch("bot.api_client.get_client")
    async def test_list_pets(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data=[{"id": 1, "name": "Рекс"}])
        mock_get_client.return_value = mock_client

        result = await api_client.list_pets(12345)
        assert result == [{"id": 1, "name": "Рекс"}]
        mock_client.get.assert_awaited_once_with("/pets/by_user/12345")

    @patch("bot.api_client.get_client")
    async def test_get_pet_found(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"id": 1, "name": "Рекс"})
        mock_get_client.return_value = mock_client

        result = await api_client.get_pet(1, 12345)
        assert result == {"id": 1, "name": "Рекс"}

    @patch("bot.api_client.get_client")
    async def test_get_pet_not_found(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(status_code=404)
        mock_get_client.return_value = mock_client

        result = await api_client.get_pet(999, 12345)
        assert result is None

    @patch("bot.api_client.get_client")
    async def test_create_pet(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(json_data={"id": 1, "name": "Рекс"})
        mock_get_client.return_value = mock_client

        result = await api_client.create_pet(12345, "Рекс", "собака")
        assert result["name"] == "Рекс"

    @patch("bot.api_client.get_client")
    async def test_update_pet(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.patch.return_value = _mock_response(json_data={"id": 1, "name": "Рексик"})
        mock_get_client.return_value = mock_client

        result = await api_client.update_pet(1, 12345, name="Рексик")
        assert result["name"] == "Рексик"

    @patch("bot.api_client.get_client")
    async def test_update_pet_not_found(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.patch.return_value = _mock_response(status_code=404)
        mock_get_client.return_value = mock_client

        result = await api_client.update_pet(999, 12345, name="X")
        assert result is None

    @patch("bot.api_client.get_client")
    async def test_delete_pet(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.delete.return_value = _mock_response(status_code=204)
        mock_get_client.return_value = mock_client

        result = await api_client.delete_pet(1, 12345)
        assert result is True

    @patch("bot.api_client.get_client")
    async def test_delete_pet_not_found(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.delete.return_value = _mock_response(status_code=404)
        mock_get_client.return_value = mock_client

        result = await api_client.delete_pet(999, 12345)
        assert result is False

    @patch("bot.api_client.get_client")
    async def test_get_pet_count(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"count": 3})
        mock_get_client.return_value = mock_client

        result = await api_client.get_pet_count(12345)
        assert result == 3

    @patch("bot.api_client.get_client")
    async def test_get_pet_stats(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"total_weight_records": 5})
        mock_get_client.return_value = mock_client

        result = await api_client.get_pet_stats(1, 12345)
        assert result["total_weight_records"] == 5

    @patch("bot.api_client.get_client")
    async def test_get_pet_export(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"text": "export data"})
        mock_get_client.return_value = mock_client

        result = await api_client.get_pet_export(1, 12345)
        assert result["text"] == "export data"


class TestRemindersApi:
    @patch("bot.api_client.get_client")
    async def test_list_reminders(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data=[{"id": 1}])
        mock_get_client.return_value = mock_client

        result = await api_client.list_reminders(12345)
        assert len(result) == 1

    @patch("bot.api_client.get_client")
    async def test_get_reminder_found(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"id": 1, "title": "Feed"})
        mock_get_client.return_value = mock_client

        result = await api_client.get_reminder(1, 12345)
        assert result["title"] == "Feed"

    @patch("bot.api_client.get_client")
    async def test_get_reminder_not_found(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(status_code=404)
        mock_get_client.return_value = mock_client

        result = await api_client.get_reminder(999, 12345)
        assert result is None

    @patch("bot.api_client.get_client")
    async def test_delete_reminder(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.delete.return_value = _mock_response(status_code=204)
        mock_get_client.return_value = mock_client

        result = await api_client.delete_reminder(1, 12345)
        assert result is True


class TestMedicalApi:
    @patch("bot.api_client.get_client")
    async def test_list_vaccinations(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data=[])
        mock_get_client.return_value = mock_client

        result = await api_client.list_vaccinations(1, 12345)
        assert result == []

    @patch("bot.api_client.get_client")
    async def test_delete_vaccination(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.delete.return_value = _mock_response(status_code=204)
        mock_get_client.return_value = mock_client

        assert await api_client.delete_vaccination(1, 12345) is True

    @patch("bot.api_client.get_client")
    async def test_list_vet_visits(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data=[])
        mock_get_client.return_value = mock_client

        result = await api_client.list_vet_visits(1, 12345)
        assert result == []

    @patch("bot.api_client.get_client")
    async def test_delete_vet_visit(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.delete.return_value = _mock_response(status_code=204)
        mock_get_client.return_value = mock_client

        assert await api_client.delete_vet_visit(1, 12345) is True

    @patch("bot.api_client.get_client")
    async def test_list_weight_records(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data=[])
        mock_get_client.return_value = mock_client

        result = await api_client.list_weight_records(1, 12345)
        assert result == []

    @patch("bot.api_client.get_client")
    async def test_list_documents(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data=[])
        mock_get_client.return_value = mock_client

        result = await api_client.list_documents(1, 12345)
        assert result == []

    @patch("bot.api_client.get_client")
    async def test_delete_document(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.delete.return_value = _mock_response(status_code=204)
        mock_get_client.return_value = mock_client

        assert await api_client.delete_document(1, 12345) is True

    @patch("bot.api_client.get_client")
    async def test_get_calendar(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"events": []})
        mock_get_client.return_value = mock_client

        result = await api_client.get_calendar(12345)
        assert "events" in result


class TestFoodApi:
    @patch("bot.api_client.get_client")
    async def test_list_food_entries(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data=[])
        mock_get_client.return_value = mock_client

        result = await api_client.list_food_entries(1, 12345)
        assert result == []

    @patch("bot.api_client.get_client")
    async def test_delete_food_entry(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.delete.return_value = _mock_response(status_code=204)
        mock_get_client.return_value = mock_client

        assert await api_client.delete_food_entry(1, 12345) is True

    @patch("bot.api_client.get_client")
    async def test_list_water_entries(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data=[])
        mock_get_client.return_value = mock_client

        result = await api_client.list_water_entries(1, 12345)
        assert result == []

    @patch("bot.api_client.get_client")
    async def test_delete_water_entry(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.delete.return_value = _mock_response(status_code=204)
        mock_get_client.return_value = mock_client

        assert await api_client.delete_water_entry(1, 12345) is True

    @patch("bot.api_client.get_client")
    async def test_list_allergies(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data=[])
        mock_get_client.return_value = mock_client

        result = await api_client.list_allergies(1, 12345)
        assert result == []

    @patch("bot.api_client.get_client")
    async def test_delete_allergy(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.delete.return_value = _mock_response(status_code=204)
        mock_get_client.return_value = mock_client

        assert await api_client.delete_allergy(1, 12345) is True


class TestSubscriptionApi:
    @patch("bot.api_client.get_client")
    async def test_get_subscription_status(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"is_premium": True})
        mock_get_client.return_value = mock_client

        result = await api_client.get_subscription_status(12345)
        assert result["is_premium"] is True

    @patch("bot.api_client.get_client")
    async def test_check_premium(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"is_premium": False})
        mock_get_client.return_value = mock_client

        result = await api_client.check_premium(12345)
        assert result is False

    @patch("bot.api_client.get_client")
    async def test_get_plan_tier(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"plan_tier": "pro"})
        mock_get_client.return_value = mock_client

        result = await api_client.get_plan_tier(12345)
        assert result == "pro"

    @patch("bot.api_client.get_client")
    async def test_check_ai_limit(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(json_data={"allowed": True, "remaining": 5})
        mock_get_client.return_value = mock_client

        allowed, remaining = await api_client.check_ai_limit(12345)
        assert allowed is True
        assert remaining == 5

    @patch("bot.api_client.get_client")
    async def test_check_pet_limit(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"allowed": True, "remaining": 3})
        mock_get_client.return_value = mock_client

        allowed, remaining = await api_client.check_pet_limit(12345)
        assert allowed is True

    @patch("bot.api_client.get_client")
    async def test_grant_premium(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(json_data={"ok": True})
        mock_get_client.return_value = mock_client

        result = await api_client.grant_premium(12345, 30)
        assert result is True

    @patch("bot.api_client.get_client")
    async def test_revoke_premium(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(json_data={"ok": True})
        mock_get_client.return_value = mock_client

        result = await api_client.revoke_premium(12345)
        assert result is True

    @patch("bot.api_client.get_client")
    async def test_check_feature_permission(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"allowed": True})
        mock_get_client.return_value = mock_client

        result = await api_client.check_feature_permission(12345, "voice_notes")
        assert result is True

    @patch("bot.api_client.get_client")
    async def test_toggle_weather_notify(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(json_data={"weather_notify": True})
        mock_get_client.return_value = mock_client

        result = await api_client.toggle_weather_notify(12345)
        assert result["weather_notify"] is True


class TestAnalyticsApi:
    @patch("bot.api_client.get_client")
    async def test_track_event_success(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(json_data={})
        mock_get_client.return_value = mock_client

        await api_client.track_event(12345, "start")
        mock_client.post.assert_awaited_once()

    @patch("bot.api_client.get_client")
    async def test_track_event_error_swallowed(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("fail")
        mock_get_client.return_value = mock_client

        await api_client.track_event(12345, "start")

    @patch("bot.api_client.get_client")
    async def test_track_user_activity(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(json_data={})
        mock_get_client.return_value = mock_client

        await api_client.track_user_activity(12345)
        mock_client.post.assert_awaited_once()

    @patch("bot.api_client.get_client")
    async def test_track_user_activity_error_swallowed(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("fail")
        mock_get_client.return_value = mock_client

        await api_client.track_user_activity(12345)

    @patch("bot.api_client.get_client")
    async def test_get_funnel_report(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"report": "stats"})
        mock_get_client.return_value = mock_client

        result = await api_client.get_funnel_report()
        assert result == "stats"


class TestServicesApi:
    @patch("bot.api_client.get_client")
    async def test_is_ai_operational(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"operational": True})
        mock_get_client.return_value = mock_client

        result = await api_client.is_ai_operational()
        assert result is True

    @patch("bot.api_client.get_client")
    async def test_is_card_payment_operational(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"operational": False})
        mock_get_client.return_value = mock_client

        result = await api_client.is_card_payment_operational()
        assert result is False

    @patch("bot.api_client.get_client")
    async def test_get_weather(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"data": {"temp_c": 20}})
        mock_get_client.return_value = mock_client

        result = await api_client.get_weather("Москва")
        assert result["temp_c"] == 20

    @patch("bot.api_client.get_client")
    async def test_get_weather_alert(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(json_data={"alert": "Жара!"})
        mock_get_client.return_value = mock_client

        result = await api_client.get_weather_alert({"temp_c": 35}, "собака")
        assert result == "Жара!"

    @patch("bot.api_client.get_client")
    async def test_get_norms(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"text": "Нормы"})
        mock_get_client.return_value = mock_client

        result = await api_client.get_norms(12345)
        assert result["text"] == "Нормы"

    @patch("bot.api_client.get_client")
    async def test_get_feeding_chart(self, mock_get_client):
        mock_client = AsyncMock()
        img_b64 = base64.b64encode(b"PNG_DATA").decode()
        mock_client.post.return_value = _mock_response(json_data={"image": img_b64})
        mock_get_client.return_value = mock_client

        result = await api_client.get_feeding_chart("Рекс", [])
        assert result == b"PNG_DATA"

    @patch("bot.api_client.get_client")
    async def test_get_feeding_chart_none(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(json_data={"image": None})
        mock_get_client.return_value = mock_client

        result = await api_client.get_feeding_chart("Рекс", [])
        assert result is None

    @patch("bot.api_client.get_client")
    async def test_get_timeline_chart(self, mock_get_client):
        mock_client = AsyncMock()
        img_b64 = base64.b64encode(b"DATA").decode()
        mock_client.post.return_value = _mock_response(json_data={"image": img_b64})
        mock_get_client.return_value = mock_client

        result = await api_client.get_timeline_chart("Рекс", [])
        assert result == b"DATA"


class TestVoiceNotesApi:
    @patch("bot.api_client.get_client")
    async def test_list_voice_notes(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data=[])
        mock_get_client.return_value = mock_client

        result = await api_client.list_voice_notes(12345)
        assert result == []

    @patch("bot.api_client.get_client")
    async def test_create_voice_note(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(json_data={"id": 1})
        mock_get_client.return_value = mock_client

        result = await api_client.create_voice_note(1, 12345, "file_id")
        assert result["id"] == 1


class TestPaymentsApi:
    @patch("bot.api_client.get_client")
    async def test_mark_payment_processed(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(json_data={"ok": True, "duplicate": False})
        mock_get_client.return_value = mock_client

        ok, dup = await api_client.mark_payment_processed("stars", "pay_1", 12345, "pro")
        assert ok is True
        assert dup is False

    @patch("bot.api_client.get_client")
    async def test_get_pending_payment(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data={"id": "pay_1"})
        mock_get_client.return_value = mock_client

        result = await api_client.get_pending_payment("stars", "pay_1")
        assert result["id"] == "pay_1"

    @patch("bot.api_client.get_client")
    async def test_list_pending_payments(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(json_data=[])
        mock_get_client.return_value = mock_client

        result = await api_client.list_pending_payments("stars")
        assert result == []
