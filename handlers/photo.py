"""Обработчики: распознавание фото, подбор питания по фото, AI-консультант."""

import logging
from html import escape
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from config import FREE_AI_LIMIT
from database import async_session
from models.models import Pet
from states.states import NutritionForm, SymptomsForm
from keyboards.keyboards import (
    add_pet_cta_kb,
    photo_menu_kb,
    back_to_menu_kb,
    main_menu_kb,
    cancel_kb,
    pets_list_kb,
)
from services.access import get_owned_pet
from services.analytics import track_user_activity
from services.vision import (
    analyze_pet_photo,
    analyze_food_photo,
    analyze_food_for_pet,
    consult_symptoms,
    transcribe_voice,
)
from utils.helpers import callback_int, format_date
from services.provider_health import is_ai_operational
from services.subscription import check_ai_limit, refund_ai_limit

logger = logging.getLogger(__name__)
router = Router(name="photo")


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


def _ai_upgrade_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐️ Подписка", callback_data="settings:subscription")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")],
        ]
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


async def _get_user_pets(user_id: int) -> list[Pet]:
    async with async_session() as session:
        result = await session.execute(select(Pet).where(Pet.user_id == user_id))
        return result.scalars().all()


# ═══════════════════════════════════════════════════
#  МЕНЮ РАСПОЗНАВАНИЯ ФОТО
# ═══════════════════════════════════════════════════


@router.message(F.text == "📷 Распознать фото")
async def photo_menu(message: Message, state: FSMContext):
    """Меню распознавания фото."""
    await state.clear()
    await track_user_activity(message.from_user.id, source="photo")
    if not await is_ai_operational():
        await message.answer(_no_ai_message(), parse_mode="HTML", reply_markup=main_menu_kb)
        return

    await message.answer(
        "📷 <b>Распознавание фото с AI</b>\n\n"
        "Продвинутый AI-анализ фото вашего питомца или корма!\n\n"
        "Выберите тип анализа или просто отправьте фото:",
        parse_mode="HTML",
        reply_markup=photo_menu_kb,
    )


@router.callback_query(F.data == "photo:menu")
async def cb_photo_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await is_ai_operational():
        await callback.message.edit_text(
            _no_ai_message(),
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "📷 <b>Распознавание фото с AI</b>\n\n"
        "Выберите тип анализа или просто отправьте фото:",
        parse_mode="HTML",
        reply_markup=photo_menu_kb,
    )
    await callback.answer()


@router.callback_query(F.data == "photo:pet")
async def cb_photo_pet(callback: CallbackQuery, state: FSMContext):
    if not await is_ai_operational():
        await callback.message.edit_text(
            _no_ai_message(),
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )
        await callback.answer()
        return

    await state.update_data(photo_mode="pet")
    await callback.message.edit_text(
        "🐾 <b>Анализ фото питомца</b>\n\n"
        "Отправьте фото, и я определю:\n"
        "• Вид и породу\n"
        "• Примерный возраст\n"
        "• Состояние здоровья\n"
        "• Рекомендации по уходу\n\n"
        "📷 Отправьте фото 👇",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer()


@router.callback_query(F.data == "photo:food")
async def cb_photo_food(callback: CallbackQuery, state: FSMContext):
    if not await is_ai_operational():
        await callback.message.edit_text(
            _no_ai_message(),
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )
        await callback.answer()
        return

    await state.update_data(photo_mode="food")
    await callback.message.edit_text(
        "🍽 <b>Анализ фото корма/еды</b>\n\n"
        "Отправьте фото, и я определю:\n"
        "• Тип корма\n"
        "• Подходит ли для питомца\n"
        "• Примерную порцию\n\n"
        "📷 Отправьте фото 👇",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer()


# ═══════════════════════════════════════════════════
#  ПОДБОР ПИТАНИЯ ПО ФОТО КОРМА
# ═══════════════════════════════════════════════════


@router.message(F.text == "🥗 Подбор питания")
async def nutrition_start(message: Message, state: FSMContext):
    """Начало подбора питания — выбор питомца."""
    await state.clear()
    await track_user_activity(message.from_user.id, source="nutrition")
    if not await is_ai_operational():
        await message.answer(_no_ai_message(), parse_mode="HTML", reply_markup=main_menu_kb)
        return

    pets = await _get_user_pets(message.from_user.id)
    if not pets:
        await message.answer(
            "😕 У вас нет питомцев.\n"
            "Сначала добавьте питомца в разделе 🐾 Мои питомцы,\n"
            "чтобы я мог рассчитать порции под его вес и возраст.",
            reply_markup=add_pet_cta_kb,
        )
        return

    await state.set_state(NutritionForm.choosing_pet)
    await message.answer(
        "🥗 <b>Подбор питания</b>\n\n"
        "Выберите питомца, для которого подбираем корм.\n"
        "Я учту его вид, породу, вес и возраст для расчёта порций:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_nutrition"),
    )


@router.callback_query(F.data == "ai:nutrition")
async def cb_nutrition_start(callback: CallbackQuery, state: FSMContext):
    """Inline-вход в подбор питания."""
    await state.clear()
    if not await is_ai_operational():
        await callback.message.edit_text(_no_ai_message(), parse_mode="HTML", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    pets = await _get_user_pets(callback.from_user.id)
    if not pets:
        await callback.message.edit_text(
            "😕 У вас нет питомцев.\n"
            "Сначала добавьте питомца в разделе 🐾 Мои питомцы,\n"
            "чтобы я мог рассчитать порции под его вес и возраст.",
            reply_markup=add_pet_cta_kb,
        )
        await callback.answer()
        return

    await state.set_state(NutritionForm.choosing_pet)
    await callback.message.edit_text(
        "🥗 <b>Подбор питания</b>\n\n"
        "Выберите питомца, для которого подбираем корм.\n"
        "Я учту его вид, породу, вес и возраст для расчёта порций:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_nutrition"),
    )
    await callback.answer()


@router.callback_query(NutritionForm.choosing_pet, F.data.startswith("pet:select_nutrition:"))
async def nutrition_pet_chosen(callback: CallbackQuery, state: FSMContext):
    """Питомец выбран — ждём фото корма."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return
    async with async_session() as session:
        pet = await get_owned_pet(session, callback.from_user.id, pet_id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    await state.set_state(NutritionForm.waiting_photo)
    await state.update_data(nutrition_pet_id=pet_id, nutrition_pet_info=_pet_info_str(pet))

    await callback.message.edit_text(
        f"🥗 <b>Подбор питания для {pet.species_emoji} {escape(pet.name)}</b>\n\n"
        f"📋 Данные питомца:\n"
        f"• Вид: {escape(pet.species)}\n"
        f"• Порода: {escape(pet.breed) if pet.breed else 'не указана'}\n"
        f"• Возраст: {pet.age_str()}\n"
        f"• Вес: {f'{pet.weight} кг' if pet.weight else 'не указан'}\n\n"
        f"📷 <b>Теперь отправьте фото корма</b> (пачка, банка, этикетка)\n"
        f"и я рассчитаю порции и дам рекомендации!",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(NutritionForm.waiting_photo, F.photo)
async def nutrition_photo_received(message: Message, state: FSMContext, bot: Bot):
    """Получено фото корма — анализируем и подбираем порции."""
    data = await state.get_data()
    pet_info = data.get("nutrition_pet_info", "Данные не указаны")
    await state.clear()

    if not await is_ai_operational():
        await message.answer(_no_ai_message(), reply_markup=main_menu_kb)
        return

    allowed, _remaining = await check_ai_limit(message.from_user.id)
    if not allowed:
        await message.answer(_ai_limit_message(), reply_markup=_ai_upgrade_kb())
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    processing_msg = await message.answer(
        "🔍 <b>AI анализирует корм и рассчитывает порции...</b>\n\n"
        "⏳ Глубокий анализ — несколько секунд...",
        parse_mode="HTML",
    )

    photo = message.photo[-1]
    try:
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_data = file_bytes.read()
    except Exception as e:
        logger.error(f"Ошибка скачивания фото: {e}")
        await refund_ai_limit(message.from_user.id)
        await processing_msg.edit_text("😕 Не удалось загрузить фото. Попробуйте ещё раз.", reply_markup=back_to_menu_kb)
        return

    result = await analyze_food_for_pet(image_data, pet_info)

    if result:
        if len(result) > 4000:
            result = result[:4000] + "..."
        safe_result = escape(result)
        await processing_msg.edit_text(
            f"🥗 <b>Результат подбора питания:</b>\n\n{safe_result}",
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


@router.message(NutritionForm.waiting_photo)
async def nutrition_not_photo(message: Message):
    """Ожидали фото, получили текст."""
    await message.answer(
        "📷 Пожалуйста, отправьте <b>фото корма</b> (пачка, банка, этикетка).\n"
        "Или нажмите «Отмена».",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )


# ═══════════════════════════════════════════════════
#  AI-КОНСУЛЬТАНТ ПО СИМПТОМАМ
# ═══════════════════════════════════════════════════


@router.message(F.text == "🩺 AI-консультант")
async def symptoms_start(message: Message, state: FSMContext):
    """Начало консультации — выбор питомца."""
    await state.clear()
    await track_user_activity(message.from_user.id, source="symptoms")
    if not await is_ai_operational():
        await message.answer(_no_ai_message(), parse_mode="HTML", reply_markup=main_menu_kb)
        return

    pets = await _get_user_pets(message.from_user.id)
    if not pets:
        await message.answer(
            "😕 У вас нет питомцев.\n"
            "Добавьте питомца в разделе 🐾 Мои питомцы,\n"
            "чтобы я мог дать более точные рекомендации.",
            reply_markup=add_pet_cta_kb,
        )
        return

    await state.set_state(SymptomsForm.choosing_pet)
    await message.answer(
        "🩺 <b>AI-консультант</b>\n\n"
        "Выберите питомца, о котором хотите спросить.\n"
        "Я учту его данные для более точного ответа:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_symptoms"),
    )


@router.callback_query(F.data == "ai:symptoms")
async def cb_symptoms_start(callback: CallbackQuery, state: FSMContext):
    """Inline-вход в консультацию по симптомам."""
    await state.clear()
    if not await is_ai_operational():
        await callback.message.edit_text(_no_ai_message(), parse_mode="HTML", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    pets = await _get_user_pets(callback.from_user.id)
    if not pets:
        await callback.message.edit_text(
            "😕 У вас нет питомцев.\n"
            "Добавьте питомца в разделе 🐾 Мои питомцы,\n"
            "чтобы я мог дать более точные рекомендации.",
            reply_markup=add_pet_cta_kb,
        )
        await callback.answer()
        return

    await state.set_state(SymptomsForm.choosing_pet)
    await callback.message.edit_text(
        "🩺 <b>AI-консультант</b>\n\n"
        "Выберите питомца, о котором хотите спросить.\n"
        "Я учту его данные для более точного ответа:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_symptoms"),
    )
    await callback.answer()


@router.callback_query(SymptomsForm.choosing_pet, F.data.startswith("pet:select_symptoms:"))
async def symptoms_pet_chosen(callback: CallbackQuery, state: FSMContext):
    """Питомец выбран — ждём описание симптомов."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return
    async with async_session() as session:
        pet = await get_owned_pet(session, callback.from_user.id, pet_id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    await state.set_state(SymptomsForm.waiting_text)
    await state.update_data(symptoms_pet_id=pet_id, symptoms_pet_info=_pet_info_str(pet))

    await callback.message.edit_text(
        f"🩺 <b>Консультация по {pet.species_emoji} {escape(pet.name)}</b>\n\n"
        f"Опишите симптомы или ситуацию:\n\n"
        f"<i>Примеры:</i>\n"
        f"• «Кот не ест второй день, вялый, нос сухой»\n"
        f"• «Собака хромает на заднюю лапу после прогулки»\n"
        f"• «Попугай чихает и перья взъерошены»\n\n"
        f"✏️ Напишите текст или 🎙 отправьте голосовое 👇",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(SymptomsForm.waiting_text, F.text)
async def symptoms_text_received(message: Message, state: FSMContext, bot: Bot):
    """Получено описание симптомов — отправляем AI."""
    text = message.text.strip()
    if len(text) < 5:
        await message.answer(
            "⚠️ Опишите симптомы подробнее (минимум 5 символов).",
            reply_markup=cancel_kb,
        )
        return

    data = await state.get_data()
    pet_info = data.get("symptoms_pet_info", "Данные не указаны")

    if not await is_ai_operational():
        await message.answer(_no_ai_message(), reply_markup=cancel_kb)
        return

    allowed, _remaining = await check_ai_limit(message.from_user.id)
    if not allowed:
        await message.answer(_ai_limit_message(), reply_markup=_ai_upgrade_kb())
        return

    # Не очищаем state — позволяем задавать вопросы подряд
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    processing_msg = await message.answer(
        "🔍 <b>AI анализирует симптомы...</b>\n\n"
        "⏳ Глубокий анализ — несколько секунд...",
        parse_mode="HTML",
    )

    result = await consult_symptoms(text, pet_info)

    if result:
        if len(result) > 4000:
            result = result[:4000] + "..."
        safe_result = escape(result)
        await processing_msg.edit_text(
            f"🩺 <b>Консультация AI:</b>\n\n{safe_result}\n\n"
            f"─────────────────\n"
            f"💬 Можете задать ещё вопрос или нажать «Отмена» для выхода.",
            parse_mode="HTML",
            reply_markup=cancel_kb,
        )
    else:
        await refund_ai_limit(message.from_user.id)
        await processing_msg.edit_text(
            "😕 AI-сервис временно недоступен. Попробуйте позже.",
            reply_markup=cancel_kb,
        )


@router.message(SymptomsForm.waiting_text, F.voice)
async def symptoms_voice_received(message: Message, state: FSMContext, bot: Bot):
    """Получено голосовое — расшифровываем и отправляем AI."""
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    transcribing_msg = await message.answer(
        "🎙 <b>Расшифровываю голосовое...</b>",
        parse_mode="HTML",
    )

    if not await is_ai_operational():
        await transcribing_msg.edit_text(_no_ai_message(), reply_markup=cancel_kb)
        return

    allowed, _remaining = await check_ai_limit(message.from_user.id)
    if not allowed:
        await transcribing_msg.edit_text(_ai_limit_message(), reply_markup=_ai_upgrade_kb())
        return

    try:
        voice_file = await bot.get_file(message.voice.file_id)
        voice_data = await bot.download_file(voice_file.file_path)
        voice_bytes = voice_data.read()
    except Exception as e:
        logger.error(f"Ошибка скачивания голосового: {e}")
        await refund_ai_limit(message.from_user.id)
        await transcribing_msg.edit_text("😕 Не удалось загрузить голосовое.", reply_markup=cancel_kb)
        return

    text = await transcribe_voice(voice_bytes)

    if not text or len(text.strip()) < 3:
        await refund_ai_limit(message.from_user.id)
        await transcribing_msg.edit_text(
            "😕 Не удалось распознать речь. Попробуйте ещё раз или напишите текстом.",
            reply_markup=cancel_kb,
        )
        return

    await transcribing_msg.edit_text(
        f"🎙 <b>Распознано:</b>\n<i>«{escape(text)}»</i>\n\n"
        f"🔍 <b>Анализирую...</b>",
        parse_mode="HTML",
    )

    data = await state.get_data()
    pet_info = data.get("symptoms_pet_info", "Данные не указаны")

    result = await consult_symptoms(text, pet_info)

    if result:
        if len(result) > 4000:
            result = result[:4000] + "..."
        safe_result = escape(result)
        await transcribing_msg.edit_text(
            f"🎙 <b>Вы сказали:</b> <i>«{escape(text)}»</i>\n\n"
            f"🩺 <b>Консультация AI:</b>\n\n{safe_result}\n\n"
            f"─────────────────\n"
            f"💬 Можете задать ещё вопрос (текст или голос) или «Отмена».",
            parse_mode="HTML",
            reply_markup=cancel_kb,
        )
    else:
        await refund_ai_limit(message.from_user.id)
        await transcribing_msg.edit_text(
            f"🎙 <b>Распознано:</b> <i>«{escape(text)}»</i>\n\n"
            "😕 AI-сервис временно недоступен. Попробуйте позже.",
            parse_mode="HTML",
            reply_markup=cancel_kb,
        )


@router.message(SymptomsForm.waiting_text)
async def symptoms_not_text(message: Message):
    """Ожидали текст или голос, получили что-то другое."""
    await message.answer(
        "✏️ <b>Опишите симптомы текстом</b> или 🎙 <b>отправьте голосовое</b>.\n"
        "Или нажмите «Отмена».",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )


# ═══════════════════════════════════════════════════
#  ОБРАБОТКА ФОТО (общий — распознавание питомца/корма)
# ═══════════════════════════════════════════════════


@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext, bot: Bot):
    """Обработка входящего фото — распознавание через AI."""
    current_state = await state.get_state()

    # Не перехватываем фото из других FSM-потоков (добавление питомца, документы и т.д.)
    from states.states import CompareForm, MedicalTestForm, PetForm, EditPetForm, DocumentForm, NutritionForm
    protected_states = [
        PetForm.photo.state,
        EditPetForm.editing_photo.state,
        DocumentForm.photo.state,
        NutritionForm.waiting_photo.state,
        MedicalTestForm.waiting_photo.state,
        CompareForm.waiting_photo_1.state,
        CompareForm.waiting_photo_2.state,
    ]
    if current_state in protected_states:
        return

    data = await state.get_data()
    mode = data.get("photo_mode")

    # Только если пользователь явно вошёл в режим распознавания
    if mode is None:
        return

    if not await is_ai_operational():
        await message.answer(_no_ai_message(), reply_markup=photo_menu_kb)
        return

    allowed, _remaining = await check_ai_limit(message.from_user.id)
    if not allowed:
        await message.answer(_ai_limit_message(), reply_markup=_ai_upgrade_kb())
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    processing_msg = await message.answer(
        "🔍 <b>AI анализирует фото...</b>\n"
        "⏳ Глубокий анализ — несколько секунд...",
        parse_mode="HTML",
    )

    photo = message.photo[-1]
    try:
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_data = file_bytes.read()
    except Exception as e:
        logger.error(f"Ошибка скачивания фото: {e}")
        await refund_ai_limit(message.from_user.id)
        await processing_msg.edit_text("😕 Не удалось загрузить фото.", reply_markup=back_to_menu_kb)
        return

    if mode == "food":
        result = await analyze_food_photo(image_data)
    else:
        result = await analyze_pet_photo(image_data)

    await state.update_data(photo_mode=None)

    if result:
        if len(result) > 4000:
            result = result[:4000] + "..."
        safe_result = escape(result)
        await processing_msg.edit_text(
            f"✨ <b>Результат анализа:</b>\n\n{safe_result}",
            parse_mode="HTML",
            reply_markup=photo_menu_kb,
        )
    else:
        await refund_ai_limit(message.from_user.id)
        await processing_msg.edit_text(
            "😕 AI-сервис временно недоступен или не смог обработать фото.\n"
            "Попробуйте позже.",
            reply_markup=photo_menu_kb,
        )


# ═══════════════════════════════════════════════════
#  ГОЛОСОВОЕ ИЗ ЛЮБОГО МЕСТА → AI-КОНСУЛЬТАНТ
# ═══════════════════════════════════════════════════


@router.message(F.voice)
async def handle_voice_anywhere(message: Message, state: FSMContext, bot: Bot):
    """Голосовое сообщение из любого места — расшифровать и отправить AI."""
    current_state = await state.get_state()
    # Не перехватываем если уже в каком-то голосовом потоке
    from states.states import VoiceNoteForm
    if current_state in [VoiceNoteForm.waiting_voice.state]:
        return

    if not await is_ai_operational():
        await message.answer(_no_ai_message(), reply_markup=back_to_menu_kb)
        return

    allowed, _remaining = await check_ai_limit(message.from_user.id)
    if not allowed:
        await message.answer(_ai_limit_message(), reply_markup=_ai_upgrade_kb())
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    processing_msg = await message.answer(
        "🎙 <b>Расшифровываю голосовое...</b>",
        parse_mode="HTML",
    )

    # Скачиваем и расшифровываем
    try:
        voice_file = await bot.get_file(message.voice.file_id)
        voice_data = await bot.download_file(voice_file.file_path)
        voice_bytes = voice_data.read()
    except Exception as e:
        logger.error(f"Ошибка скачивания голосового: {e}")
        await refund_ai_limit(message.from_user.id)
        await processing_msg.edit_text(
            "😕 Не удалось загрузить голосовое.",
            reply_markup=back_to_menu_kb,
        )
        return

    text = await transcribe_voice(voice_bytes)

    if not text or len(text.strip()) < 3:
        await refund_ai_limit(message.from_user.id)
        await processing_msg.edit_text(
            "😕 Не удалось распознать речь. Попробуйте ещё раз чётче.",
            reply_markup=back_to_menu_kb,
        )
        return

    # Получаем первого питомца пользователя для контекста
    pets = await _get_user_pets(message.from_user.id)
    if pets:
        pet = pets[0]
        pet_info = _pet_info_str(pet)
    else:
        pet_info = "Питомец не указан"

    await processing_msg.edit_text(
        f"🎙 <b>Распознано:</b>\n<i>«{escape(text)}»</i>\n\n"
        f"🔍 <b>AI анализирует...</b>",
        parse_mode="HTML",
    )

    result = await consult_symptoms(text, pet_info)

    if result:
        if len(result) > 4000:
            result = result[:4000] + "..."
        safe_result = escape(result)

        pet_note = f" (для {pet.species_emoji} {escape(pet.name)})" if pets else ""
        await processing_msg.edit_text(
            f"🎙 <b>Вы сказали:</b> <i>«{escape(text)}»</i>{pet_note}\n\n"
            f"🩺 <b>AI-консультация:</b>\n\n{safe_result}",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )
    else:
        await refund_ai_limit(message.from_user.id)
        await processing_msg.edit_text(
            f"🎙 <b>Распознано:</b> <i>«{escape(text)}»</i>\n\n"
            "😕 AI-сервис временно недоступен. Попробуйте позже.",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )
