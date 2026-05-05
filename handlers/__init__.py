"""Регистрация всех роутеров."""

from aiogram import Router

from handlers.analysis import router as analysis_router
from handlers.calendar_view import router as calendar_router
from handlers.common import router as common_router
from handlers.compare import router as compare_router
from handlers.emergency import router as emergency_router
from handlers.food import router as food_router
from handlers.medical import router as medical_router
from handlers.norms import router as norms_router
from handlers.payment import router as payment_router
from handlers.pets import router as pets_router
from handlers.photo import router as photo_router
from handlers.reminders import router as reminders_router
from handlers.subscription import router as subscription_router
from handlers.tips import router as tips_router
from handlers.voice import router as voice_router
from handlers.weather_handler import router as weather_handler_router
from handlers.weight_goal import router as weight_goal_router


def get_all_routers() -> list[Router]:
    """Возвращает список всех роутеров бота."""
    return [
        common_router,
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
