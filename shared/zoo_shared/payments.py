"""Shared payment plans and money helpers."""

from __future__ import annotations

PAYMENT_PLANS = {
    "basic": {
        "name": "🐾 Базовый",
        "price": 199,
        "days": 30,
        "stars": 150,
        "tier": "basic",
    },
    "pro": {
        "name": "⭐ PRO",
        "price": 299,
        "days": 30,
        "stars": 200,
        "tier": "pro",
    },
}


def get_payment_plan(plan_key: str) -> dict | None:
    """Return a payment plan by key."""
    return PAYMENT_PLANS.get(plan_key)


def normalize_money_value(value: str | int | float | None) -> str:
    """Normalize provider money values to two decimals."""
    if value in (None, ""):
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value).strip()
