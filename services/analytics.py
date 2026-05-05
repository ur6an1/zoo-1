"""Минимальная аналитика воронки внутри SQLite."""

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import distinct, func, select

from database import async_session
from models.models import AnalyticsEvent

logger = logging.getLogger(__name__)

RETURN_GAP = timedelta(hours=12)
FUNNEL_EVENTS = (
    "start",
    "onboarding_started",
    "pet_created",
    "first_value_reached",
    "paywall_view",
    "plan_selected",
    "payment_started",
    "payment_pending",
    "payment_succeeded",
    "payment_failed",
    "payment_canceled",
    "premium_feature_used",
    "user_returned",
)


async def track_event(
    user_id: int,
    event_name: str,
    source: str = "",
    payload: dict | None = None,
) -> None:
    """Сохраняет событие, не прерывая основной сценарий при ошибке."""
    try:
        async with async_session() as session:
            session.add(
                AnalyticsEvent(
                    user_id=user_id,
                    event_name=event_name,
                    source=source[:100],
                    payload_json=json.dumps(payload or {}, ensure_ascii=False),
                )
            )
            await session.commit()
    except Exception as e:
        logger.warning("Не удалось сохранить analytics event %s: %s", event_name, e)


async def track_user_activity(user_id: int, source: str = "") -> None:
    """Фиксирует возврат, если пользователь вернулся после паузы."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(AnalyticsEvent.created_at)
                .where(AnalyticsEvent.user_id == user_id)
                .order_by(AnalyticsEvent.created_at.desc())
                .limit(1)
            )
            last_seen = result.scalar_one_or_none()
    except Exception as e:
        logger.warning("Не удалось проверить user_returned для %s: %s", user_id, e)
        return

    if last_seen and datetime.utcnow() - last_seen >= RETURN_GAP:
        gap_hours = round((datetime.utcnow() - last_seen).total_seconds() / 3600, 1)
        await track_event(
            user_id,
            "user_returned",
            source=source,
            payload={"gap_hours": gap_hours},
        )


async def build_funnel_report(days: int = 7) -> str:
    """Возвращает краткую сводку по событиям воронки."""
    since = datetime.utcnow() - timedelta(days=days)
    lines = [f"Воронка за последние {days} дн.\n"]

    async with async_session() as session:
        for event_name in FUNNEL_EVENTS:
            result = await session.execute(
                select(
                    func.count(AnalyticsEvent.id),
                    func.count(distinct(AnalyticsEvent.user_id)),
                ).where(
                    AnalyticsEvent.event_name == event_name,
                    AnalyticsEvent.created_at >= since,
                )
            )
            total, users = result.one()
            lines.append(f"• {event_name}: {int(total)} событий / {int(users)} пользователей")

    return "\n".join(lines)
