"""Агрегации для админ-панели: статистика, пользователи, финансы.

Все функции возвращают примитивные dict/list (JSON-friendly), без ORM-объектов.
I/O изолирован здесь (паттерн как в analytics.py) — роутеры остаются тонкими.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import Numeric, cast, distinct, func, select
from zoo_shared.db import async_session
from zoo_shared.db.models import (
    AnalyticsEvent,
    PendingPayment,
    Pet,
    ProcessedPayment,
    UserSettings,
)

logger = logging.getLogger(__name__)

# Цены тарифов (₽). Источник истины — bot/handlers/payment.py::PLANS.
PLAN_PRICES: dict[str, int] = {"basic": 199, "pro": 299}
PAID_STATUS = "succeeded"


def _start_of_today(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def get_overview() -> dict:
    """Сводная продуктовая статистика: пользователи, подписки, активность, питомцы."""
    now = datetime.utcnow()
    start_today = _start_of_today(now)
    since_7d = now - timedelta(days=7)
    since_30d = now - timedelta(days=30)

    async with async_session() as session:
        users_total = (await session.execute(select(func.count(UserSettings.id)))).scalar_one()

        premium_active = (
            await session.execute(
                select(func.count(UserSettings.id)).where(
                    UserSettings.is_premium.is_(True),
                    (UserSettings.premium_until.is_(None)) | (UserSettings.premium_until > now),
                )
            )
        ).scalar_one()

        by_tier_rows = (
            await session.execute(
                select(UserSettings.plan_tier, func.count(UserSettings.id)).group_by(UserSettings.plan_tier)
            )
        ).all()
        by_tier = {str(tier): int(cnt) for tier, cnt in by_tier_rows}

        new_today = (
            await session.execute(select(func.count(UserSettings.id)).where(UserSettings.created_at >= start_today))
        ).scalar_one()
        new_7d = (
            await session.execute(select(func.count(UserSettings.id)).where(UserSettings.created_at >= since_7d))
        ).scalar_one()
        new_30d = (
            await session.execute(select(func.count(UserSettings.id)).where(UserSettings.created_at >= since_30d))
        ).scalar_one()

        pets_total = (await session.execute(select(func.count(Pet.id)))).scalar_one()
        by_species_rows = (await session.execute(select(Pet.species, func.count(Pet.id)).group_by(Pet.species))).all()
        by_species = {str(sp): int(cnt) for sp, cnt in by_species_rows}

        active_today = (
            await session.execute(
                select(func.count(distinct(AnalyticsEvent.user_id))).where(AnalyticsEvent.created_at >= start_today)
            )
        ).scalar_one()
        active_7d = (
            await session.execute(
                select(func.count(distinct(AnalyticsEvent.user_id))).where(AnalyticsEvent.created_at >= since_7d)
            )
        ).scalar_one()
        events_total = (await session.execute(select(func.count(AnalyticsEvent.id)))).scalar_one()

        ai_requests_today = (
            await session.execute(
                select(func.coalesce(func.sum(UserSettings.ai_requests_today), 0)).where(
                    UserSettings.last_request_date == now.date()
                )
            )
        ).scalar_one()

    return {
        "users_total": int(users_total),
        "premium_active": int(premium_active),
        "by_tier": by_tier,
        "new_today": int(new_today),
        "new_7d": int(new_7d),
        "new_30d": int(new_30d),
        "pets_total": int(pets_total),
        "by_species": by_species,
        "active_today": int(active_today),
        "active_7d": int(active_7d),
        "events_total": int(events_total),
        "ai_requests_today": int(ai_requests_today),
    }


async def get_finance() -> dict:
    """Финансы: выручка (succeeded-платежи), разбивка по тарифам и статусам."""
    now = datetime.utcnow()
    since_30d = now - timedelta(days=30)
    amount = cast(PendingPayment.amount_value, Numeric)

    async with async_session() as session:
        revenue_total = (
            await session.execute(
                select(func.coalesce(func.sum(amount), 0)).where(PendingPayment.status == PAID_STATUS)
            )
        ).scalar_one()
        revenue_30d = (
            await session.execute(
                select(func.coalesce(func.sum(amount), 0)).where(
                    PendingPayment.status == PAID_STATUS, PendingPayment.created_at >= since_30d
                )
            )
        ).scalar_one()
        paid_count = (
            await session.execute(select(func.count(PendingPayment.id)).where(PendingPayment.status == PAID_STATUS))
        ).scalar_one()
        paying_users = (
            await session.execute(
                select(func.count(distinct(PendingPayment.user_id))).where(PendingPayment.status == PAID_STATUS)
            )
        ).scalar_one()

        by_plan_rows = (
            await session.execute(
                select(PendingPayment.plan_key, func.count(PendingPayment.id), func.coalesce(func.sum(amount), 0))
                .where(PendingPayment.status == PAID_STATUS)
                .group_by(PendingPayment.plan_key)
            )
        ).all()
        by_plan = {str(plan or "—"): {"count": int(cnt), "amount": float(amt)} for plan, cnt, amt in by_plan_rows}

        by_status_rows = (
            await session.execute(
                select(PendingPayment.status, func.count(PendingPayment.id)).group_by(PendingPayment.status)
            )
        ).all()
        by_status = {str(st): int(cnt) for st, cnt in by_status_rows}

        processed_total = (await session.execute(select(func.count(ProcessedPayment.id)))).scalar_one()

        recent_rows = (
            await session.execute(
                select(
                    PendingPayment.user_id,
                    PendingPayment.plan_key,
                    PendingPayment.amount_value,
                    PendingPayment.currency,
                    PendingPayment.created_at,
                )
                .where(PendingPayment.status == PAID_STATUS)
                .order_by(PendingPayment.created_at.desc())
                .limit(10)
            )
        ).all()
        recent = [
            {
                "user_id": int(uid),
                "plan_key": str(plan or ""),
                "amount": str(amt or ""),
                "currency": str(cur or ""),
                "created_at": created.isoformat() if created else None,
            }
            for uid, plan, amt, cur, created in recent_rows
        ]

    return {
        "revenue_total": float(revenue_total),
        "revenue_30d": float(revenue_30d),
        "paid_count": int(paid_count),
        "paying_users": int(paying_users),
        "by_plan": by_plan,
        "by_status": by_status,
        "processed_total": int(processed_total),
        "recent": recent,
        "currency": "RUB",
    }


async def list_users(limit: int = 8, offset: int = 0, query: str | None = None) -> dict:
    """Список пользователей с пагинацией; query — точный поиск по telegram user_id."""
    limit = max(1, min(limit, 50))
    offset = max(0, offset)

    base = select(UserSettings)
    counter = select(func.count(UserSettings.id))
    exact_id: int | None = None
    if query:
        stripped = query.strip()
        if stripped.isdigit():
            exact_id = int(stripped)
            base = base.where(UserSettings.user_id == exact_id)
            counter = counter.where(UserSettings.user_id == exact_id)

    async with async_session() as session:
        total = (await session.execute(counter)).scalar_one()
        rows = (
            (await session.execute(base.order_by(UserSettings.created_at.desc()).limit(limit).offset(offset)))
            .scalars()
            .all()
        )
        items = []
        for s in rows:
            pets = (await session.execute(select(func.count(Pet.id)).where(Pet.user_id == s.user_id))).scalar_one()
            items.append(
                {
                    "user_id": int(s.user_id),
                    "plan_tier": s.plan_tier,
                    "is_premium": bool(s.is_premium),
                    "premium_until": s.premium_until.isoformat() if s.premium_until else None,
                    "pets": int(pets),
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
            )

    return {"items": items, "total": int(total), "limit": limit, "offset": offset, "query": query}


async def get_user_detail(user_id: int) -> dict | None:
    """Детали пользователя: подписка, питомцы, активность, платежи. None если нет настроек."""
    async with async_session() as session:
        settings = (
            await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        ).scalar_one_or_none()
        if settings is None:
            return None

        pets = (await session.execute(select(func.count(Pet.id)).where(Pet.user_id == user_id))).scalar_one()
        events = (
            await session.execute(select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.user_id == user_id))
        ).scalar_one()
        last_seen = (
            await session.execute(select(func.max(AnalyticsEvent.created_at)).where(AnalyticsEvent.user_id == user_id))
        ).scalar_one()
        payments = (
            await session.execute(select(func.count(ProcessedPayment.id)).where(ProcessedPayment.user_id == user_id))
        ).scalar_one()

    return {
        "user_id": int(settings.user_id),
        "plan_tier": settings.plan_tier,
        "is_premium": bool(settings.is_premium),
        "premium_until": settings.premium_until.isoformat() if settings.premium_until else None,
        "city": settings.city or "",
        "ai_requests_today": int(settings.ai_requests_today),
        "weather_notify": bool(settings.weather_notify),
        "pets": int(pets),
        "events": int(events),
        "last_seen": last_seen.isoformat() if last_seen else None,
        "payments": int(payments),
        "created_at": settings.created_at.isoformat() if settings.created_at else None,
    }


async def get_broadcast_targets() -> list[int]:
    """Все user_id для рассылки (объединение настроек и аналитики, уникальные)."""
    async with async_session() as session:
        union_q = select(UserSettings.user_id).union(select(AnalyticsEvent.user_id))
        ids = (await session.execute(union_q)).scalars().all()
    return sorted({int(i) for i in ids if i is not None})
