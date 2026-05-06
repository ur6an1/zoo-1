"""Обработчики: голосовые заметки (запись, транскрипция, список)."""

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from backend.backend.services.vision import transcribe_voice
from bot import api_client
from bot.keyboards.keyboards import add_pet_cta_kb, back_to_menu_kb, cancel_kb, pets_list_kb
from bot.states.states import VoiceNoteForm
from bot.utils.helpers import callback_int

logger = logging.getLogger(__name__)
router = Router(name="voice")

VOICE_MENU_TEXT = (
    "🎙 <b>Голосовые заметки</b>\n\n"
    "Записывайте наблюдения о питомце голосом — бот автоматически "
    "транскрибирует и сохранит запись.\n\n"
    "Выберите действие:"
)


def _voice_upgrade_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐️ Подписка", callback_data="settings:subscription")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")],
        ]
    )


def _voice_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎙 Добавить заметку", callback_data="voice:add")],
            [InlineKeyboardButton(text="📋 Мои заметки", callback_data="voice:list")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
        ]
    )


@router.message(F.text == "🎙 Голосовые")
async def voice_menu(message: Message, state: FSMContext):
    """Меню голосовых заметок."""
    await state.clear()
    await api_client.track_user_activity(message.from_user.id, source="voice")

    can_voice = await api_client.check_feature_permission(message.from_user.id, "voice_notes")
    if not can_voice:
        await message.answer(
            "🔒 <b>Голосовые заметки доступны только в тарифе PRO.</b>\n\n"
            "Подключите или повысьте подписку, чтобы сохранять голосовые наблюдения.",
            parse_mode="HTML",
            reply_markup=_voice_upgrade_kb(),
        )
        return

    await api_client.track_event(message.from_user.id, "premium_feature_used", source="voice_menu")
    await message.answer(VOICE_MENU_TEXT, parse_mode="HTML", reply_markup=_voice_menu_kb())


@router.callback_query(F.data == "voice:menu")
async def cb_voice_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню голосовых."""
    await state.clear()

    can_voice = await api_client.check_feature_permission(callback.from_user.id, "voice_notes")
    if not can_voice:
        await callback.message.edit_text(
            "🔒 <b>Голосовые заметки доступны только в тарифе PRO.</b>",
            parse_mode="HTML",
            reply_markup=_voice_upgrade_kb(),
        )
        await callback.answer("Доступно только в PRO", show_alert=True)
        return

    await api_client.track_event(callback.from_user.id, "premium_feature_used", source="voice_menu")
    await callback.message.edit_text(VOICE_MENU_TEXT, parse_mode="HTML", reply_markup=_voice_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "voice:add")
async def cb_voice_add(callback: CallbackQuery, state: FSMContext):
    """Начало добавления — выбор питомца."""
    can_voice = await api_client.check_feature_permission(callback.from_user.id, "voice_notes")
    if not can_voice:
        await callback.message.edit_text(
            "🔒 <b>Голосовые заметки доступны только в тарифе PRO.</b>",
            parse_mode="HTML",
            reply_markup=_voice_upgrade_kb(),
        )
        await callback.answer("Доступно только в PRO", show_alert=True)
        return

    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text(
            "😕 У вас нет питомцев.\n"
            "Сначала добавьте питомца в разделе 🐾 Мои питомцы.",
            reply_markup=add_pet_cta_kb,
        )
        await callback.answer()
        return

    await state.set_state(VoiceNoteForm.choosing_pet)
    await callback.message.edit_text(
        "🎙 <b>Голосовая заметка</b>\n\nВыберите питомца:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_voice"),
    )
    await callback.answer()


@router.callback_query(VoiceNoteForm.choosing_pet, F.data.startswith("pet:select_voice:"))
async def cb_voice_pet(callback: CallbackQuery, state: FSMContext):
    """Питомец выбран — ждём голосовое сообщение."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return
    pet = await api_client.get_pet(pet_id, callback.from_user.id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return
    await state.update_data(pet_id=pet_id)
    await state.set_state(VoiceNoteForm.waiting_voice)

    await callback.message.edit_text(
        "🎙 <b>Отправьте голосовое сообщение</b>\n\n"
        "Запишите наблюдения о питомце — я транскрибирую и сохраню.",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(VoiceNoteForm.waiting_voice, F.voice)
async def voice_received(message: Message, state: FSMContext, bot: Bot):
    """Получено голосовое — скачиваем, транскрибируем, сохраняем."""
    data = await state.get_data()
    pet_id = data["pet_id"]

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    processing_msg = await message.answer(
        "🎙 <b>Обрабатываю голосовое сообщение...</b>",
        parse_mode="HTML",
    )

    try:
        file = await bot.get_file(message.voice.file_id)
        file_bytes = await bot.download_file(file.file_path)
        voice_bytes = file_bytes.read()
    except Exception as e:
        logger.error("Ошибка скачивания голосового: %s", e)
        await processing_msg.edit_text(
            "😕 Не удалось загрузить голосовое. Попробуйте ещё раз.",
            reply_markup=cancel_kb,
        )
        return

    transcription = ""
    try:
        transcription = await transcribe_voice(voice_bytes) or ""
    except Exception as e:
        logger.error("Ошибка транскрипции: %s", e)

    await state.clear()

    result = await api_client.create_voice_note(
        pet_id=pet_id,
        user_id=message.from_user.id,
        file_id=message.voice.file_id,
        transcription=transcription,
    )

    if not result:
        await processing_msg.edit_text("😕 Питомец не найден.", reply_markup=back_to_menu_kb)
        return

    pet_name = result.get("pet_name", "—")
    text_preview = transcription[:300] if transcription else "транскрипция недоступна"

    await processing_msg.edit_text(
        "✅ <b>Голосовая заметка сохранена!</b>\n\n"
        f"🐾 Питомец: {escape(pet_name)}\n"
        f"📝 Текст:\n{escape(text_preview)}",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )
    await api_client.track_event(
        message.from_user.id, "premium_feature_used",
        source="voice_note", payload={"pet_id": pet_id},
    )


@router.message(VoiceNoteForm.waiting_voice)
async def voice_not_voice(message: Message):
    """Ожидали голосовое, получили что-то другое."""
    await message.answer(
        "🎙 Пожалуйста, отправьте <b>голосовое сообщение</b>.\n"
        "Или нажмите «Отмена».",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )


@router.callback_query(F.data == "voice:list")
async def cb_voice_list(callback: CallbackQuery):
    """Последние 10 голосовых заметок."""
    can_voice = await api_client.check_feature_permission(callback.from_user.id, "voice_notes")
    if not can_voice:
        await callback.message.edit_text(
            "🔒 <b>Голосовые заметки доступны только в тарифе PRO.</b>",
            parse_mode="HTML",
            reply_markup=_voice_upgrade_kb(),
        )
        await callback.answer("Доступно только в PRO", show_alert=True)
        return

    try:
        notes = await api_client.list_voice_notes(callback.from_user.id)

        if not notes:
            await callback.message.edit_text(
                "🎙 Голосовых заметок пока нет.",
                reply_markup=back_to_menu_kb,
            )
        else:
            lines = [f"🎙 <b>Голосовые заметки</b> (последние {len(notes)})\n"]

            for n in notes:
                pet_label = n.get("pet_label", "?")
                dt = n.get("created_at_str", "—")
                transcription = n.get("transcription", "")
                preview = transcription[:80] + "..." if len(transcription) > 80 else transcription
                if not preview:
                    preview = "без текста"
                lines.append(
                    f"• {escape(pet_label)} — {dt}\n"
                    f"  📝 {escape(preview)}"
                )

            await callback.message.edit_text(
                "\n".join(lines),
                parse_mode="HTML",
                reply_markup=back_to_menu_kb,
            )

    except Exception as e:
        logger.error("Ошибка загрузки голосовых заметок: %s", e)
        await callback.message.edit_text(
            "😕 Ошибка загрузки заметок. Попробуйте позже.",
            reply_markup=back_to_menu_kb,
        )

    await callback.answer()
