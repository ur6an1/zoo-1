"""Payment schemas."""

from __future__ import annotations

from pydantic import BaseModel


class PaymentCreate(BaseModel):
    user_id: int
    plan_key: str
    provider: str = "yookassa"


class PaymentStatus(BaseModel):
    payment_id: str
    status: str
    provider: str
