"""HTTP client for worker-to-backend calls."""

from __future__ import annotations

import logging

import httpx
from zoo_shared.config import get_settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _internal_headers() -> dict[str, str]:
    key = get_settings().INTERNAL_API_KEY.strip()
    return {"X-Internal-API-Key": key} if key else {}


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        settings = get_settings()
        _client = httpx.AsyncClient(base_url=settings.BACKEND_URL, timeout=30.0, headers=_internal_headers())
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def is_card_payment_operational() -> bool:
    c = await get_client()
    r = await c.get("/services/health/card_payment")
    r.raise_for_status()
    return bool(r.json()["operational"])


async def list_pending_payments(provider: str) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/payments/pending_list/{provider}")
    r.raise_for_status()
    return r.json()


async def update_pending_payment(
    provider: str,
    payment_id: str,
    status: str,
    last_error: str = "",
    completed: bool = False,
) -> None:
    c = await get_client()
    r = await c.post(
        "/payments/update_pending",
        json={
            "provider": provider,
            "payment_id": payment_id,
            "status": status,
            "last_error": last_error,
            "completed": completed,
        },
    )
    r.raise_for_status()


async def mark_payment_processed(
    provider: str,
    payment_id: str,
    user_id: int,
    plan_key: str,
) -> dict[str, bool]:
    c = await get_client()
    r = await c.post(
        "/payments/mark_processed",
        json={
            "provider": provider,
            "payment_id": payment_id,
            "user_id": user_id,
            "plan_key": plan_key,
        },
    )
    r.raise_for_status()
    data = r.json()
    success = bool(data.get("ok"))
    duplicate = bool(data.get("duplicate"))
    return {"success": success, "ok": success, "duplicate": duplicate}


async def grant_premium(user_id: int, days: int, plan_tier: str) -> bool:
    c = await get_client()
    r = await c.post(
        "/subscriptions/grant",
        json={"user_id": user_id, "days": days, "plan_tier": plan_tier},
    )
    r.raise_for_status()
    return bool(r.json().get("success"))


async def get_subscription_status(user_id: int) -> dict:
    c = await get_client()
    r = await c.get(f"/subscriptions/status/{user_id}")
    r.raise_for_status()
    return r.json()


async def track_event(user_id: int, event_name: str, source: str = "", payload: dict | None = None) -> None:
    try:
        c = await get_client()
        await c.post(
            "/analytics/track",
            json={"user_id": user_id, "event_name": event_name, "source": source, "payload": payload},
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to track worker event %s: %s", event_name, e)
