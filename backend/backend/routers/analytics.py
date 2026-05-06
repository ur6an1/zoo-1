"""Analytics REST API."""

from __future__ import annotations

from fastapi import APIRouter
from zoo_shared.schemas.analytics import AnalyticsEventCreate

from backend.services.analytics import build_funnel_report, track_event, track_user_activity

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/track")
async def track(body: AnalyticsEventCreate):
    await track_event(
        user_id=body.user_id,
        event_name=body.event_name,
        source=body.source,
        payload=body.payload,
    )
    return {"ok": True}


@router.post("/track_activity/{user_id}")
async def track_activity(user_id: int, source: str = ""):
    await track_user_activity(user_id, source=source)
    return {"ok": True}


@router.get("/funnel")
async def funnel_report(days: int = 7):
    report = await build_funnel_report(days=days)
    return {"report": report}
