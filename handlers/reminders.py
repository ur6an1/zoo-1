"""Обработчики: напоминания и расписание."""

import logging
from datetime import datetime
from html import escape

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database import async_session
from keyboards.keyboards import add_pet_cta_kb
from models.models import Pet, Reminder
from states.states import ReminderForm
from keyboards.keyboards import (
    reminders_menu_kb,
    reminder_category_kb,
    reminder_repeat_kb,
    reminders_list_kb,
    reminder_detail_kb,
    pets_list_kb,
    cancel_kb,
    back_to_menu_kb,
)
from services.access import get_owned_pet, get_owned_reminder
from services.analytics import track_user_activity
from utils.helpers import callback_int, format_datetime, parse_date, parse_time
from services.scheduler import schedule_reminder, remove_reminder_job

logger = logging.getLogger(__name__)
router = Router(name="reminders")


# ──────────────────── МЕНЮ НАПОМИНАНИЙ ────────────────────


@router.message(F.text == "⏰ Напоминания")
async def reminders_menu(message: Message):
    """Меню напоминаний."""
    await track_user_activity(message.from_user.id, source="reminders")
    await message.answer(
        "⏰ <b>Напоминания</b>\n\nЧто хотите сделать?",
        parse_mode="HTML",
        reply_markup=reminders_menu_kb,
    )


@router.callback_query(F.data == "reminder:menu")
async def cb_reminders_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "⏰ <b>Напоминания</b>\n\nЧто хотите сделать?",
        parse_mode="HTML",
        reply_markup=reminders_menu_kb,
    )
    await callback.answer()


# ──────────────────── ДОБАВЛЕНИЕ НАПОМИНАНИЯ ────────────────────


@router.callback_query(F.data == "reminder:add")
async def cb_reminder_add(callback: CallbackQuery, state: FSMContext):
    """Начало добавления напоминания — выбор питомца."""
    async with async_session() as session:
        result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = result.scalars().all()

    if not pets:
        await callback.message.edit_text(
            "😕 У вас нет питомцев.\nСначала добавьте питомца в разделе 🐾 Мои питомцы.",
            reply_markup=add_pet_cta_kb,
        )
        await callback.answer()
        return

    await state.set_state(ReminderForm.choosing_pet)
    await callback.message.edit_text(
        "⏰ <b>Новое напоминание</b>\n\nВыберите питомца:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_reminder"),
    )
    await callback.answer()


@router.callback_query(ReminderForm.choosing_pet, F.data.startswith("pet:select_reminder:"))
async def cb_reminder_pet(callback: CallbackQuery, state: FSMContext):
    """Выбран питомец для напоминания."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return
    async with async_session() as session:
        pet = await get_owned_pet(session, callback.from_user.id, pet_id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return
    await state.update_data(pet_id=pet_id)
    await state.set_state(ReminderForm.category)
    await callback.message.edit_text(
        "Выберите тип напоминания:",
        reply_markup=reminder_category_kb,
    )
    await callback.answer()


@router.callback_query(F.data == "reminder:cancel")
async def cb_reminder_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Создание напоминания отменено.",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer()


@router.callback_query(ReminderForm.category, F.data.startswith("rem_cat:"))
async def cb_reminder_category(callback: CallbackQuery, state: FSMContext):
    """Выбрана категория."""
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(ReminderForm.title)

    category_names = {
        "feeding": "🍽 Кормление",
        "vaccine": "💉 Прививка",
        "vet": "🏥 Ветеринар",
        "grooming": "✂️ Груминг",
        "custom": "📌 Своё",
    }
    name = category_names.get(category, category)

    await callback.message.edit_text(
        f"Тип: <b>{name}</b> ✅\n\n"
        "Введите название напоминания\n"
        "(например: «Утреннее кормление» или «Прививка от бешенства»):",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(ReminderForm.title)
async def reminder_title(message: Message, state: FSMContext):
    """Получаем название."""
    title = message.text.strip()
    if not title or len(title) > 200:
        await message.answer("⚠️ Название должно быть от 1 до 200 символов:")
        return
    await state.update_data(title=title)
    await state.set_state(ReminderForm.description)
    await message.answer(
        f"Название: <b>{title}</b> ✅\n\n"
        "Добавьте описание или комментарий (необязательно).\n"
        "Отправьте текст или напишите <b>-</b> чтобы пропустить:",
        parse_mode="HTML",
    )


@router.message(ReminderForm.description)
async def reminder_description(message: Message, state: FSMContext):
    """Получаем описание."""
    desc = message.text.strip()
    if desc == "-":
        desc = ""
    await state.update_data(description=desc)
    await state.set_state(ReminderForm.date)
    await message.answer(
        "📅 Введите дату напоминания в формате <b>ДД.ММ.ГГГГ</b>\n"
        "(например: 15.03.2026):",
        parse_mode="HTML",
    )


@router.message(ReminderForm.date)
async def reminder_date(message: Message, state: FSMContext):
    """Получаем дату."""
    d = parse_date(message.text)
    if d is None:
        await message.answer(
            "⚠️ Неверный формат. Введите дату в формате <b>ДД.ММ.ГГГГ</b>:",
            parse_mode="HTML",
        )
        return
    await state.update_data(date=d.isoformat())
    await state.set_state(ReminderForm.time)
    await message.answer(
        f"Дата: <b>{d.strftime('%d.%m.%Y')}</b> ✅\n\n"
        "⏰ Введите время в формате <b>ЧЧ:ММ</b>\n"
        "(например: 09:00):",
        parse_mode="HTML",
    )


@router.message(ReminderForm.time)
async def reminder_time(message: Message, state: FSMContext):
    """Получаем время."""
    t = parse_time(message.text)
    if t is None:
        await message.answer(
            "⚠️ Неверный формат. Введите время в формате <b>ЧЧ:ММ</b>:",
            parse_mode="HTML",
        )
        return
    h, m = t
    await state.update_data(hour=h, minute=m)
    await state.set_state(ReminderForm.repeat)
    await message.answer(
        f"Время: <b>{h:02d}:{m:02d}</b> ✅\n\n"
        "🔄 Выберите периодичность:",
        parse_mode="HTML",
        reply_markup=reminder_repeat_kb,
    )


@router.callback_query(ReminderForm.repeat, F.data.startswith("repeat:"))
async def reminder_repeat(callback: CallbackQuery, state: FSMContext):
    """Получаем периодичность и сохраняем."""
    repeat = callback.data.split(":")[1]
    data = await state.get_data()
    await state.clear()

    from datetime import date as date_type

    d = date_type.fromisoformat(data["date"])
    remind_at = datetime(d.year, d.month, d.day, data["hour"], data["minute"])

    reminder = Reminder(
        pet_id=data["pet_id"],
        user_id=callback.from_user.id,
        category=data["category"],
        title=data["title"],
        description=data.get("description", ""),
        remind_at=remind_at,
        repeat=repeat,
        is_active=True,
    )

    async with async_session() as session:
        session.add(reminder)
        await session.commit()
        await session.refresh(reminder)
        # Подгружаем связь с питомцем
        pet = await session.get(Pet, reminder.pet_id)

    # Планируем в APScheduler
    reminder.pet = pet
    schedule_reminder(reminder)

    repeat_texts = {
        "once": "разово",
        "daily": "ежедневно",
        "weekly": "еженедельно",
        "monthly": "ежемесячно",
        "yearly": "ежегодно",
    }

    pet_name = pet.name if pet else "—"

    await callback.message.edit_text(
        f"✅ <b>Напоминание создано!</b>\n\n"
        f"🐾 Питомец: {escape(pet_name)}\n"
        f"{reminder.category_emoji} {escape(reminder.title)}\n"
        f"📅 Дата: {d.strftime('%d.%m.%Y')}\n"
        f"⏰ Время: {data['hour']:02d}:{data['minute']:02d}\n"
        f"🔄 Повтор: {repeat_texts.get(repeat, repeat)}",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer("Напоминание создано! ✅")


# ──────────────────── СПИСОК НАПОМИНАНИЙ ────────────────────


@router.callback_query(F.data == "reminder:list")
async def cb_reminder_list(callback: CallbackQuery):
    """Список напоминаний пользователя (активные + приостановленные)."""
    async with async_session() as session:
        result = await session.execute(
            select(Reminder)
            .where(Reminder.user_id == callback.from_user.id)
            .order_by(Reminder.is_active.desc(), Reminder.remind_at)
        )
        reminders = result.scalars().all()

    if not reminders:
        await callback.message.edit_text(
            "📋 У вас нет напоминаний.",
            reply_markup=reminders_menu_kb,
        )
    else:
        active = sum(1 for r in reminders if r.is_active)
        paused = len(reminders) - active
        status_text = f"✅ Активных: {active}"
        if paused:
            status_text += f" | ⏸ На паузе: {paused}"
        await callback.message.edit_text(
            f"📋 <b>Ваши напоминания</b> ({len(reminders)})\n{status_text}",
            parse_mode="HTML",
            reply_markup=reminders_list_kb(reminders),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("reminder:view:"))
async def cb_reminder_view(callback: CallbackQuery):
    """Подробности напоминания."""
    rem_id = callback_int(callback.data, 2)
    if rem_id is None:
        await callback.answer("Некорректное напоминание", show_alert=True)
        return
    async with async_session() as session:
        reminder = await get_owned_reminder(session, callback.from_user.id, rem_id)
        if not reminder:
            await callback.answer("Напоминание не найдено", show_alert=True)
            return
        pet = await session.get(Pet, reminder.pet_id)

    pet_name = pet.name if pet else "—"
    text = (
        f"{reminder.category_emoji} <b>{escape(reminder.title)}</b>\n\n"
        f"🐾 Питомец: {escape(pet_name)}\n"
        f"📅 Дата/время: {format_datetime(reminder.remind_at)}\n"
        f"🔄 Повтор: {reminder.repeat_text}\n"
    )
    if reminder.description:
        text += f"📝 Описание: {escape(reminder.description)}\n"
    text += f"\n{'✅ Активно' if reminder.is_active else '⏸ Приостановлено'}"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=reminder_detail_kb(rem_id, is_active=reminder.is_active),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reminder:pause:"))
async def cb_reminder_pause(callback: CallbackQuery):
    """Приостановить напоминание."""
    rem_id = callback_int(callback.data, 2)
    if rem_id is None:
        await callback.answer("Некорректное напоминание", show_alert=True)
        return

    async with async_session() as session:
        reminder = await get_owned_reminder(session, callback.from_user.id, rem_id)
        if not reminder:
            await callback.answer("Напоминание не найдено", show_alert=True)
            return
        reminder.is_active = False
        await session.commit()
        remove_reminder_job(reminder.id)
        pet = await get_owned_pet(session, callback.from_user.id, reminder.pet_id)

    await callback.message.edit_text(
        f"⏸ Напоминание <b>{escape(reminder.title)}</b> приостановлено.\n"
        "Вы можете возобновить его в любое время.",
        parse_mode="HTML",
        reply_markup=reminder_detail_kb(rem_id, is_active=False),
    )
    await callback.answer("Приостановлено ⏸")


@router.callback_query(F.data.startswith("reminder:resume:"))
async def cb_reminder_resume(callback: CallbackQuery):
    """Возобновить напоминание."""
    rem_id = callback_int(callback.data, 2)
    if rem_id is None:
        await callback.answer("Некорректное напоминание", show_alert=True)
        return

    async with async_session() as session:
        reminder = await get_owned_reminder(session, callback.from_user.id, rem_id)
        if not reminder:
            await callback.answer("Напоминание не найдено", show_alert=True)
            return
        reminder.is_active = True
        await session.commit()
        pet = await get_owned_pet(session, callback.from_user.id, reminder.pet_id)
        reminder.pet = pet
        schedule_reminder(reminder)

    await callback.message.edit_text(
        f"▶️ Напоминание <b>{escape(reminder.title)}</b> возобновлено!",
        parse_mode="HTML",
        reply_markup=reminder_detail_kb(rem_id, is_active=True),
    )
    await callback.answer("Возобновлено ▶️")


@router.callback_query(F.data.startswith("reminder:delete:"))
async def cb_reminder_delete(callback: CallbackQuery):
    """Удаление напоминания."""
    rem_id = callback_int(callback.data, 2)
    if rem_id is None:
        await callback.answer("Некорректное напоминание", show_alert=True)
        return

    async with async_session() as session:
        reminder = await get_owned_reminder(session, callback.from_user.id, rem_id)
        if not reminder:
            await callback.answer("Напоминание не найдено", show_alert=True)
            return
        remove_reminder_job(reminder.id)
        await session.delete(reminder)
        await session.commit()

    await callback.message.edit_text(
        "🗑 Напоминание удалено.",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer("Удалено ✅")
