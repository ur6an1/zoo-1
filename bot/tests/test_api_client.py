"""Tests for bot/bot/api_client.py — HTTP client layer."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import bot.api_client as ac
import httpx
import pytest


@pytest.fixture(autouse=True)
async def _reset_client():
    """Reset the global client before each test."""
    ac._client = None
    yield
    if ac._client and not ac._client.is_closed:
        await ac._client.aclose()
    ac._client = None


def _mock_response(json_data=None, status_code=200) -> AsyncMock:
    resp = AsyncMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status = AsyncMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=AsyncMock(), response=resp,
        )
    return resp


def _mock_client(**overrides) -> AsyncMock:
    c = AsyncMock(spec=httpx.AsyncClient)
    c.is_closed = False
    for method in ("get", "post", "patch", "delete", "put"):
        getattr(c, method).return_value = _mock_response()
    for k, v in overrides.items():
        getattr(c, k).return_value = v
    return c


# ── lifecycle ──


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_get_client_creates_new(self):
        client = await ac.get_client()
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_get_client_reuses(self):
        c1 = await ac.get_client()
        c2 = await ac.get_client()
        assert c1 is c2

    @pytest.mark.asyncio
    async def test_init(self):
        await ac.init()
        assert ac._client is not None

    @pytest.mark.asyncio
    async def test_close(self):
        await ac.init()
        await ac.close()
        assert ac._client is None

    @pytest.mark.asyncio
    async def test_close_client(self):
        await ac.init()
        await ac.close_client()
        assert ac._client is None

    @pytest.mark.asyncio
    async def test_close_client_when_none(self):
        ac._client = None
        await ac.close_client()
        assert ac._client is None


# ── PETS ──


class TestPetsApi:
    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_list_pets(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response([{"id": 1, "name": "Rex"}]))
        mock_gc.return_value = c
        result = await ac.list_pets(42)
        c.get.assert_awaited_once_with("/pets/by_user/42")
        assert result == [{"id": 1, "name": "Rex"}]

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_pet_found(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.get_pet(1, 42)
        assert result == {"id": 1}

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_pet_not_found(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response(status_code=404))
        mock_gc.return_value = c
        result = await ac.get_pet(1, 42)
        assert result is None

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_pet_minimal(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1, "name": "Rex"}))
        mock_gc.return_value = c
        result = await ac.create_pet(42, "Rex", "Собака")
        assert result["name"] == "Rex"

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_pet_full(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_pet(
            42, "Rex", "Собака", breed="Лабрадор",
            birth_date=date(2020, 1, 1), weight=25.5, photo_file_id="abc",
        )
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_update_pet(self, mock_gc: AsyncMock):
        c = _mock_client(patch=_mock_response({"id": 1, "name": "Max"}))
        mock_gc.return_value = c
        result = await ac.update_pet(1, 42, name="Max")
        assert result["name"] == "Max"

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_update_pet_not_found(self, mock_gc: AsyncMock):
        c = _mock_client(patch=_mock_response(status_code=404))
        mock_gc.return_value = c
        result = await ac.update_pet(1, 42, name="Max")
        assert result is None

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_delete_pet(self, mock_gc: AsyncMock):
        c = _mock_client(delete=_mock_response(status_code=204))
        mock_gc.return_value = c
        assert await ac.delete_pet(1, 42) is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_pet_stats(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"pet": {}, "counts": {}}))
        mock_gc.return_value = c
        result = await ac.get_pet_stats(1, 42)
        assert "pet" in result

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_pet_export(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"pet": {}}))
        mock_gc.return_value = c
        result = await ac.get_pet_export(1, 42)
        assert result is not None

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_pet_export_not_found(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response(status_code=404))
        mock_gc.return_value = c
        result = await ac.get_pet_export(1, 42)
        assert result is None

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_pet_count(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"count": 3}))
        mock_gc.return_value = c
        assert await ac.get_pet_count(42) == 3


# ── REMINDERS ──


class TestRemindersApi:
    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_list_reminders(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response([{"id": 1}]))
        mock_gc.return_value = c
        result = await ac.list_reminders(42)
        assert len(result) == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_reminder(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"id": 1, "title": "Feed"}))
        mock_gc.return_value = c
        result = await ac.get_reminder(1, 42)
        assert result["title"] == "Feed"

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_reminder_not_found(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response(status_code=404))
        mock_gc.return_value = c
        assert await ac.get_reminder(1, 42) is None

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_reminder(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_reminder(
            42, 1, "Feed", remind_at=datetime(2026, 1, 1, 9, 0),
        )
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_reminder_no_datetime(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_reminder(42, 1, "Walk")
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_pause_reminder(self, mock_gc: AsyncMock):
        c = _mock_client(patch=_mock_response({"id": 1, "is_active": False}))
        mock_gc.return_value = c
        result = await ac.pause_reminder(1, 42)
        assert result["is_active"] is False

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_resume_reminder(self, mock_gc: AsyncMock):
        c = _mock_client(patch=_mock_response({"id": 1, "is_active": True}))
        mock_gc.return_value = c
        result = await ac.resume_reminder(1, 42)
        assert result["is_active"] is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_delete_reminder(self, mock_gc: AsyncMock):
        c = _mock_client(delete=_mock_response(status_code=204))
        mock_gc.return_value = c
        assert await ac.delete_reminder(1, 42) is True


# ── MEDICAL ──


class TestMedicalApi:
    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_list_vaccinations(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response([]))
        mock_gc.return_value = c
        assert await ac.list_vaccinations(1, 42) == []

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_vaccination(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_vaccination(42, 1, "Rabies", date(2026, 1, 1))
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_vaccination_with_next(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_vaccination(
            42, 1, "Rabies", date(2026, 1, 1), next_date=date(2027, 1, 1),
        )
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_delete_vaccination(self, mock_gc: AsyncMock):
        c = _mock_client(delete=_mock_response(status_code=204))
        mock_gc.return_value = c
        assert await ac.delete_vaccination(1, 42) is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_list_vet_visits(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response([]))
        mock_gc.return_value = c
        assert await ac.list_vet_visits(1, 42) == []

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_vet_visit(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_vet_visit(42, 1, date(2026, 1, 1))
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_delete_vet_visit(self, mock_gc: AsyncMock):
        c = _mock_client(delete=_mock_response(status_code=204))
        mock_gc.return_value = c
        assert await ac.delete_vet_visit(1, 42) is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_list_weight_records(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response([]))
        mock_gc.return_value = c
        assert await ac.list_weight_records(1, 42) == []

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_weight_record(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_weight_record(42, 1, 5.5)
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_list_documents(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response([]))
        mock_gc.return_value = c
        assert await ac.list_documents(1, 42) == []

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_document(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_document(42, 1, "passport", "file_abc")
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_delete_document(self, mock_gc: AsyncMock):
        c = _mock_client(delete=_mock_response(status_code=204))
        mock_gc.return_value = c
        assert await ac.delete_document(1, 42) is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_calendar(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"events": []}))
        mock_gc.return_value = c
        result = await ac.get_calendar(42)
        assert "events" in result


# ── FOOD / WATER / ALLERGIES ──


class TestFoodApi:
    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_list_food_entries(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response([]))
        mock_gc.return_value = c
        assert await ac.list_food_entries(1, 42) == []

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_food_entry(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_food_entry(42, 1, "Chicken")
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_food_entry_with_grams(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_food_entry(42, 1, "Chicken", portion_grams=100.0)
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_delete_food_entry(self, mock_gc: AsyncMock):
        c = _mock_client(delete=_mock_response(status_code=204))
        mock_gc.return_value = c
        assert await ac.delete_food_entry(1, 42) is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_clear_food_entries(self, mock_gc: AsyncMock):
        c = _mock_client(delete=_mock_response())
        mock_gc.return_value = c
        await ac.clear_food_entries(1, 42)
        c.delete.assert_awaited_once()

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_list_water_entries(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response([]))
        mock_gc.return_value = c
        assert await ac.list_water_entries(1, 42) == []

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_water_entry(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_water_entry(42, 1, 250)
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_delete_water_entry(self, mock_gc: AsyncMock):
        c = _mock_client(delete=_mock_response(status_code=204))
        mock_gc.return_value = c
        assert await ac.delete_water_entry(1, 42) is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_clear_water_entries(self, mock_gc: AsyncMock):
        c = _mock_client(delete=_mock_response())
        mock_gc.return_value = c
        await ac.clear_water_entries(1, 42)
        c.delete.assert_awaited_once()

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_list_allergies(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response([]))
        mock_gc.return_value = c
        assert await ac.list_allergies(1, 42) == []

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_list_allergies_by_user(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response([]))
        mock_gc.return_value = c
        assert await ac.list_allergies_by_user(42) == []

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_allergy(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_allergy(42, 1, "Chicken")
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_delete_allergy(self, mock_gc: AsyncMock):
        c = _mock_client(delete=_mock_response(status_code=204))
        mock_gc.return_value = c
        assert await ac.delete_allergy(1, 42) is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_daily_summary(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"summary": {}}))
        mock_gc.return_value = c
        result = await ac.get_daily_summary(1, 42)
        assert "summary" in result


# ── SUBSCRIPTIONS ──


class TestSubscriptionsApi:
    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_subscription_status(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"is_premium": False}))
        mock_gc.return_value = c
        result = await ac.get_subscription_status(42)
        assert result["is_premium"] is False

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_user_settings(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"city": ""}))
        mock_gc.return_value = c
        result = await ac.get_user_settings(42)
        assert "city" in result

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_plan_tier(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"plan_tier": "free"}))
        mock_gc.return_value = c
        assert await ac.get_plan_tier(42) == "free"

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_check_premium(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"is_premium": True}))
        mock_gc.return_value = c
        assert await ac.check_premium(42) is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_check_ai_limit(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"allowed": True, "remaining": 5}))
        mock_gc.return_value = c
        allowed, remaining = await ac.check_ai_limit(42)
        assert allowed is True
        assert remaining == 5

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_refund_ai_limit(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response())
        mock_gc.return_value = c
        await ac.refund_ai_limit(42)
        c.post.assert_awaited_once()

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_check_pet_limit(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"allowed": True, "remaining": 3}))
        mock_gc.return_value = c
        allowed, remaining = await ac.check_pet_limit(42)
        assert allowed is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_grant_premium(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"ok": True}))
        mock_gc.return_value = c
        assert await ac.grant_premium(42, 30) is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_revoke_premium(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"ok": True}))
        mock_gc.return_value = c
        assert await ac.revoke_premium(42) is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_can_use_pdf_export(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"allowed": True}))
        mock_gc.return_value = c
        assert await ac.can_use_pdf_export(42) is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_can_use_weather(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"allowed": False}))
        mock_gc.return_value = c
        assert await ac.can_use_weather(42) is False

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_can_use_voice_notes(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"allowed": True}))
        mock_gc.return_value = c
        assert await ac.can_use_voice_notes(42) is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_update_user_settings(self, mock_gc: AsyncMock):
        c = _mock_client(patch=_mock_response())
        mock_gc.return_value = c
        await ac.update_user_settings(42, city="Moscow")
        c.patch.assert_awaited_once()


# ── PAYMENTS ──


class TestPaymentsApi:
    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_mark_payment_processed(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"ok": True, "duplicate": False}))
        mock_gc.return_value = c
        ok, dup = await ac.mark_payment_processed("stars", "p1", 42, "basic")
        assert ok is True
        assert dup is False

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_upsert_pending_payment(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response())
        mock_gc.return_value = c
        await ac.upsert_pending_payment("yookassa", "p1", 42, "basic")
        c.post.assert_awaited_once()

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_update_pending_payment(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response())
        mock_gc.return_value = c
        await ac.update_pending_payment("yookassa", "p1", "succeeded")
        c.post.assert_awaited_once()

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_pending_payment(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"payment_id": "p1"}))
        mock_gc.return_value = c
        result = await ac.get_pending_payment("yookassa", "p1")
        assert result["payment_id"] == "p1"

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_yookassa_payment(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"ok": True, "payment_id": "p1"}))
        mock_gc.return_value = c
        result = await ac.create_yookassa_payment(
            "basic", 199, "Базовый", 42, "https://t.me/bot",
        )
        assert result["ok"] is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_reconcile_yookassa_payment(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"ok": True, "status": "succeeded"}))
        mock_gc.return_value = c
        result = await ac.reconcile_yookassa_payment("p1")
        assert result["status"] == "succeeded"

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_list_pending_payments(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response([]))
        mock_gc.return_value = c
        assert await ac.list_pending_payments("yookassa") == []


# ── ANALYTICS ──


class TestAnalyticsApi:
    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_track_event(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response())
        mock_gc.return_value = c
        await ac.track_event(42, "test_event")
        c.post.assert_awaited_once()

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_track_event_swallows_errors(self, mock_gc: AsyncMock):
        c = _mock_client()
        c.post.side_effect = Exception("network error")
        mock_gc.return_value = c
        await ac.track_event(42, "test_event")

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_track_user_activity(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response())
        mock_gc.return_value = c
        await ac.track_user_activity(42, source="test")
        c.post.assert_awaited_once()

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_track_user_activity_swallows_errors(self, mock_gc: AsyncMock):
        c = _mock_client()
        c.post.side_effect = Exception("network error")
        mock_gc.return_value = c
        await ac.track_user_activity(42)

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_funnel_report(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"report": "data"}))
        mock_gc.return_value = c
        assert await ac.get_funnel_report() == "data"


# ── SERVICES ──


class TestServicesApi:
    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_is_ai_operational(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"operational": True}))
        mock_gc.return_value = c
        assert await ac.is_ai_operational() is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_is_card_payment_operational(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"operational": True}))
        mock_gc.return_value = c
        assert await ac.is_card_payment_operational() is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_weather(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"data": {"temp": 20}}))
        mock_gc.return_value = c
        result = await ac.get_weather("Moscow")
        assert result["temp"] == 20

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_weather_alert(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"alert": "Stay inside"}))
        mock_gc.return_value = c
        result = await ac.get_weather_alert({}, "cat")
        assert result == "Stay inside"

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_food_norm(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"norm": 100}))
        mock_gc.return_value = c
        result = await ac.get_food_norm("cat")
        assert "norm" in result

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_progress_bar(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"bar": "████░░"}))
        mock_gc.return_value = c
        result = await ac.get_progress_bar(4, 10)
        assert "█" in result

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_feeding_chart(self, mock_gc: AsyncMock):
        import base64
        img_b64 = base64.b64encode(b"PNG").decode()
        c = _mock_client(post=_mock_response({"image": img_b64}))
        mock_gc.return_value = c
        result = await ac.get_feeding_chart("Rex", [])
        assert result == b"PNG"

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_feeding_chart_none(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"image": None}))
        mock_gc.return_value = c
        result = await ac.get_feeding_chart("Rex", [])
        assert result is None

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_timeline_chart(self, mock_gc: AsyncMock):
        import base64
        img_b64 = base64.b64encode(b"PNG").decode()
        c = _mock_client(post=_mock_response({"image": img_b64}))
        mock_gc.return_value = c
        result = await ac.get_timeline_chart("Rex", [])
        assert result == b"PNG"

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_list_voice_notes(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response([]))
        mock_gc.return_value = c
        assert await ac.list_voice_notes(42) == []

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_create_voice_note(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"id": 1}))
        mock_gc.return_value = c
        result = await ac.create_voice_note(1, 42, "file_abc")
        assert result["id"] == 1

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_delete_voice_note(self, mock_gc: AsyncMock):
        c = _mock_client(delete=_mock_response())
        mock_gc.return_value = c
        await ac.delete_voice_note(1, 42)
        c.delete.assert_awaited_once()

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_check_feature_permission(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"allowed": True}))
        mock_gc.return_value = c
        assert await ac.check_feature_permission(42, "weather") is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_toggle_weather_notify(self, mock_gc: AsyncMock):
        c = _mock_client(post=_mock_response({"weather_notify": True}))
        mock_gc.return_value = c
        result = await ac.toggle_weather_notify(42)
        assert result["weather_notify"] is True

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_medical_calendar(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"events": []}))
        mock_gc.return_value = c
        result = await ac.get_medical_calendar(42)
        assert "events" in result

    @pytest.mark.asyncio
    @patch.object(ac, "get_client")
    async def test_get_norms(self, mock_gc: AsyncMock):
        c = _mock_client(get=_mock_response({"norms": {}}))
        mock_gc.return_value = c
        result = await ac.get_norms(42)
        assert "norms" in result
