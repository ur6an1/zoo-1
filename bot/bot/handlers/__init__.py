"""Регистрация всех роутеров."""

from aiogram import Router

from bot.handlers.analysis import router as analysis_router
from bot.handlers.calendar_view import router as calendar_router
from bot.handlers.common import router as common_router
from bot.handlers.compare import router as compare_router
from bot.handlers.emergency import router as emergency_router
from bot.handlers.food import router as food_router
from bot.handlers.legal import router as legal_router
from bot.handlers.medical import router as medical_router
from bot.handlers.norms import router as norms_router
from bot.handlers.payment import router as payment_router
from bot.handlers.pets import router as pets_router
from bot.handlers.photo import router as photo_router
from bot.handlers.reminders import router as reminders_router
from bot.handlers.subscription import router as subscription_router
from bot.handlers.tips import router as tips_router
from bot.handlers.voice import router as voice_router
from bot.handlers.weather_handler import router as weather_handler_router
from bot.handlers.weight_goal import router as weight_goal_router


def get_all_routers() -> list[Router]:
    """Возвращает список всех роутеров бота."""
    return [
        common_router,
        legal_router,
        pets_router,
        reminders_router,
        medical_router,
        food_router,
        tips_router,
        emergency_router,
        analysis_router,
        photo_router,
        norms_router,
        compare_router,
        voice_router,
        calendar_router,
        weight_goal_router,
        subscription_router,
        payment_router,
        weather_handler_router,
    ]
