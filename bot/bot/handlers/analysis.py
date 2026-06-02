"""Обработчики: AI-анализ медицинских анализов питомцев."""

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from backend.services.vision import analyze_medical_test
from zoo_shared.config import get_settings

from bot import api_client
from bot.keyboards.keyboards import add_pet_cta_kb, back_to_menu_kb, cancel_kb, main_menu_kb, pets_list_kb
from bot.states.states import MedicalTestForm
from bot.utils.helpers import callback_int, format_date

logger = logging.getLogger(__name__)
router = Router(name="analysis")


def _no_ai_message() -> str:
    return "⚠️ AI-функции временно недоступны.\n\nМы уже работаем над восстановлением. Попробуйте позже."


def _ai_limit_message() -> str:
    return (
        "⚠️ Дневной лимит AI-запросов исчерпан.\n\n"
        f"На бесплатном плане доступно {get_settings().FREE_AI_LIMIT} AI-запросов в день.\n"
        "Подключите тариф, чтобы получить безлимит."
    )


def _pet_info_str(pet: dict) -> str:
    """Формирует строку с данными питомца для промпта."""
    lines = [
        f"Вид: {pet.get('species', '')}",
        f"Имя: {pet.get('name', '')}",
    ]
    if pet.get("breed"):
        lines.append(f"Порода: {pet['breed']}")
    if pet.get("birth_date"):
        lines.append(f"Дата рождения: {format_date(pet['birth_date'])} (возраст: {pet.get('age_str', '')})")
    if pet.get("weight"):
        lines.append(f"Вес: {pet['weight']} кг")
    return "\n".join(lines)


def _ai_upgrade_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐️ Подписка", callback_data="settings:subscription")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")],
        ]
    )


@router.message(F.text == "🔬 Анализы")
async def analysis_start(message: Message, state: FSMContext):
    """Начало анализа медицинских тестов — выбор питомца."""
    await state.clear()
    await api_client.track_user_activity(message.from_user.id, source="analysis")

    ai_ok = await api_client.is_ai_operational()
    if not ai_ok:
        await message.answer(_no_ai_message(), parse_mode="HTML", reply_markup=main_menu_kb)
        return

    pets = await api_client.list_pets(message.from_user.id)
    if not pets:
        await message.answer(
            "😕 У вас нет питомцев.\n"
            "Сначала добавьте питомца в разделе 🐾 Мои питомцы,\n"
            "чтобы я мог правильно расшифровать анализы.",
            reply_markup=add_pet_cta_kb,
        )
        return

    await state.set_state(MedicalTestForm.choosing_pet)
    await message.answer(
        "🔬 <b>AI-анализ медицинских тестов</b>\n\n"
        "Отправьте фото результатов анализов (кровь, моча, биохимия и т.д.),\n"
        "и AI расшифрует их с учётом данных вашего питомца.\n\n"
        "Выберите питомца:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_analysis"),
    )


@router.callback_query(F.data == "analysis:start")
async def cb_analysis_start(callback: CallbackQuery, state: FSMContext):
    """Inline-вход в анализ медицинских тестов."""
    await state.clear()
    ai_ok = await api_client.is_ai_operational()
    if not ai_ok:
        await callback.message.edit_text(
            _no_ai_message(),
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )
        await callback.answer()
        return

    pets = await api_client.list_pets(callback.from_user.id)
    if not pets:
        await callback.message.edit_text(
            "😕 У вас нет питомцев.\n"
            "Сначала добавьте питомца в разделе 🐾 Мои питомцы,\n"
            "чтобы я мог правильно расшифровать анализы.",
            reply_markup=add_pet_cta_kb,
        )
        await callback.answer()
        return

    await state.set_state(MedicalTestForm.choosing_pet)
    await callback.message.edit_text(
        "🔬 <b>AI-анализ медицинских тестов</b>\n\n"
        "Отправьте фото результатов анализов (кровь, моча, биохимия и т.д.),\n"
        "и AI расшифрует их с учётом данных вашего питомца.\n\n"
        "Выберите питомца:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_analysis"),
    )
    await callback.answer()


@router.callback_query(MedicalTestForm.choosing_pet, F.data.startswith("pet:select_analysis:"))
async def analysis_pet_chosen(callback: CallbackQuery, state: FSMContext):
    """Питомец выбран — ждём фото анализов."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return

    pet = await api_client.get_pet(pet_id, callback.from_user.id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    await state.set_state(MedicalTestForm.waiting_photo)
    await state.update_data(
        analysis_pet_id=pet_id,
        analysis_pet_info=_pet_info_str(pet),
    )

    species_emoji = pet.get("species_emoji", "🐾")
    breed_str = escape(pet.get("breed", "")) if pet.get("breed") else "не указана"
    weight_str = f"{pet['weight']} кг" if pet.get("weight") else "не указан"

    await callback.message.edit_text(
        f"🔬 <b>Анализы для {species_emoji} {escape(pet['name'])}</b>\n\n"
        "📋 Данные питомца:\n"
        f"• Вид: {escape(pet.get('species', ''))}\n"
        f"• Порода: {breed_str}\n"
        f"• Возраст: {pet.get('age_str', '')}\n"
        f"• Вес: {weight_str}\n\n"
        "📷 <b>Отправьте фото результатов анализов</b>\n"
        "(анализ крови, мочи, биохимия и т.д.)",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(MedicalTestForm.waiting_photo, F.photo)
async def analysis_photo_received(message: Message, state: FSMContext, bot: Bot):
    """Получено фото анализов — отправляем AI."""
    data = await state.get_data()
    pet_info = data.get("analysis_pet_info", "Данные не указаны")
    await state.clear()

    ai_ok = await api_client.is_ai_operational()
    if not ai_ok:
        await message.answer(_no_ai_message(), reply_markup=main_menu_kb)
        return

    can_use, _remaining = await api_client.check_ai_limit(message.from_user.id)
    if not can_use:
        await message.answer(_ai_limit_message(), reply_markup=_ai_upgrade_kb())
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    processing_msg = await message.answer(
        "🔬 <b>AI расшифровывает анализы...</b>\n\n⏳ Глубокий анализ — это может занять несколько секунд...",
        parse_mode="HTML",
    )

    photo = message.photo[-1]
    try:
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_data = file_bytes.read()
    except Exception as e:
        logger.error("Ошибка скачивания фото анализов: %s", e)
        await api_client.refund_ai_limit(message.from_user.id)
        await processing_msg.edit_text(
            "😕 Не удалось загрузить фото. Попробуйте ещё раз.",
            reply_markup=back_to_menu_kb,
        )
        return

    try:
        result = await analyze_medical_test(image_data, pet_info)
    except Exception as e:
        logger.error("Ошибка AI-анализа: %s", e)
        result = None

    if result:
        if len(result) > 4000:
            result = result[:4000] + "..."
        safe_result = escape(result)
        await processing_msg.edit_text(
            f"🔬 <b>Результат расшифровки анализов:</b>\n\n{safe_result}",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )
    else:
        await api_client.refund_ai_limit(message.from_user.id)
        await processing_msg.edit_text(
            "😕 AI-сервис временно недоступен или не смог обработать фото.\nПопробуйте позже.",
            reply_markup=back_to_menu_kb,
        )


@router.message(MedicalTestForm.waiting_photo)
async def analysis_not_photo(message: Message):
    """Ожидали фото, получили что-то другое."""
    await message.answer(
        "📷 Пожалуйста, отправьте <b>фото результатов анализов</b>.\nИли нажмите «Отмена».",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
