"""Subscriptions & user settings REST API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from zoo_shared.db.models import UserSettings
from zoo_shared.schemas.subscription import SubscriptionGrant, SubscriptionStatus

from backend.deps import get_session
from backend.services.subscription import (
    can_use_pdf_export,
    can_use_voice_notes,
    can_use_weather_notifications,
    check_ai_limit,
    check_pet_limit,
    format_subscription_info,
    get_or_create_settings,
    get_plan_tier,
    grant_premium,
    is_premium,
    refund_ai_limit,
    revoke_premium,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/status/{user_id}", response_model=SubscriptionStatus)
async def subscription_status(user_id: int):
    settings = await get_or_create_settings(user_id)
    return SubscriptionStatus(
        user_id=settings.user_id,
        plan_tier=settings.plan_tier,
        is_premium=settings.is_premium,
        premium_until=settings.premium_until,
        ai_requests_today=settings.ai_requests_today,
        weather_notify=settings.weather_notify,
    )


@router.get("/settings/{user_id}")
async def get_user_settings(user_id: int):
    settings = await get_or_create_settings(user_id)
    return {
        "user_id": settings.user_id,
        "city": settings.city,
        "latitude": settings.latitude,
        "longitude": settings.longitude,
        "is_premium": settings.is_premium,
        "premium_until": settings.premium_until.isoformat() if settings.premium_until else None,
        "plan_tier": settings.plan_tier,
        "ai_requests_today": settings.ai_requests_today,
        "weather_notify": settings.weather_notify,
        "subscription_info": format_subscription_info(settings),
    }


@router.get("/plan_tier/{user_id}")
async def get_user_plan_tier(user_id: int):
    tier = await get_plan_tier(user_id)
    return {"plan_tier": tier}


@router.get("/is_premium/{user_id}")
async def check_premium(user_id: int):
    return {"is_premium": await is_premium(user_id)}


@router.post("/check_ai_limit/{user_id}")
async def check_user_ai_limit(user_id: int):
    allowed, remaining = await check_ai_limit(user_id)
    return {"allowed": allowed, "remaining": remaining}


@router.post("/refund_ai_limit/{user_id}")
async def refund_user_ai_limit(user_id: int):
    await refund_ai_limit(user_id)
    return {"ok": True}


@router.get("/check_pet_limit/{user_id}")
async def check_user_pet_limit(user_id: int):
    allowed, remaining = await check_pet_limit(user_id)
    return {"allowed": allowed, "remaining": remaining}


@router.post("/grant")
async def grant_user_premium(body: SubscriptionGrant):
    result = await grant_premium(body.user_id, body.days, plan_tier=body.plan_tier)
    return {"ok": result}


@router.post("/revoke/{user_id}")
async def revoke_user_premium(user_id: int):
    result = await revoke_premium(user_id)
    return {"ok": result}


@router.get("/can_pdf/{user_id}")
async def can_pdf(user_id: int):
    return {"allowed": await can_use_pdf_export(user_id)}


@router.get("/can_weather/{user_id}")
async def can_weather(user_id: int):
    return {"allowed": await can_use_weather_notifications(user_id)}


@router.get("/can_voice/{user_id}")
async def can_voice(user_id: int):
    return {"allowed": await can_use_voice_notes(user_id)}


@router.get("/check_feature/{user_id}")
async def check_feature(user_id: int, feature: str = ""):
    feature_map = {
        "voice_notes": can_use_voice_notes,
        "weather_notifications": can_use_weather_notifications,
        "pdf_export": can_use_pdf_export,
    }
    checker = feature_map.get(feature)
    if checker:
        return {"allowed": await checker(user_id)}
    return {"allowed": await is_premium(user_id)}


@router.post("/toggle_weather/{user_id}")
async def toggle_weather(user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id=user_id)
        session.add(settings)
    settings.weather_notify = not settings.weather_notify
    await session.commit()
    return {"weather_notify": settings.weather_notify}


@router.patch("/settings/{user_id}")
async def update_user_settings(
    user_id: int,
    city: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    weather_notify: bool | None = None,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id=user_id)
        session.add(settings)

    if city is not None:
        settings.city = city
    if latitude is not None:
        settings.latitude = latitude
    if longitude is not None:
        settings.longitude = longitude
    if weather_notify is not None:
        settings.weather_notify = weather_notify
    await session.commit()
    return {"ok": True}
