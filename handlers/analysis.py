"""Обработчики: AI-анализ медицинских анализов питомцев."""

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from config import FREE_AI_LIMIT
from database import async_session
from keyboards.keyboards import add_pet_cta_kb, back_to_menu_kb, cancel_kb, main_menu_kb, pets_list_kb
from models.models import Pet
from services.access import get_owned_pet
from services.analytics import track_user_activity
from services.provider_health import is_ai_operational
from services.subscription import check_ai_limit, refund_ai_limit
from services.vision import analyze_medical_test
from states.states import MedicalTestForm
from utils.helpers import callback_int, format_date

logger = logging.getLogger(__name__)
router = Router(name="analysis")


def _no_ai_message() -> str:
    return (
        "⚠️ AI-функции временно недоступны.\n\n"
        "Мы уже работаем над восстановлением. Попробуйте позже."
    )


def _ai_limit_message() -> str:
    return (
        "⚠️ Дневной лимит AI-запросов исчерпан.\n\n"
        f"На бесплатном плане доступно {FREE_AI_LIMIT} AI-запросов в день.\n"
        "Подключите тариф, чтобы получить безлимит."
    )


def _pet_info_str(pet: Pet) -> str:
    """Формирует строку с данными питомца для промпта."""
    lines = [
        f"Вид: {pet.species}",
        f"Имя: {pet.name}",
    ]
    if pet.breed:
        lines.append(f"Порода: {pet.breed}")
    if pet.birth_date:
        lines.append(f"Дата рождения: {format_date(pet.birth_date)} (возраст: {pet.age_str()})")
    if pet.weight:
        lines.append(f"Вес: {pet.weight} кг")
    return "\n".join(lines)


def _ai_upgrade_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐️ Подписка", callback_data="settings:subscription")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")],
        ]
    )


async def _get_user_pets(user_id: int) -> list[Pet]:
    async with async_session() as session:
        result = await session.execute(select(Pet).where(Pet.user_id == user_id))
        return result.scalars().all()


@router.message(F.text == "🔬 Анализы")
async def analysis_start(message: Message, state: FSMContext):
    """Начало анализа медицинских тестов — выбор питомца."""
    await state.clear()
    await track_user_activity(message.from_user.id, source="analysis")

    if not await is_ai_operational():
        await message.answer(
            _no_ai_message(),
            parse_mode="HTML",
            reply_markup=main_menu_kb,
        )
        return

    pets = await _get_user_pets(message.from_user.id)
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
    if not await is_ai_operational():
        await callback.message.edit_text(
            _no_ai_message(),
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )
        await callback.answer()
        return

    pets = await _get_user_pets(callback.from_user.id)
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

    async with async_session() as session:
        pet = await get_owned_pet(session, callback.from_user.id, pet_id)

    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    await state.set_state(MedicalTestForm.waiting_photo)
    await state.update_data(
        analysis_pet_id=pet_id,
        analysis_pet_info=_pet_info_str(pet),
    )

    await callback.message.edit_text(
        f"🔬 <b>Анализы для {pet.species_emoji} {escape(pet.name)}</b>\n\n"
        "📋 Данные питомца:\n"
        f"• Вид: {escape(pet.species)}\n"
        f"• Порода: {escape(pet.breed) if pet.breed else 'не указана'}\n"
        f"• Возраст: {pet.age_str()}\n"
        f"• Вес: {f'{pet.weight} кг' if pet.weight else 'не указан'}\n\n"
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

    if not await is_ai_operational():
        await message.answer(
            _no_ai_message(),
            reply_markup=main_menu_kb,
        )
        return

    allowed, _remaining = await check_ai_limit(message.from_user.id)
    if not allowed:
        await message.answer(_ai_limit_message(), reply_markup=_ai_upgrade_kb())
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    processing_msg = await message.answer(
        "🔬 <b>AI расшифровывает анализы...</b>\n\n"
        "⏳ Глубокий анализ — это может занять несколько секунд...",
        parse_mode="HTML",
    )

    photo = message.photo[-1]
    try:
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_data = file_bytes.read()
    except Exception as e:
        logger.error("Ошибка скачивания фото анализов: %s", e)
        await refund_ai_limit(message.from_user.id)
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
        await refund_ai_limit(message.from_user.id)
        await processing_msg.edit_text(
            "😕 AI-сервис временно недоступен или не смог обработать фото.\n"
            "Попробуйте позже.",
            reply_markup=back_to_menu_kb,
        )


@router.message(MedicalTestForm.waiting_photo)
async def analysis_not_photo(message: Message):
    """Ожидали фото, получили что-то другое."""
    await message.answer(
        "📷 Пожалуйста, отправьте <b>фото результатов анализов</b>.\n"
        "Или нажмите «Отмена».",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
