"""Обработчики: целевой вес питомца и прогресс."""

import logging
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from backend.backend.services.norms import weight_progress
from bot import api_client
from bot.keyboards.keyboards import back_to_menu_kb, cancel_kb
from bot.states.states import WeightGoalForm
from bot.utils.helpers import callback_int, parse_weight

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

    pet = await api_client.get_pet(pet_id, callback.from_user.id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    species_emoji = pet.get("species_emoji", "🐾")
    weight = pet.get("weight")
    target_weight = pet.get("target_weight")
    weight_str = f"{weight} кг" if weight else "не указан"
    target_str = f"{target_weight} кг" if target_weight else "не установлен"

    lines = [
        f"🎯 <b>Целевой вес — {species_emoji} {escape(pet['name'])}</b>\n",
        f"⚖️ Текущий вес: <b>{weight_str}</b>",
        f"🎯 Целевой вес: <b>{target_str}</b>",
    ]

    progress = weight_progress(weight, target_weight)
    if progress:
        lines.append(f"\n📊 {progress}")

    if weight and target_weight and abs(weight - target_weight) < 0.1:
        lines.append("\n🎉 <b>Поздравляем! Целевой вес достигнут!</b>")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🎯 Установить цель",
                callback_data=f"weight_goal:set:{pet_id}",
            )],
            [InlineKeyboardButton(
                text="◀️ К профилю",
                callback_data=f"pet:view:{pet_id}",
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

    pet = await api_client.get_pet(pet_id, callback.from_user.id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    await state.set_state(WeightGoalForm.target)
    await state.update_data(goal_pet_id=pet_id)

    species_emoji = pet.get("species_emoji", "🐾")
    weight_str = f"{pet['weight']} кг" if pet.get("weight") else "не указан"

    await callback.message.edit_text(
        f"🎯 <b>Установка целевого веса для {species_emoji} {escape(pet['name'])}</b>\n\n"
        f"Текущий вес: <b>{weight_str}</b>\n\n"
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
        updated = await api_client.update_pet(pet_id, message.from_user.id, target_weight=target)
        if not updated:
            await message.answer("😕 Питомец не найден.", reply_markup=back_to_menu_kb)
            return

        weight = updated.get("weight")
        species_emoji = updated.get("species_emoji", "🐾")
        pet_name = updated.get("name", "")

        progress = weight_progress(weight, target)
        lines = [
            "✅ <b>Целевой вес установлен!</b>\n",
            f"{species_emoji} {escape(pet_name)}",
            f"⚖️ Текущий вес: <b>{f'{weight} кг' if weight else 'не указан'}</b>",
            f"🎯 Цель: <b>{target} кг</b>",
        ]
        if progress:
            lines.append(f"\n📊 {progress}")

        if weight and abs(weight - target) < 0.1:
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
