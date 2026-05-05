"""Обработчики: советы по уходу, FAQ, питание."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from keyboards.keyboards import back_to_menu_kb, tips_menu_kb
from services.content import FAQ_TEXT, NUTRITION_TEXT, TIPS

logger = logging.getLogger(__name__)
router = Router(name="tips")


@router.message(F.text == "💡 Советы")
async def tips_menu(message: Message):
    await message.answer(
        "💡 <b>Полезные советы</b>\n\nВыберите тему:",
        parse_mode="HTML",
        reply_markup=tips_menu_kb,
    )


@router.callback_query(F.data == "tips:menu")
async def cb_tips_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "💡 <b>Полезные советы</b>\n\nВыберите тему:",
        parse_mode="HTML",
        reply_markup=tips_menu_kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tips:"))
async def cb_tips(callback: CallbackQuery):
    """Показать совет по категории."""
    topic = callback.data.split(":")[1]

    if topic == "faq":
        text = FAQ_TEXT
    elif topic == "nutrition":
        text = NUTRITION_TEXT
    else:
        text = TIPS.get(topic, TIPS.get("другое", "Совет не найден."))

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer()
