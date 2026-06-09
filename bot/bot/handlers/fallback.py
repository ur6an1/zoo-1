"""Fallback-обработчики для непредусмотренного ввода."""

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.keyboards import cancel_kb, main_menu_kb

router = Router(name="fallback")


@router.message()
async def unknown_message(message: Message, state: FSMContext):
    """Единый ответ на сообщения, которые не подошли ни одному сценарию."""
    current_state = await state.get_state()
    if current_state:
        await message.answer(
            "⚠️ Сейчас я жду ответ по текущему шагу.\n\n"
            "Отправьте данные в формате из предыдущего сообщения или отмените действие.",
            reply_markup=cancel_kb,
        )
        return

    await message.answer(
        "Не понял сообщение. Выберите раздел в меню ниже или нажмите /help.",
        reply_markup=main_menu_kb,
    )


@router.callback_query()
async def unknown_callback(callback: CallbackQuery, state: FSMContext):
    """Понятный ответ на устаревшие или неактуальные inline-кнопки."""
    current_state = await state.get_state()
    if current_state:
        await callback.answer(
            "Эта кнопка сейчас не подходит к текущему шагу. Продолжите сценарий или нажмите /cancel.",
            show_alert=True,
        )
        return

    await callback.answer(
        "Кнопка устарела. Откройте меню заново.",
        show_alert=True,
    )
