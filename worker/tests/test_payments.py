"""Tests for worker.tasks.payments reconciliation."""

from types import SimpleNamespace

import pytest
from worker.tasks import payments


@pytest.mark.asyncio
async def test_reconcile_pending_payments_skips_without_yookassa_credentials(monkeypatch):
    monkeypatch.setattr(
        payments,
        "get_settings",
        lambda: SimpleNamespace(YOOKASSA_SHOP_ID="", YOOKASSA_SECRET_KEY=""),
    )

    await payments.reconcile_pending_payments()


@pytest.mark.asyncio
async def test_reconcile_card_payment_grants_subscription(monkeypatch):
    calls: list[tuple] = []

    amount = SimpleNamespace(value="199.00", currency="RUB")
    payment = SimpleNamespace(
        status="succeeded",
        metadata={"user_id": "123", "plan_key": "basic"},
        amount=amount,
    )

    monkeypatch.setattr(payments.YooPayment, "find_one", lambda payment_id: payment)

    async def mark_payment_processed(**kwargs):
        calls.append(("mark", kwargs))
        return {"success": True, "duplicate": False}

    async def grant_premium(user_id: int, days: int, plan_tier: str):
        calls.append(("grant", user_id, days, plan_tier))
        return True

    async def update_pending_payment(provider: str, payment_id: str, status: str, **kwargs):
        calls.append(("update", provider, payment_id, status, kwargs))

    async def track_event(user_id: int, event_name: str, source: str = "", payload: dict | None = None):
        calls.append(("track", user_id, event_name, source, payload))

    async def get_subscription_status(user_id: int):
        calls.append(("status", user_id))
        return {"premium_until_str": "01.07.2026"}

    async def send_success_message(user_id: int, plan_name: str, until: str):
        calls.append(("send", user_id, plan_name, until))

    monkeypatch.setattr(payments.api_client, "mark_payment_processed", mark_payment_processed)
    monkeypatch.setattr(payments.api_client, "grant_premium", grant_premium)
    monkeypatch.setattr(payments.api_client, "update_pending_payment", update_pending_payment)
    monkeypatch.setattr(payments.api_client, "track_event", track_event)
    monkeypatch.setattr(payments.api_client, "get_subscription_status", get_subscription_status)
    monkeypatch.setattr(payments, "_send_success_message", send_success_message)

    status, details = await payments._reconcile_card_payment(
        "pay_1",
        expected_user_id=123,
        expected_plan_key="basic",
    )

    assert status == "succeeded"
    assert details == "01.07.2026"
    assert ("grant", 123, 30, "basic") in calls
    assert ("send", 123, "🐾 Базовый", "01.07.2026") in calls


@pytest.mark.asyncio
async def test_reconcile_card_payment_rejects_amount_mismatch(monkeypatch):
    calls: list[tuple] = []
    amount = SimpleNamespace(value="1.00", currency="RUB")
    payment = SimpleNamespace(status="succeeded", metadata={"user_id": "123", "plan_key": "basic"}, amount=amount)

    monkeypatch.setattr(payments.YooPayment, "find_one", lambda payment_id: payment)

    async def update_pending_payment(provider: str, payment_id: str, status: str, **kwargs):
        calls.append((provider, payment_id, status, kwargs))

    monkeypatch.setattr(payments.api_client, "update_pending_payment", update_pending_payment)

    status, details = await payments._reconcile_card_payment(
        "pay_1",
        expected_user_id=None,
        expected_plan_key="basic",
    )

    assert status == "error"
    assert details == "amount_mismatch"
    assert calls[0][2] == "error"
