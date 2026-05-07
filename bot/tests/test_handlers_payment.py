"""Tests for bot/bot/handlers/payment.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.handlers.payment import (
    _normalize_money_value,
    _payment_methods_note,
    _reconcile_card_payment,
    card_unavailable,
    check_card,
    choose_plan,
    pay_card,
    pay_stars,
    payment_methods_kb,
    payment_plans_kb,
    pre_checkout,
    reconcile_pending_card_payments,
    show_plans_cb,
    successful_payment,
)

# ── helpers ──


def _make_callback(user_id: int = 1, data: str = "") -> MagicMock:
    cb = AsyncMock()
    cb.from_user = MagicMock(id=user_id)
    cb.data = data
    cb.bot = AsyncMock()
    cb.bot.get_me = AsyncMock(return_value=MagicMock(username="testbot"))
    cb.message = AsyncMock()
    cb.message.chat = MagicMock(id=1)
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _make_message(user_id: int = 1) -> MagicMock:
    msg = AsyncMock()
    msg.from_user = MagicMock(id=user_id)
    msg.answer = AsyncMock()
    return msg


def _make_pre_checkout(user_id: int = 1, payload: str = "") -> MagicMock:
    pcq = AsyncMock()
    pcq.from_user = MagicMock(id=user_id)
    pcq.invoice_payload = payload
    pcq.answer = AsyncMock()
    return pcq


# ── pure function tests ──


class TestNormalizeMoney:
    def test_none(self):
        assert _normalize_money_value(None) == ""

    def test_empty(self):
        assert _normalize_money_value("") == ""

    def test_int(self):
        assert _normalize_money_value(199) == "199.00"

    def test_float(self):
        assert _normalize_money_value(299.0) == "299.00"

    def test_string(self):
        assert _normalize_money_value("199") == "199.00"

    def test_invalid(self):
        assert _normalize_money_value("abc") == "abc"


class TestPaymentMethodsNote:
    def test_card_available(self):
        note = _payment_methods_note(True)
        assert "картой" in note
        assert "Stars" in note

    def test_card_unavailable(self):
        note = _payment_methods_note(False)
        assert "Stars" in note
        assert "отключена" in note


class TestPaymentKbs:
    def test_payment_plans_kb(self):
        kb = payment_plans_kb()
        assert len(kb.inline_keyboard) == 3
        assert "Базовый" in kb.inline_keyboard[0][0].text
        assert "PRO" in kb.inline_keyboard[1][0].text

    def test_payment_methods_kb_with_card(self):
        kb = payment_methods_kb("basic", card_available=True)
        texts = [row[0].text for row in kb.inline_keyboard]
        assert any("карта" in t.lower() or "💳" in t for t in texts)
        assert any("Stars" in t for t in texts)

    def test_payment_methods_kb_without_card(self):
        kb = payment_methods_kb("basic", card_available=False)
        texts = [row[0].text for row in kb.inline_keyboard]
        assert not any("💳" in t for t in texts)
        assert any("Stars" in t for t in texts)


# ── reconcile tests ──


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_reconcile_card_payment_backend_error(mock_api: MagicMock):
    mock_api.reconcile_yookassa_payment = AsyncMock(side_effect=Exception("timeout"))
    mock_api.track_event = AsyncMock()

    status, msg = await _reconcile_card_payment(
        "pay_123", expected_user_id=1, expected_plan_key="basic",
    )
    assert status == "error"
    assert "проверить" in msg.lower() or "позже" in msg.lower()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_reconcile_card_payment_not_ok(mock_api: MagicMock):
    mock_api.reconcile_yookassa_payment = AsyncMock(
        return_value={"ok": False, "error": "user_mismatch"}
    )
    mock_api.update_pending_payment = AsyncMock()
    mock_api.track_event = AsyncMock()

    status, msg = await _reconcile_card_payment(
        "pay_123", expected_user_id=1, expected_plan_key="basic",
    )
    assert status == "error"
    assert "другому пользователю" in msg


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_reconcile_card_payment_pending(mock_api: MagicMock):
    mock_api.reconcile_yookassa_payment = AsyncMock(
        return_value={"ok": True, "status": "pending"}
    )
    mock_api.update_pending_payment = AsyncMock()

    status, msg = await _reconcile_card_payment(
        "pay_123", expected_user_id=1, expected_plan_key="basic",
    )
    assert status == "pending"


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_reconcile_card_payment_canceled(mock_api: MagicMock):
    mock_api.reconcile_yookassa_payment = AsyncMock(
        return_value={"ok": True, "status": "canceled"}
    )
    mock_api.update_pending_payment = AsyncMock()
    mock_api.track_event = AsyncMock()

    status, msg = await _reconcile_card_payment(
        "pay_123", expected_user_id=1, expected_plan_key="basic",
    )
    assert status == "canceled"
    assert "отменён" in msg.lower()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_reconcile_card_payment_unknown_plan(mock_api: MagicMock):
    mock_api.reconcile_yookassa_payment = AsyncMock(
        return_value={
            "ok": True, "status": "succeeded",
            "metadata_user_id": "1", "metadata_plan_key": "nonexistent",
        }
    )
    mock_api.update_pending_payment = AsyncMock()
    mock_api.track_event = AsyncMock()

    status, msg = await _reconcile_card_payment(
        "pay_123", expected_user_id=1, expected_plan_key="basic",
    )
    assert status == "error"
    assert "тариф" in msg.lower()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_reconcile_card_payment_succeeded(mock_api: MagicMock):
    mock_api.reconcile_yookassa_payment = AsyncMock(
        return_value={
            "ok": True, "status": "succeeded",
            "metadata_user_id": "1", "metadata_plan_key": "basic",
        }
    )
    mock_api.mark_payment_processed = AsyncMock(return_value={"success": True})
    mock_api.grant_premium = AsyncMock()
    mock_api.update_pending_payment = AsyncMock()
    mock_api.track_event = AsyncMock()
    mock_api.get_subscription_status = AsyncMock(
        return_value={"premium_until_str": "01.01.2027"}
    )

    status, until = await _reconcile_card_payment(
        "pay_123", expected_user_id=1, expected_plan_key="basic",
    )
    assert status == "succeeded"
    assert "2027" in until
    mock_api.grant_premium.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_reconcile_card_payment_already_processed(mock_api: MagicMock):
    mock_api.reconcile_yookassa_payment = AsyncMock(
        return_value={
            "ok": True, "status": "succeeded",
            "metadata_user_id": "1", "metadata_plan_key": "basic",
        }
    )
    mock_api.mark_payment_processed = AsyncMock(return_value={"success": False})
    mock_api.update_pending_payment = AsyncMock()
    mock_api.get_subscription_status = AsyncMock(
        return_value={"premium_until_str": "01.01.2027"}
    )

    status, until = await _reconcile_card_payment(
        "pay_123", expected_user_id=1, expected_plan_key="basic",
    )
    assert status == "already_processed"


# ── reconcile_pending_card_payments ──


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
@patch("bot.handlers.payment._reconcile_card_payment", new_callable=AsyncMock)
async def test_reconcile_pending_skips_when_unavailable(
    mock_reconcile: AsyncMock, mock_api: MagicMock,
):
    mock_api.is_card_payment_operational = AsyncMock(return_value=False)
    bot = AsyncMock()

    await reconcile_pending_card_payments(bot)

    mock_reconcile.assert_not_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
@patch("bot.handlers.payment._reconcile_card_payment", new_callable=AsyncMock)
async def test_reconcile_pending_processes_payments(
    mock_reconcile: AsyncMock, mock_api: MagicMock,
):
    mock_api.is_card_payment_operational = AsyncMock(return_value=True)
    mock_api.list_pending_payments = AsyncMock(
        return_value=[
            {"payment_id": "p1", "user_id": 1, "plan_key": "basic"},
            {"payment_id": "p2", "user_id": 2, "plan_key": "pro"},
        ]
    )
    mock_reconcile.return_value = ("succeeded", "01.01.2027")
    bot = AsyncMock()

    await reconcile_pending_card_payments(bot)

    assert mock_reconcile.await_count == 2


# ── handler tests ──


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_show_plans_cb(mock_api: MagicMock):
    mock_api.get_subscription_status = AsyncMock(return_value={"formatted_info": "Free"})
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.track_event = AsyncMock()

    cb = _make_callback(data="settings:subscription")
    await show_plans_cb(cb)

    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_choose_plan_unknown(mock_api: MagicMock):
    mock_api.track_event = AsyncMock()
    cb = _make_callback(data="zoo_sub:")
    await choose_plan(cb)
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_choose_plan_basic(mock_api: MagicMock):
    mock_api.track_event = AsyncMock()
    mock_api.is_card_payment_operational = AsyncMock(return_value=True)

    cb = _make_callback(data="zoo_sub:basic")
    await choose_plan(cb)

    cb.message.edit_text.assert_awaited_once()
    call_text = cb.message.edit_text.call_args[0][0]
    assert "Базовый" in call_text


@pytest.mark.asyncio
async def test_card_unavailable_handler():
    cb = _make_callback(data="zoo_pay_card_unavailable")
    await card_unavailable(cb)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.payment.get_settings")
@patch("bot.handlers.payment.api_client")
async def test_pay_card_creates_payment(mock_api: MagicMock, mock_settings: MagicMock):
    mock_settings.return_value = MagicMock(
        PAYMENT_RETURN_URL="https://t.me/testbot",
        RECEIPT_EMAIL="test@test.com",
    )
    mock_api.is_card_payment_operational = AsyncMock(return_value=True)
    mock_api.create_yookassa_payment = AsyncMock(
        return_value={"ok": True, "payment_id": "pid_1", "confirmation_url": "https://pay.url"}
    )
    mock_api.upsert_pending_payment = AsyncMock()
    mock_api.track_event = AsyncMock()

    cb = _make_callback(data="zoo_pay_card:basic")
    await pay_card(cb)

    mock_api.create_yookassa_payment.assert_awaited_once()
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.payment.get_settings")
@patch("bot.handlers.payment.api_client")
async def test_pay_card_unavailable(mock_api: MagicMock, mock_settings: MagicMock):
    mock_api.is_card_payment_operational = AsyncMock(return_value=False)
    mock_api.track_event = AsyncMock()

    cb = _make_callback(data="zoo_pay_card:basic")
    await pay_card(cb)

    cb.answer.assert_awaited()
    assert "недоступна" in cb.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("bot.handlers.payment.get_settings")
@patch("bot.handlers.payment.api_client")
async def test_pay_card_create_error(mock_api: MagicMock, mock_settings: MagicMock):
    mock_settings.return_value = MagicMock(
        PAYMENT_RETURN_URL="https://t.me/testbot",
        RECEIPT_EMAIL="",
    )
    mock_api.is_card_payment_operational = AsyncMock(return_value=True)
    mock_api.create_yookassa_payment = AsyncMock(side_effect=Exception("fail"))
    mock_api.track_event = AsyncMock()

    cb = _make_callback(data="zoo_pay_card:basic")
    await pay_card(cb)

    cb.answer.assert_awaited()
    assert "создать" in cb.answer.call_args[0][0].lower()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
@patch("bot.handlers.payment._reconcile_card_payment", new_callable=AsyncMock)
async def test_check_card_succeeded(mock_reconcile: AsyncMock, mock_api: MagicMock):
    mock_api.is_card_payment_operational = AsyncMock(return_value=True)
    mock_reconcile.return_value = ("succeeded", "01.02.2027")

    cb = _make_callback(data="zoo_check_card:pid1:basic")
    await check_card(cb)

    cb.message.edit_text.assert_awaited_once()
    assert "активирована" in cb.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_check_card_bad_params(mock_api: MagicMock):
    cb = _make_callback(data="zoo_check_card:only_one")
    await check_card(cb)
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_pay_stars_handler(mock_api: MagicMock):
    mock_api.track_event = AsyncMock()
    cb = _make_callback(data="zoo_pay_stars:basic")
    bot = AsyncMock()
    bot.send_invoice = AsyncMock()

    await pay_stars(cb, bot)

    bot.send_invoice.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_pay_stars_unknown_plan(mock_api: MagicMock):
    cb = _make_callback(data="zoo_pay_stars:nonexistent")
    bot = AsyncMock()

    await pay_stars(cb, bot)

    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_pre_checkout_valid(mock_api: MagicMock):
    pcq = _make_pre_checkout(user_id=42, payload="zoo:basic:42")
    await pre_checkout(pcq)
    pcq.answer.assert_awaited_once_with(ok=True)


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_pre_checkout_bad_payload(mock_api: MagicMock):
    mock_api.track_event = AsyncMock()
    pcq = _make_pre_checkout(user_id=42, payload="bad_payload")
    await pre_checkout(pcq)
    pcq.answer.assert_awaited_once()
    assert pcq.answer.call_args.kwargs.get("ok") is False


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_pre_checkout_user_mismatch(mock_api: MagicMock):
    mock_api.track_event = AsyncMock()
    pcq = _make_pre_checkout(user_id=42, payload="zoo:basic:99")
    await pre_checkout(pcq)
    pcq.answer.assert_awaited_once()
    assert pcq.answer.call_args.kwargs.get("ok") is False


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_successful_payment_handler(mock_api: MagicMock):
    mock_api.mark_payment_processed = AsyncMock(return_value={"success": True})
    mock_api.grant_premium = AsyncMock()
    mock_api.track_event = AsyncMock()
    mock_api.get_subscription_status = AsyncMock(
        return_value={"premium_until_str": "01.01.2027"}
    )

    msg = _make_message(user_id=42)
    msg.successful_payment = MagicMock(
        invoice_payload="zoo:basic:42",
        currency="XTR",
        total_amount=150,
        telegram_payment_charge_id="charge_1",
        provider_payment_charge_id="prov_1",
    )

    await successful_payment(msg)

    mock_api.mark_payment_processed.assert_awaited_once()
    mock_api.grant_premium.assert_awaited_once()
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_successful_payment_wrong_user(mock_api: MagicMock):
    mock_api.track_event = AsyncMock()

    msg = _make_message(user_id=42)
    msg.successful_payment = MagicMock(
        invoice_payload="zoo:basic:99",
        currency="XTR",
        total_amount=150,
        telegram_payment_charge_id="charge_1",
        provider_payment_charge_id="prov_1",
    )

    await successful_payment(msg)

    mock_api.track_event.assert_awaited()
    msg.answer.assert_not_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.payment.api_client")
async def test_successful_payment_amount_mismatch(mock_api: MagicMock):
    mock_api.track_event = AsyncMock()

    msg = _make_message(user_id=42)
    msg.successful_payment = MagicMock(
        invoice_payload="zoo:basic:42",
        currency="XTR",
        total_amount=999,
        telegram_payment_charge_id="charge_1",
        provider_payment_charge_id="prov_1",
    )

    await successful_payment(msg)

    mock_api.track_event.assert_awaited()
    msg.answer.assert_not_awaited()
