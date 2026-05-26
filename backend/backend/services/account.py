"""Удаление персональных данных пользователя (152-ФЗ, команда /delete_me).

FK у дочерних таблиц объявлены с ON DELETE CASCADE, поэтому удаление питомца
на уровне БД каскадно сносит напоминания/прививки/визиты/вес/еду/воду/аллергии/
документы/голосовые. Остальное (настройки, события, платежи) удаляем явно по user_id.
"""

from __future__ import annotations

import logging

from sqlalchemy import delete, func, select
from zoo_shared.db import async_session
from zoo_shared.db.models import (
    AnalyticsEvent,
    PendingPayment,
    Pet,
    ProcessedPayment,
    Reminder,
    UserSettings,
)

logger = logging.getLogger(__name__)


async def delete_user_data(user_id: int) -> dict[str, int]:
    """Полностью удаляет данные пользователя. Возвращает счётчики удалённого."""
    deleted: dict[str, int] = {}
    async with async_session() as session:
        pets = (await session.execute(select(func.count(Pet.id)).where(Pet.user_id == user_id))).scalar_one()
        deleted["pets"] = int(pets)
        # Каскад БД снесёт всё, что привязано к питомцам.
        await session.execute(delete(Pet).where(Pet.user_id == user_id))

        for label, model in (
            ("reminders", Reminder),
            ("events", AnalyticsEvent),
            ("pending_payments", PendingPayment),
            ("processed_payments", ProcessedPayment),
            ("user_settings", UserSettings),
        ):
            res = await session.execute(delete(model).where(model.user_id == user_id))
            deleted[label] = res.rowcount or 0

        await session.commit()

    logger.info("Удалены данные пользователя %s: %s", user_id, deleted)
    return deleted
