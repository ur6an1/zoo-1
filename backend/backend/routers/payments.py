"""Payments REST API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from zoo_shared.db.models import PendingPayment, ProcessedPayment

from backend.deps import get_session

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
