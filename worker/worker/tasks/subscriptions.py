"""Subscription expiration notifications."""

import logging
from datetime import date

from sqlalchemy import select
from zoo_shared.db import async_session
from zoo_shared.db.models import UserSettings

from worker.bot_sender import send_message

logger = logging.getLogger(__name__)


async def send_subscription_expiration_notifications():
    """Отправляет напоминания о скором окончании подписки."""
    today = date.today()
    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(
                UserSettings.is_premium == True,  # noqa: E712
                UserSettings.premium_until != None,  # noqa: E711
            )
        )
        users = result.scalars().all()

    for s in users:
        if not s.premium_until:
            continue
        days_left = (s.premium_until.date() - today).days
        if days_left not in (3, 1, 0, -1):
            continue

        if days_left > 0:
            text = (
                "⏳ <b>Подписка скоро закончится</b>\n\n"
                f"Осталось {days_left} дн. до окончания.\n"
                "Продлите подписку, чтобы не потерять доступ к PRO-функциям."
            )
        elif days_left == 0:
            text = (
                "⏰ <b>Подписка заканчивается сегодня</b>\n\nПродлите подписку, чтобы сохранить доступ к PRO-функциям."
            )
        else:
            text = (
                "❌ <b>Подписка истекла</b>\n\nДоступ к PRO-функциям закрыт. Вы можете продлить подписку в настройках."
            )

        await send_message(s.user_id, text)
