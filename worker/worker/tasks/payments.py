"""Payment reconciliation for pending YooKassa card payments."""

from __future__ import annotations

import logging

from yookassa import Configuration
from yookassa import Payment as YooPayment
from zoo_shared.config import get_settings
from zoo_shared.payments import PAYMENT_PLANS, normalize_money_value

from worker import api_client
from worker.bot_sender import send_message

logger = logging.getLogger(__name__)


def _configure_yookassa() -> bool:
    settings = get_settings()
    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        logger.info("Skipping YooKassa reconcile: credentials are not configured")
        return False
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
    return True


async def _track_payment_failure(user_id: int | None, payment_id: str, reason: str) -> None:
    if user_id is None:
        return
    await api_client.track_event(
        user_id,
        "payment_failed",
        source="yookassa_worker",
        payload={"payment_id": payment_id, "reason": reason},
    )


async def _send_success_message(user_id: int, plan_name: str, until: str) -> None:
    await send_message(
        user_id,
        f"✅ Подписка <b>{plan_name}</b> активирована!\nДействует до {until}.\n\nГлавное меню ниже.",
    )


async def _reconcile_card_payment(
    payment_id: str,
    *,
    expected_user_id: int | None = None,
    expected_plan_key: str | None = None,
    notify_user: bool = True,
) -> tuple[str, str]:
    try:
        payment = YooPayment.find_one(payment_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("YooKassa check payment error: %s", e)
        await _track_payment_failure(expected_user_id, payment_id, "provider_check_error")
        return "error", "provider_check_error"

    payment_status = str(getattr(payment, "status", "") or "").strip()
    if payment_status != "succeeded":
        await api_client.update_pending_payment(
            "yookassa",
            payment_id,
            status=payment_status or "pending",
            completed=payment_status == "canceled",
        )
        if payment_status == "canceled":
            if expected_user_id is not None:
                await api_client.track_event(
                    expected_user_id,
                    "payment_canceled",
                    source="yookassa_worker",
                    payload={"payment_id": payment_id},
                )
            return "canceled", "canceled"
        return "pending", payment_status or "pending"

    metadata_raw = getattr(payment, "metadata", {}) or {}
    metadata = metadata_raw if hasattr(metadata_raw, "get") else {}
    meta_user_id = str(metadata.get("user_id", "")).strip()
    meta_plan_key = str(metadata.get("plan_key", "")).strip()

    if not meta_user_id or not meta_plan_key:
        await api_client.update_pending_payment(
            "yookassa",
            payment_id,
            status="error",
            last_error="metadata_missing",
        )
        await _track_payment_failure(expected_user_id, payment_id, "metadata_missing")
        return "error", "metadata_missing"

    if expected_user_id is not None and meta_user_id != str(expected_user_id):
        await api_client.update_pending_payment(
            "yookassa",
            payment_id,
            status="error",
            last_error="user_mismatch",
        )
        await _track_payment_failure(expected_user_id, payment_id, "user_mismatch")
        return "error", "user_mismatch"

    if expected_plan_key is not None and meta_plan_key != expected_plan_key:
        await api_client.update_pending_payment(
            "yookassa",
            payment_id,
            status="error",
            last_error="plan_mismatch",
        )
        await _track_payment_failure(expected_user_id, payment_id, "plan_mismatch")
        return "error", "plan_mismatch"

    plan = PAYMENT_PLANS.get(meta_plan_key)
    if not plan:
        await api_client.update_pending_payment(
            "yookassa",
            payment_id,
            status="error",
            last_error="unknown_plan",
        )
        await _track_payment_failure(expected_user_id, payment_id, "unknown_plan")
        return "error", "unknown_plan"

    amount_raw = getattr(getattr(payment, "amount", None), "value", "")
    currency_raw = getattr(getattr(payment, "amount", None), "currency", "")
    amount_value = normalize_money_value(amount_raw)
    expected_amount = normalize_money_value(plan["price"])
    currency_value = str(currency_raw or "").strip().upper()
    if amount_value != expected_amount or currency_value != "RUB":
        await api_client.update_pending_payment(
            "yookassa",
            payment_id,
            status="error",
            last_error=f"amount_mismatch:{amount_value}:{currency_value}",
        )
        await _track_payment_failure(expected_user_id, payment_id, "amount_mismatch")
        return "error", "amount_mismatch"

    user_id = int(meta_user_id)
    result = await api_client.mark_payment_processed(
        provider="yookassa",
        payment_id=payment_id,
        user_id=user_id,
        plan_key=meta_plan_key,
    )
    if not result.get("success"):
        await api_client.update_pending_payment(
            "yookassa",
            payment_id,
            status="succeeded",
            completed=True,
        )
        return "already_processed", "already_processed"

    await api_client.grant_premium(user_id, days=plan["days"], plan_tier=plan["tier"])
    await api_client.update_pending_payment(
        "yookassa",
        payment_id,
        status="succeeded",
        completed=True,
    )
    await api_client.track_event(
        user_id,
        "payment_succeeded",
        source="yookassa_worker",
        payload={"plan_key": meta_plan_key, "payment_id": payment_id},
    )

    sub = await api_client.get_subscription_status(user_id)
    until = sub.get("premium_until_str", "бессрочно")
    if notify_user:
        try:
            await _send_success_message(user_id, plan["name"], until)
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not notify user about YooKassa payment %s: %s", payment_id, e)
    return "succeeded", until


async def reconcile_pending_payments() -> None:
    """Background check for pending card payments and subscription activation."""
    if not _configure_yookassa():
        return

    card_ok = await api_client.is_card_payment_operational()
    if not card_ok:
        logger.info("Skipping YooKassa reconcile: card payment provider is not operational")
        return

    pending_payments = await api_client.list_pending_payments("yookassa")
    processed = 0
    for pending in pending_payments:
        try:
            status, _details = await _reconcile_card_payment(
                pending["payment_id"],
                expected_user_id=pending.get("user_id"),
                expected_plan_key=pending.get("plan_key"),
                notify_user=True,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to reconcile YooKassa payment %s: %s", pending.get("payment_id"), e)
            continue
        if status in {"succeeded", "already_processed", "canceled"}:
            processed += 1

    if pending_payments:
        logger.info("YooKassa reconciliation checked=%s processed=%s", len(pending_payments), processed)
