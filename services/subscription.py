"""Управление подписками, тарифами и лимитами."""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import func, select

from config import FREE_AI_LIMIT, FREE_PET_LIMIT
from database import async_session
from models.models import Pet, UserSettings

logger = logging.getLogger(__name__)

PLAN_FREE = "free"
PLAN_BASIC = "basic"
PLAN_PRO = "pro"

PLAN_LABELS = {
    PLAN_FREE: "Бесплатный",
    PLAN_BASIC: "Базовый",
    PLAN_PRO: "PRO",
}

PLAN_AI_LIMITS: dict[str, int | None] = {
    PLAN_FREE: FREE_AI_LIMIT,
    PLAN_BASIC: None,
    PLAN_PRO: None,
}

PLAN_PET_LIMITS: dict[str, int | None] = {
    PLAN_FREE: FREE_PET_LIMIT,
    PLAN_BASIC: 5,
    PLAN_PRO: None,
}

GRACE_DAYS = 2


def _normalize_plan(plan_tier: str | None, is_premium: bool) -> str:
    plan = (plan_tier or "").strip().lower()
    if plan in (PLAN_FREE, PLAN_BASIC, PLAN_PRO):
        return plan
    return PLAN_PRO if is_premium else PLAN_FREE


def _is_subscription_active(settings: UserSettings) -> bool:
    if not settings.is_premium:
        return False
    return settings.premium_until is None or settings.premium_until + timedelta(days=GRACE_DAYS) > datetime.utcnow()


def _ai_limit_for_plan(plan_tier: str) -> int | None:
    return PLAN_AI_LIMITS.get(plan_tier, FREE_AI_LIMIT)


def _pet_limit_for_plan(plan_tier: str) -> int | None:
    return PLAN_PET_LIMITS.get(plan_tier, FREE_PET_LIMIT)


async def get_or_create_settings(user_id: int) -> UserSettings:
    """Получает или создаёт настройки пользователя с авто-нормализацией тарифа."""
    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar()
        if not settings:
            settings = UserSettings(user_id=user_id, plan_tier=PLAN_FREE)
            session.add(settings)
            await session.commit()
            await session.refresh(settings)
            return settings

        changed = False
        if settings.is_premium and settings.premium_until and settings.premium_until + timedelta(days=GRACE_DAYS) <= datetime.utcnow():
            settings.is_premium = False
            settings.premium_until = None
            settings.plan_tier = PLAN_FREE
            settings.weather_notify = False
            changed = True

        normalized = _normalize_plan(getattr(settings, "plan_tier", None), settings.is_premium)
        if settings.plan_tier != normalized:
            settings.plan_tier = normalized
            changed = True

        if changed:
            await session.commit()
            await session.refresh(settings)

        return settings


async def get_plan_tier(user_id: int) -> str:
    """Возвращает активный тариф пользователя: free/basic/pro."""
    settings = await get_or_create_settings(user_id)
    if not _is_subscription_active(settings):
        return PLAN_FREE
    return _normalize_plan(settings.plan_tier, settings.is_premium)


async def is_premium(user_id: int) -> bool:
    """Проверяет, есть ли активная платная подписка (basic/pro)."""
    return await get_plan_tier(user_id) in (PLAN_BASIC, PLAN_PRO)


async def check_ai_limit(user_id: int) -> tuple[bool, int]:
    """Проверяет и списывает лимит AI-запросов. Returns: (allowed, remaining)."""
    plan_tier = await get_plan_tier(user_id)
    limit = _ai_limit_for_plan(plan_tier)
    if limit is None:
        return True, 999

    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        s = result.scalar()
        if not s:
            s = UserSettings(user_id=user_id, plan_tier=PLAN_FREE)
            session.add(s)
            await session.flush()

        today = date.today()
        if s.last_request_date != today:
            s.ai_requests_today = 0
            s.last_request_date = today

        remaining = limit - s.ai_requests_today
        if remaining <= 0:
            await session.commit()
            return False, 0

        s.ai_requests_today += 1
        await session.commit()
        return True, remaining - 1


async def refund_ai_limit(user_id: int) -> None:
    """Возвращает 1 AI-запрос за неуспешный внешний вызов."""
    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        s = result.scalar()
        if not s:
            return

        if s.last_request_date != date.today():
            return

        if s.ai_requests_today > 0:
            s.ai_requests_today -= 1
            await session.commit()


async def check_pet_limit(user_id: int) -> tuple[bool, int]:
    """Проверяет лимит питомцев. Returns: (allowed, remaining)."""
    plan_tier = await get_plan_tier(user_id)
    limit = _pet_limit_for_plan(plan_tier)
    if limit is None:
        return True, 999

    async with async_session() as session:
        result = await session.execute(
            select(func.count(Pet.id)).where(Pet.user_id == user_id)
        )
        count = int(result.scalar_one() or 0)

    return count < limit, max(limit - count, 0)


async def grant_premium(user_id: int, days: int = 30, plan_tier: str = PLAN_PRO) -> bool:
    """Выдаёт/продлевает премиум пользователю и фиксирует тариф."""
    if days <= 0:
        return False

    if plan_tier not in (PLAN_BASIC, PLAN_PRO):
        plan_tier = PLAN_PRO

    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        s = result.scalar()
        if not s:
            s = UserSettings(user_id=user_id)
            session.add(s)

        now = datetime.utcnow()
        start_from = now
        if s.is_premium and s.premium_until and s.premium_until > now:
            start_from = s.premium_until

        s.is_premium = True
        s.plan_tier = plan_tier
        s.premium_until = start_from + timedelta(days=days)
        await session.commit()

    logger.info("Premium granted to user %s for %s days (tier=%s)", user_id, days, plan_tier)
    return True


async def revoke_premium(user_id: int) -> bool:
    """Отзывает подписку и возвращает на free-план."""
    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        s = result.scalar()
        if s:
            s.is_premium = False
            s.premium_until = None
            s.plan_tier = PLAN_FREE
            s.weather_notify = False
            await session.commit()
    return True


async def can_use_pdf_export(user_id: int) -> bool:
    return await get_plan_tier(user_id) == PLAN_PRO


async def can_use_weather_notifications(user_id: int) -> bool:
    return await get_plan_tier(user_id) == PLAN_PRO


async def can_use_voice_notes(user_id: int) -> bool:
    return await get_plan_tier(user_id) == PLAN_PRO


def format_subscription_info(settings: UserSettings) -> str:
    """Форматирует информацию о подписке для экрана настроек/оплаты."""
    if _is_subscription_active(settings):
        plan_tier = _normalize_plan(settings.plan_tier, settings.is_premium)
        exp = settings.premium_until.strftime("%d.%m.%Y") if settings.premium_until else "бессрочно"

        if plan_tier == PLAN_BASIC:
            return (
                "⭐️ <b>Текущий тариф: Базовый</b>\n\n"
                f"📅 Действует до: {exp}\n"
                "✅ Безлимитные AI-запросы\n"
                "✅ До 5 питомцев\n"
                "❌ PDF-экспорт\n"
                "❌ Погодные уведомления\n"
                "❌ Голосовые заметки\n\n"
                "Хотите расширенные функции? Перейдите на <b>PRO</b>."
            )

        return (
            "⭐️ <b>Текущий тариф: PRO</b>\n\n"
            f"📅 Действует до: {exp}\n"
            "✅ Безлимитные AI-запросы\n"
            "✅ Неограниченное количество питомцев\n"
            "✅ Экспорт в PDF\n"
            "✅ Погодные уведомления\n"
            "✅ Голосовые заметки"
        )

    today = date.today()
    used = settings.ai_requests_today if settings.last_request_date == today else 0
    remaining = max(FREE_AI_LIMIT - used, 0)

    return (
        "📋 <b>Текущий тариф: Бесплатный</b>\n\n"
        f"🤖 AI-запросы: {remaining}/{FREE_AI_LIMIT} в день\n"
        f"🐾 Питомцы: до {FREE_PET_LIMIT}\n"
        "❌ PDF-экспорт\n"
        "❌ Погодные уведомления\n"
        "❌ Голосовые заметки\n\n"
        "Выберите тариф ниже, чтобы снять ограничения."
    )
