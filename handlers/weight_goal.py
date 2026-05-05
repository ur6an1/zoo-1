"""Обработчики: целевой вес питомца и прогресс."""

import logging
from html import escape
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database import async_session
from models.models import Pet
from states.states import WeightGoalForm
from keyboards.keyboards import back_to_menu_kb, cancel_kb, pets_list_kb
from services.access import get_owned_pet
from services.norms import weight_progress
from utils.helpers import callback_int, parse_weight

logger = logging.getLogger(__name__)
router = Router(name="weight_goal")


# ═══════════════════════════════════════════════════
#  ПРОСМОТР ЦЕЛИ ПО ВЕСУ
# ═══════════════════════════════════════════════════


@router.callback_query(F.data.startswith("pet:weight_goal:"))
async def cb_weight_goal(callback: CallbackQuery):
    """Показывает текущий вес, целевой вес и прогресс."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return

    async with async_session() as session:
        pet = await get_owned_pet(session, callback.from_user.id, pet_id)

    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    lines = [
        f"🎯 <b>Целевой вес — {pet.species_emoji} {escape(pet.name)}</b>\n",
        f"⚖️ Текущий вес: <b>{f'{pet.weight} кг' if pet.weight else 'не указан'}</b>",
        f"🎯 Целевой вес: <b>{f'{pet.target_weight} кг' if pet.target_weight else 'не установлен'}</b>",
    ]

    progress = weight_progress(pet.weight, pet.target_weight)
    if progress:
        lines.append(f"\n📊 {progress}")

    # Проверяем, достигнута ли цель
    if (
        pet.weight
        and pet.target_weight
        and abs(pet.weight - pet.target_weight) < 0.1
    ):
        lines.append("\n🎉 <b>Поздравляем! Целевой вес достигнут!</b>")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🎯 Установить цель",
                callback_data=f"weight_goal:set:{pet.id}",
            )],
            [InlineKeyboardButton(
                text="◀️ К профилю",
                callback_data=f"pet:view:{pet.id}",
            )],
        ]
    )

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=kb,
    )
    await callback.answer()


# ═══════════════════════════════════════════════════
#  УСТАНОВКА ЦЕЛИ
# ═══════════════════════════════════════════════════


@router.callback_query(F.data.startswith("weight_goal:set:"))
async def cb_weight_goal_set(callback: CallbackQuery, state: FSMContext):
    """Начало установки целевого веса — запоминаем питомца."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return

    async with async_session() as session:
        pet = await get_owned_pet(session, callback.from_user.id, pet_id)

    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    await state.set_state(WeightGoalForm.target)
    await state.update_data(goal_pet_id=pet_id)

    await callback.message.edit_text(
        f"🎯 <b>Установка целевого веса для {pet.species_emoji} {escape(pet.name)}</b>\n\n"
        f"Текущий вес: <b>{f'{pet.weight} кг' if pet.weight else 'не указан'}</b>\n\n"
        f"Введите желаемый вес в кг (например: <b>4.5</b>):",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(WeightGoalForm.target, F.text)
async def weight_goal_target_value(message: Message, state: FSMContext):
    """Получено значение целевого веса."""
    target = parse_weight(message.text)
    if target is None:
        await message.answer(
            "⚠️ Введите корректный вес в кг (например: <b>4.5</b>).",
            parse_mode="HTML",
            reply_markup=cancel_kb,
        )
        return

    data = await state.get_data()
    pet_id = data.get("goal_pet_id")
    await state.clear()

    if not pet_id:
        await message.answer("😕 Ошибка. Попробуйте заново.", reply_markup=back_to_menu_kb)
        return

    try:
        async with async_session() as session:
            pet = await get_owned_pet(session, message.from_user.id, pet_id)
            if not pet:
                await message.answer("😕 Питомец не найден.", reply_markup=back_to_menu_kb)
                return

            pet.target_weight = target
            await session.commit()

        progress = weight_progress(pet.weight, target)
        lines = [
            f"✅ <b>Целевой вес установлен!</b>\n",
            f"{pet.species_emoji} {escape(pet.name)}",
            f"⚖️ Текущий вес: <b>{f'{pet.weight} кг' if pet.weight else 'не указан'}</b>",
            f"🎯 Цель: <b>{target} кг</b>",
        ]
        if progress:
            lines.append(f"\n📊 {progress}")

        if pet.weight and abs(pet.weight - target) < 0.1:
            lines.append("\n🎉 <b>Ура! Цель уже достигнута!</b>")

        await message.answer(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )

    except Exception as e:
        logger.error(f"Ошибка сохранения целевого веса: {e}")
        await message.answer(
            "😕 Не удалось сохранить целевой вес. Попробуйте ещё раз.",
            reply_markup=back_to_menu_kb,
        )


@router.message(WeightGoalForm.target)
async def weight_goal_target_invalid(message: Message):
    """Получили не текст в состоянии ввода целевого веса."""
    await message.answer(
        "⚠️ Пожалуйста, введите <b>число</b> — целевой вес в кг.",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
