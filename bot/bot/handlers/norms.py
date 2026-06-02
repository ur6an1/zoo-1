"""Обработчики: отображение суточных норм еды и воды."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot import api_client
from bot.keyboards.keyboards import back_to_menu_kb

logger = logging.getLogger(__name__)
router = Router(name="norms")


@router.callback_query(F.data == "food:norms")
async def cb_food_norms(callback: CallbackQuery):
    """Показывает суточные нормы еды/воды и прогресс за сегодня."""
    try:
        norms_data = await api_client.get_norms(callback.from_user.id)

        if norms_data.get("no_pets"):
            await callback.message.edit_text(
                "😕 У вас нет питомцев.\nСначала добавьте питомца в разделе 🐾 Мои питомцы.",
                reply_markup=back_to_menu_kb,
            )
            await callback.answer()
            return

        text = norms_data.get("text", "😕 Нет данных.")
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )

    except Exception as e:
        logger.error(f"Ошибка отображения норм: {e}")
        await callback.message.edit_text(
            "😕 Произошла ошибка при расчёте норм. Попробуйте позже.",
            reply_markup=back_to_menu_kb,
        )

    await callback.answer()
