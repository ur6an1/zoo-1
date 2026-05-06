"""Общие обработчики: /start, меню, отмена."""

import logging
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import api_client
from bot.keyboards.keyboards import (
    ai_hub_kb,
    back_to_menu_kb,
    health_hub_kb,
    main_menu_kb,
    pets_hub_kb,
    quick_start_kb,
    settings_hub_kb,
)

logger = logging.getLogger(__name__)
router = Router(name="common")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    await api_client.track_user_activity(message.from_user.id, source="start")
    await api_client.track_event(message.from_user.id, "start", source="command")
    await message.answer(
        f"🐾 <b>Добро пожаловать в ZooBuddy!</b>\n\n"
        f"Привет, {escape(message.from_user.first_name or 'друг')}! 👋\n\n"
        "Здесь вы ведёте карточку питомца, ставите напоминания и быстро получаете подсказки по уходу.\n\n"
        "<b>Первый полезный результат за 1 минуту:</b>\n"
        "1. Добавьте питомца\n"
        "2. Поставьте первое напоминание или цель по весу\n"
        "3. При необходимости откройте подписку для AI и PRO-функций",
        parse_mode="HTML",
        reply_markup=quick_start_kb,
    )
    await message.answer(
        "Полное меню уже доступно ниже.",
        reply_markup=main_menu_kb,
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help."""
    await message.answer(
        "📖 <b>Помощь</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — Перезапустить бота\n"
        "/help — Показать помощь\n"
        "/cancel — Отменить текущее действие\n\n"
        "<b>Разделы меню:</b>\n"
        "🐾 <b>Питомцы</b> — карточки, напоминания, календарь\n"
        "🩺 <b>Здоровье</b> — медкарта, питание, погода, советы, SOS\n"
        "🤖 <b>AI-сервисы</b> — фото-анализ, консультант, анализы, голос\n"
        "⚙️ <b>Настройки</b> — подписка и персональные параметры",
        parse_mode="HTML",
        reply_markup=main_menu_kb,
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "🤷 Нечего отменять — вы в главном меню.",
            reply_markup=main_menu_kb,
        )
        return

    await state.clear()
    await message.answer(
        "❌ Действие отменено. Вы в главном меню.",
        reply_markup=main_menu_kb,
    )


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена через inline-кнопку."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено.",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer()


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await state.clear()
    await callback.message.answer(
        "🏠 <b>Главное меню</b>\n\nВыберите раздел 👇",
        parse_mode="HTML",
        reply_markup=main_menu_kb,
    )
    await callback.answer()


@router.message(F.text == "◀️ Назад в меню")
async def back_to_menu_text(message: Message, state: FSMContext):
    """Возврат в меню по текстовой кнопке."""
    await state.clear()
    await message.answer(
        "🏠 <b>Главное меню</b>\n\nВыберите раздел 👇",
        parse_mode="HTML",
        reply_markup=main_menu_kb,
    )


@router.message(F.text == "🐾 Питомцы")
async def pets_hub(message: Message):
    await message.answer(
        "🐾 <b>Раздел питомцев</b>\n\nВыберите нужный инструмент:",
        parse_mode="HTML",
        reply_markup=pets_hub_kb,
    )


@router.message(F.text == "🩺 Здоровье")
async def health_hub(message: Message):
    await message.answer(
        "🩺 <b>Здоровье и уход</b>\n\nВыберите раздел:",
        parse_mode="HTML",
        reply_markup=health_hub_kb,
    )


@router.message(F.text == "🤖 AI-сервисы")
async def ai_hub(message: Message):
    await message.answer(
        "🤖 <b>AI-инструменты</b>\n\nВыберите сценарий:",
        parse_mode="HTML",
        reply_markup=ai_hub_kb,
    )


@router.message(F.text == "⚙️ Настройки")
async def settings_hub(message: Message):
    await message.answer(
        "⚙️ <b>Настройки и подписка</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=settings_hub_kb,
    )
