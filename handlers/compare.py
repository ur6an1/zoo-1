"""Обработчики: сравнение двух кормов по фото."""

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import FREE_AI_LIMIT
from keyboards.keyboards import back_to_menu_kb, cancel_kb, photo_menu_kb
from services.provider_health import is_ai_operational
from services.subscription import check_ai_limit, refund_ai_limit
from services.vision import compare_two_foods
from states.states import CompareForm

logger = logging.getLogger(__name__)
router = Router(name="compare")


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


@router.callback_query(F.data == "photo:compare")
async def cb_compare_start(callback: CallbackQuery, state: FSMContext):
    """Начало сравнения — запрос первого фото."""
    if not await is_ai_operational():
        await callback.message.edit_text(
            _no_ai_message(),
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )
        await callback.answer()
        return

    await state.set_state(CompareForm.waiting_photo_1)
    await callback.message.edit_text(
        "⚖️ <b>Сравнение двух кормов</b>\n\n"
        "📷 Отправьте фото <b>первого</b> корма 👇\n"
        "(пачка, банка или этикетка)",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(CompareForm.waiting_photo_1, F.photo)
async def compare_photo_1(message: Message, state: FSMContext, bot: Bot):
    """Получено первое фото — сохраняем и просим второе."""
    photo = message.photo[-1]
    try:
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_data = file_bytes.read()
    except Exception as e:
        logger.error("Ошибка скачивания фото 1: %s", e)
        await message.answer(
            "😕 Не удалось загрузить фото. Попробуйте ещё раз.",
            reply_markup=cancel_kb,
        )
        return

    await state.update_data(image_1=image_data)
    await state.set_state(CompareForm.waiting_photo_2)
    await message.answer(
        "✅ Первое фото получено!\n\n"
        "📷 Теперь отправьте фото <b>второго</b> корма 👇",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )


@router.message(CompareForm.waiting_photo_1)
async def compare_not_photo_1(message: Message):
    """Ожидали первое фото, получили не фото."""
    await message.answer(
        "📷 Пожалуйста, отправьте <b>фото первого корма</b>.\n"
        "Или нажмите «Отмена».",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )


@router.message(CompareForm.waiting_photo_2, F.photo)
async def compare_photo_2(message: Message, state: FSMContext, bot: Bot):
    """Получено второе фото — запускаем сравнение."""
    photo = message.photo[-1]
    try:
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_data_2 = file_bytes.read()
    except Exception as e:
        logger.error("Ошибка скачивания фото 2: %s", e)
        await message.answer(
            "😕 Не удалось загрузить фото. Попробуйте ещё раз.",
            reply_markup=cancel_kb,
        )
        return

    data = await state.get_data()
    image_data_1 = data.get("image_1")
    await state.clear()

    if not image_data_1:
        await message.answer(
            "😕 Первое фото потеряно. Начните сравнение заново.",
            reply_markup=photo_menu_kb,
        )
        return

    if not await is_ai_operational():
        await message.answer(
            _no_ai_message(),
            reply_markup=photo_menu_kb,
        )
        return

    allowed, _remaining = await check_ai_limit(message.from_user.id)
    if not allowed:
        await message.answer(_ai_limit_message(), reply_markup=_ai_upgrade_kb())
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    processing_msg = await message.answer(
        "🔍 <b>AI сравнивает два корма...</b>\n\n"
        "⏳ Глубокий анализ — несколько секунд...",
        parse_mode="HTML",
    )

    try:
        result = await compare_two_foods(image_data_1, image_data_2)
    except Exception as e:
        logger.error("Ошибка сравнения кормов: %s", e)
        result = None

    if result:
        if len(result) > 4000:
            result = result[:4000] + "..."
        safe_result = escape(result)
        await processing_msg.edit_text(
            f"⚖️ <b>Результат сравнения кормов:</b>\n\n{safe_result}",
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


@router.message(CompareForm.waiting_photo_2)
async def compare_not_photo_2(message: Message):
    """Ожидали второе фото, получили не фото."""
    await message.answer(
        "📷 Пожалуйста, отправьте <b>фото второго корма</b>.\n"
        "Или нажмите «Отмена».",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
