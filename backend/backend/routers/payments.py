"""Payments REST API."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from yookassa import Configuration
from yookassa import Payment as YooPayment
from zoo_shared.config import get_settings
from zoo_shared.db.models import PendingPayment, ProcessedPayment

from backend.deps import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])


class MarkProcessedRequest(BaseModel):
    provider: str
    payment_id: str
    user_id: int
    plan_key: str


class UpsertPendingRequest(BaseModel):
    provider: str
    payment_id: str
    user_id: int
    plan_key: str
    amount_value: str = ""
    currency: str = ""
    status: str = "pending"


class UpdatePendingRequest(BaseModel):
    provider: str
    payment_id: str
    status: str
    last_error: str = ""
    completed: bool = False


@router.post("/mark_processed")
async def mark_processed(body: MarkProcessedRequest, session: AsyncSession = Depends(get_session)):
    if not body.payment_id:
        return {"ok": False, "duplicate": False}
    session.add(
        ProcessedPayment(
            provider=body.provider,
            payment_id=body.payment_id,
            user_id=body.user_id,
            plan_key=body.plan_key,
        )
    )
    try:
        await session.commit()
        return {"ok": True, "duplicate": False}
    except IntegrityError:
        await session.rollback()
        return {"ok": False, "duplicate": True}


@router.post("/upsert_pending")
async def upsert_pending(body: UpsertPendingRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(PendingPayment).where(
            PendingPayment.provider == body.provider,
            PendingPayment.payment_id == body.payment_id,
        )
    )
    pending = result.scalar_one_or_none()
    if not pending:
        pending = PendingPayment(
            provider=body.provider,
            payment_id=body.payment_id,
            user_id=body.user_id,
            plan_key=body.plan_key,
            amount_value=body.amount_value,
            currency=body.currency,
        )
        session.add(pending)

    pending.user_id = body.user_id
    pending.plan_key = body.plan_key
    pending.amount_value = body.amount_value
    pending.currency = body.currency
    pending.status = body.status
    pending.last_error = ""
    await session.commit()
    return {"ok": True}


@router.post("/update_pending")
async def update_pending(body: UpdatePendingRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(PendingPayment).where(
            PendingPayment.provider == body.provider,
            PendingPayment.payment_id == body.payment_id,
        )
    )
    pending = result.scalar_one_or_none()
    if not pending:
        return {"ok": False}

    pending.status = body.status
    pending.last_checked_at = datetime.utcnow()
    pending.last_error = body.last_error[:1000]
    if body.completed:
        pending.completed_at = datetime.utcnow()
    await session.commit()
    return {"ok": True}


@router.get("/pending_list/{provider}")
async def list_pending(provider: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(PendingPayment).where(
            PendingPayment.provider == provider,
            PendingPayment.completed_at.is_(None),
        )
    )
    rows = result.scalars().all()
    return [
        {
            "id": p.id, "provider": p.provider, "payment_id": p.payment_id,
            "user_id": p.user_id, "plan_key": p.plan_key,
            "amount_value": p.amount_value, "currency": p.currency,
            "status": p.status, "last_error": p.last_error,
            "created_at": p.created_at.isoformat(),
        }
        for p in rows
    ]


@router.get("/pending/{provider}/{payment_id}")
async def get_pending(provider: str, payment_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(PendingPayment).where(
            PendingPayment.provider == provider,
            PendingPayment.payment_id == payment_id,
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        return None
    return {
        "id": p.id, "provider": p.provider, "payment_id": p.payment_id,
        "user_id": p.user_id, "plan_key": p.plan_key,
        "amount_value": p.amount_value, "currency": p.currency,
        "status": p.status, "last_error": p.last_error,
        "created_at": p.created_at.isoformat(),
    }


# ══════════════ YOOKASSA PROXY ══════════════


class CreateYooKassaPaymentRequest(BaseModel):
    plan_key: str
    plan_price: int
    plan_name: str
    user_id: int
    return_url: str
    receipt_email: str = ""


@router.post("/yookassa/create")
async def create_yookassa_payment(body: CreateYooKassaPaymentRequest):
    settings = get_settings()
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    payment_request: dict = {
        "amount": {"value": f"{body.plan_price}.00", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "return_url": body.return_url,
        },
        "capture": True,
        "description": f"Zoo Bot — {body.plan_name}, 1 месяц",
        "metadata": {
            "user_id": str(body.user_id),
            "plan_key": body.plan_key,
        },
    }
    if body.receipt_email:
        payment_request["receipt"] = {
            "customer": {"email": body.receipt_email},
            "items": [
                {
                    "description": f"Подписка {body.plan_name} Zoo Bot",
                    "quantity": "1.00",
                    "amount": {"value": f"{body.plan_price}.00", "currency": "RUB"},
                    "vat_code": 1,
                    "payment_subject": "service",
                    "payment_mode": "full_payment",
                }
            ],
        }

    try:
        payment = YooPayment.create(payment_request, uuid.uuid4().hex)
    except Exception as e:
        logger.exception("YooKassa create payment error: %s", e)
        return {"ok": False, "error": str(e)}

    return {
        "ok": True,
        "payment_id": payment.id,
        "confirmation_url": payment.confirmation.confirmation_url,
    }


class ReconcileYooKassaRequest(BaseModel):
    payment_id: str
    expected_user_id: int | None = None
    expected_plan_key: str | None = None
    expected_amount: str | None = None


@router.post("/yookassa/reconcile")
async def reconcile_yookassa_payment(body: ReconcileYooKassaRequest):
    settings = get_settings()
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    try:
        payment = YooPayment.find_one(body.payment_id)
    except Exception as e:
        logger.exception("YooKassa check payment error: %s", e)
        return {"ok": False, "status": "error", "error": "provider_check_error"}

    payment_status = str(getattr(payment, "status", "") or "").strip()
    if payment_status != "succeeded":
        return {
            "ok": True,
            "status": payment_status or "pending",
            "metadata_user_id": None,
            "metadata_plan_key": None,
        }

    metadata_raw = getattr(payment, "metadata", {}) or {}
    metadata = metadata_raw if hasattr(metadata_raw, "get") else {}
    meta_user_id = str(metadata.get("user_id", "")).strip()
    meta_plan_key = str(metadata.get("plan_key", "")).strip()

    if not meta_user_id or not meta_plan_key:
        return {"ok": False, "status": "error", "error": "metadata_missing"}

    if body.expected_user_id is not None and meta_user_id != str(body.expected_user_id):
        return {"ok": False, "status": "error", "error": "user_mismatch"}

    if body.expected_plan_key is not None and meta_plan_key != body.expected_plan_key:
        return {"ok": False, "status": "error", "error": "plan_mismatch"}

    amount_raw = getattr(getattr(payment, "amount", None), "value", "")
    currency_raw = getattr(getattr(payment, "amount", None), "currency", "")
    amount_value = _normalize_money_value(amount_raw)
    currency_value = str(currency_raw or "").strip().upper()

    if body.expected_amount is not None:
        expected_norm = _normalize_money_value(body.expected_amount)
        if amount_value != expected_norm or currency_value != "RUB":
            return {"ok": False, "status": "error", "error": "amount_mismatch"}

    return {
        "ok": True,
        "status": "succeeded",
        "metadata_user_id": meta_user_id,
        "metadata_plan_key": meta_plan_key,
        "amount_value": amount_value,
        "currency": currency_value,
    }


def _normalize_money_value(value: str | int | float | None) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value).strip()
