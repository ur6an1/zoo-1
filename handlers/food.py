"""Обработчики: дневник питания (еда, вода, аллергии, графики)."""

import logging
from datetime import date, datetime, timedelta
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy import and_, select

from database import async_session
from keyboards.keyboards import (
    add_pet_cta_kb,
    allergy_action_kb,
    allergy_list_kb,
    back_to_menu_kb,
    cancel_kb,
    food_action_kb,
    food_analytics_kb,
    food_clear_confirm_kb,
    food_menu_kb,
    pets_list_kb,
    water_action_kb,
)
from models.models import Allergy, FoodEntry, Pet, WaterEntry
from services.access import get_owned_allergy, get_owned_pet
from services.charts import generate_daily_timeline, generate_feeding_chart
from states.states import AllergyForm, FoodForm, WaterForm
from utils.helpers import callback_int, format_datetime, parse_amount

logger = logging.getLogger(__name__)
router = Router(name="food")


# ──────────────────── МЕНЮ ДНЕВНИКА ────────────────────


@router.message(F.text == "🍽 Дневник питания")
async def food_menu(message: Message):
    await message.answer(
        "🍽 <b>Дневник питания</b>\n\nВыберите раздел:",
        parse_mode="HTML",
        reply_markup=food_menu_kb,
    )


@router.callback_query(F.data == "food:menu")
async def cb_food_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🍽 <b>Дневник питания</b>\n\nВыберите раздел:",
        parse_mode="HTML",
        reply_markup=food_menu_kb,
    )
    await callback.answer()


# ──────── Подменю ────────


@router.callback_query(F.data == "food:meal")
async def cb_food_meal(callback: CallbackQuery):
    await callback.message.edit_text(
        "🍽 <b>Приёмы пищи</b>",
        parse_mode="HTML",
        reply_markup=food_action_kb,
    )
    await callback.answer()


@router.callback_query(F.data == "food:water")
async def cb_food_water(callback: CallbackQuery):
    await callback.message.edit_text(
        "💧 <b>Учёт воды</b>",
        parse_mode="HTML",
        reply_markup=water_action_kb,
    )
    await callback.answer()


@router.callback_query(F.data == "food:allergies")
async def cb_food_allergies(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚠️ <b>Аллергии и непереносимости</b>",
        parse_mode="HTML",
        reply_markup=allergy_action_kb,
    )
    await callback.answer()


@router.callback_query(F.data == "food:analytics")
async def cb_food_analytics(callback: CallbackQuery):
    await callback.message.edit_text(
        "📊 <b>Аналитика питания</b>\n\n"
        "Выберите, что хотите посмотреть:",
        parse_mode="HTML",
        reply_markup=food_analytics_kb,
    )
    await callback.answer()


# ══════════════════════════════════════════════
#  ПРИЁМЫ ПИЩИ
# ══════════════════════════════════════════════


@router.callback_query(F.data == "food:meal:add")
async def cb_meal_add(callback: CallbackQuery, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = result.scalars().all()

    if not pets:
        await callback.message.edit_text("😕 Сначала добавьте питомца.", reply_markup=add_pet_cta_kb)
        await callback.answer()
        return

    await state.set_state(FoodForm.choosing_pet)
    await callback.message.edit_text(
        "🍽 <b>Добавить приём пищи</b>\n\nВыберите питомца:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_food"),
    )
    await callback.answer()


@router.callback_query(FoodForm.choosing_pet, F.data.startswith("pet:select_food:"))
async def cb_meal_pet(callback: CallbackQuery, state: FSMContext):
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
    await state.set_state(FoodForm.food_name)
    await callback.message.edit_text(
        "🍽 Что ел питомец?\n(Название корма или еды):",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(FoodForm.food_name)
async def meal_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name or len(name) > 200:
        await message.answer("⚠️ Название от 1 до 200 символов:")
        return
    await state.update_data(food_name=name)
    await state.set_state(FoodForm.portion)
    await message.answer(
        "⚖️ Укажите порцию (например: «100 г», «1/2 пакетика»)\n"
        "или напишите <b>-</b> чтобы пропустить:",
        parse_mode="HTML",
    )


@router.message(FoodForm.portion)
async def meal_portion(message: Message, state: FSMContext):
    portion = message.text.strip()
    if portion == "-":
        portion = ""
    await state.update_data(portion=portion)
    await state.set_state(FoodForm.notes)
    await message.answer(
        "📝 Заметки (или <b>-</b> чтобы пропустить):",
        parse_mode="HTML",
    )


@router.message(FoodForm.notes)
async def meal_notes(message: Message, state: FSMContext):
    notes = message.text.strip()
    if notes == "-":
        notes = ""
    data = await state.get_data()
    await state.clear()

    entry = FoodEntry(
        pet_id=data["pet_id"],
        food_name=data["food_name"],
        portion=data.get("portion", ""),
        notes=notes,
    )

    async with async_session() as session:
        session.add(entry)
        await session.commit()

    await message.answer(
        f"✅ <b>Приём пищи записан!</b>\n\n"
        f"🍽 {escape(entry.food_name)}\n"
        f"⚖️ Порция: {escape(entry.portion) if entry.portion else '—'}\n"
        f"🕐 {format_datetime(entry.meal_time)}",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )


@router.callback_query(F.data == "food:meal:list")
async def cb_meal_list(callback: CallbackQuery):
    async with async_session() as session:
        pets_result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = pets_result.scalars().all()
        pet_ids = [p.id for p in pets]

        if not pet_ids:
            await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
            await callback.answer()
            return

        result = await session.execute(
            select(FoodEntry)
            .where(FoodEntry.pet_id.in_(pet_ids))
            .order_by(FoodEntry.meal_time.desc())
            .limit(20)
        )
        entries = result.scalars().all()

    if not entries:
        await callback.message.edit_text("🍽 Записей нет.", reply_markup=back_to_menu_kb)
    else:
        pet_map = {p.id: p.name for p in pets}
        lines = ["🍽 <b>История приёмов пищи</b>\n"]
        for e in entries:
            lines.append(
                f"• <b>{escape(e.food_name)}</b> ({escape(pet_map.get(e.pet_id, '?'))})\n"
                f"  ⚖️ {escape(e.portion) if e.portion else '—'} | 🕐 {format_datetime(e.meal_time)}"
            )
        await callback.message.edit_text(
            "\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu_kb
        )
    await callback.answer()


# ══════════════════════════════════════════════
#  УЧЁТ ВОДЫ
# ══════════════════════════════════════════════


@router.callback_query(F.data == "food:water:add")
async def cb_water_add(callback: CallbackQuery, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = result.scalars().all()

    if not pets:
        await callback.message.edit_text("😕 Сначала добавьте питомца.", reply_markup=add_pet_cta_kb)
        await callback.answer()
        return

    await state.set_state(WaterForm.choosing_pet)
    await callback.message.edit_text(
        "💧 <b>Записать воду</b>\n\nВыберите питомца:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_water"),
    )
    await callback.answer()


@router.callback_query(WaterForm.choosing_pet, F.data.startswith("pet:select_water:"))
async def cb_water_pet(callback: CallbackQuery, state: FSMContext):
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
    await state.set_state(WaterForm.amount)
    await callback.message.edit_text(
        "💧 Сколько воды выпил питомец (в мл)?\nНапример: <b>150</b>",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(WaterForm.amount)
async def water_amount(message: Message, state: FSMContext):
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer("⚠️ Введите число (мл), например: 150")
        return
    data = await state.get_data()
    await state.clear()

    entry = WaterEntry(pet_id=data["pet_id"], amount_ml=amount)

    async with async_session() as session:
        session.add(entry)
        await session.commit()

    await message.answer(
        f"✅ Записано: <b>{amount} мл</b> воды\n"
        f"🕐 {format_datetime(entry.recorded_at)}",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )


@router.callback_query(F.data == "food:water:list")
async def cb_water_list(callback: CallbackQuery):
    async with async_session() as session:
        pets_result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = pets_result.scalars().all()
        pet_ids = [p.id for p in pets]

        if not pet_ids:
            await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
            await callback.answer()
            return

        result = await session.execute(
            select(WaterEntry)
            .where(WaterEntry.pet_id.in_(pet_ids))
            .order_by(WaterEntry.recorded_at.desc())
            .limit(20)
        )
        entries = result.scalars().all()

    if not entries:
        await callback.message.edit_text("💧 Записей нет.", reply_markup=back_to_menu_kb)
    else:
        pet_map = {p.id: p.name for p in pets}
        lines = ["💧 <b>История потребления воды</b>\n"]
        for e in entries:
            lines.append(
                f"• {escape(pet_map.get(e.pet_id, '?'))}: <b>{e.amount_ml} мл</b> — {format_datetime(e.recorded_at)}"
            )
        await callback.message.edit_text(
            "\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu_kb
        )
    await callback.answer()


# ══════════════════════════════════════════════
#  АЛЛЕРГИИ
# ══════════════════════════════════════════════


@router.callback_query(F.data == "food:allergy:add")
async def cb_allergy_add(callback: CallbackQuery, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = result.scalars().all()

    if not pets:
        await callback.message.edit_text("😕 Сначала добавьте питомца.", reply_markup=add_pet_cta_kb)
        await callback.answer()
        return

    await state.set_state(AllergyForm.choosing_pet)
    await callback.message.edit_text(
        "⚠️ <b>Добавить аллергию</b>\n\nВыберите питомца:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_allergy"),
    )
    await callback.answer()


@router.callback_query(AllergyForm.choosing_pet, F.data.startswith("pet:select_allergy:"))
async def cb_allergy_pet(callback: CallbackQuery, state: FSMContext):
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
    await state.set_state(AllergyForm.allergen)
    await callback.message.edit_text(
        "⚠️ На что аллергия/непереносимость?\n(Название продукта или вещества):",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(AllergyForm.allergen)
async def allergy_allergen(message: Message, state: FSMContext):
    allergen = message.text.strip()
    if not allergen or len(allergen) > 200:
        await message.answer("⚠️ Введите название (от 1 до 200 символов):")
        return
    await state.update_data(allergen=allergen)
    await state.set_state(AllergyForm.reaction)
    await message.answer(
        "Опишите реакцию (или <b>-</b> чтобы пропустить):",
        parse_mode="HTML",
    )


@router.message(AllergyForm.reaction)
async def allergy_reaction(message: Message, state: FSMContext):
    reaction = message.text.strip()
    if reaction == "-":
        reaction = ""
    await state.update_data(reaction=reaction)
    await state.set_state(AllergyForm.notes)
    await message.answer("📝 Заметки (или <b>-</b>):", parse_mode="HTML")


@router.message(AllergyForm.notes)
async def allergy_notes(message: Message, state: FSMContext):
    notes = message.text.strip()
    if notes == "-":
        notes = ""
    data = await state.get_data()
    await state.clear()

    allergy = Allergy(
        pet_id=data["pet_id"],
        allergen=data["allergen"],
        reaction=data.get("reaction", ""),
        notes=notes,
    )

    async with async_session() as session:
        session.add(allergy)
        await session.commit()

    await message.answer(
        f"✅ <b>Аллергия записана!</b>\n\n"
        f"⚠️ {escape(allergy.allergen)}\n"
        f"🤒 Реакция: {escape(allergy.reaction) if allergy.reaction else '—'}\n"
        f"📝 {escape(notes) if notes else '—'}",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )


@router.callback_query(F.data == "food:allergy:list")
async def cb_allergy_list(callback: CallbackQuery):
    async with async_session() as session:
        pets_result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = pets_result.scalars().all()
        pet_ids = [p.id for p in pets]

        if not pet_ids:
            await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
            await callback.answer()
            return

        result = await session.execute(
            select(Allergy).where(Allergy.pet_id.in_(pet_ids))
        )
        allergies = result.scalars().all()

    if not allergies:
        await callback.message.edit_text(
            "⚠️ Аллергий не зарегистрировано.", reply_markup=back_to_menu_kb
        )
    else:
        pet_map = {p.id: p.name for p in pets}
        lines = ["⚠️ <b>Аллергии и непереносимости</b>\n"]
        for a in allergies:
            lines.append(
                f"• <b>{escape(a.allergen)}</b> ({escape(pet_map.get(a.pet_id, '?'))})\n"
                f"  🤒 {escape(a.reaction) if a.reaction else '—'}"
            )
        lines.append("\n🗑 <i>Нажмите, чтобы удалить:</i>")
        await callback.message.edit_text(
            "\n".join(lines), parse_mode="HTML", reply_markup=allergy_list_kb(allergies)
        )
    await callback.answer()


# ══════════════════════════════════════════════
#  УДАЛЕНИЕ ЗАПИСЕЙ
# ══════════════════════════════════════════════


@router.callback_query(F.data.startswith("food:allergy:del:"))
async def cb_allergy_delete(callback: CallbackQuery):
    """Удаление аллергии."""
    allergy_id = callback_int(callback.data, 3)
    if allergy_id is None:
        await callback.answer("Некорректная аллергия", show_alert=True)
        return
    async with async_session() as session:
        allergy = await get_owned_allergy(session, callback.from_user.id, allergy_id)
        if allergy:
            name = allergy.allergen
            await session.delete(allergy)
            await session.commit()
            await callback.answer(f"🗑 Аллергия «{name}» удалена", show_alert=True)
        else:
            await callback.answer("Запись не найдена", show_alert=True)
            return

    # Обновляем список
    await cb_allergy_list(callback)


@router.callback_query(F.data == "food:meal:clear_confirm")
async def cb_meal_clear_confirm(callback: CallbackQuery):
    """Подтверждение очистки истории приёмов пищи."""
    await callback.message.edit_text(
        "⚠️ <b>Вы уверены?</b>\n\nВся история приёмов пищи будет удалена.",
        parse_mode="HTML",
        reply_markup=food_clear_confirm_kb("meal"),
    )
    await callback.answer()


@router.callback_query(F.data == "food:meal:clear")
async def cb_meal_clear(callback: CallbackQuery):
    """Очистка всех записей еды."""
    async with async_session() as session:
        pets_result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = pets_result.scalars().all()
        pet_ids = [p.id for p in pets]

        if pet_ids:
            result = await session.execute(
                select(FoodEntry).where(FoodEntry.pet_id.in_(pet_ids))
            )
            entries = result.scalars().all()
            for e in entries:
                await session.delete(e)
            await session.commit()
            count = len(entries)
        else:
            count = 0

    await callback.message.edit_text(
        f"🗑 Удалено записей: <b>{count}</b>",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer("Очищено ✅")


@router.callback_query(F.data == "food:water:clear_confirm")
async def cb_water_clear_confirm(callback: CallbackQuery):
    """Подтверждение очистки истории воды."""
    await callback.message.edit_text(
        "⚠️ <b>Вы уверены?</b>\n\nВся история потребления воды будет удалена.",
        parse_mode="HTML",
        reply_markup=food_clear_confirm_kb("water"),
    )
    await callback.answer()


@router.callback_query(F.data == "food:water:clear")
async def cb_water_clear(callback: CallbackQuery):
    """Очистка всех записей воды."""
    async with async_session() as session:
        pets_result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = pets_result.scalars().all()
        pet_ids = [p.id for p in pets]

        if pet_ids:
            result = await session.execute(
                select(WaterEntry).where(WaterEntry.pet_id.in_(pet_ids))
            )
            entries = result.scalars().all()
            for e in entries:
                await session.delete(e)
            await session.commit()
            count = len(entries)
        else:
            count = 0

    await callback.message.edit_text(
        f"🗑 Удалено записей: <b>{count}</b>",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer("Очищено ✅")


# ──────────────────── ИСТОРИЯ ЗА СЕГОДНЯ ────────────────────


@router.callback_query(F.data == "food:today")
async def cb_food_today(callback: CallbackQuery):
    """Показать все записи за сегодня."""
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    today_end = datetime(today.year, today.month, today.day, 23, 59, 59)

    async with async_session() as session:
        pets_result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = pets_result.scalars().all()
        pet_ids = [p.id for p in pets]

        if not pet_ids:
            await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
            await callback.answer()
            return

        # Еда за сегодня
        food_result = await session.execute(
            select(FoodEntry)
            .where(
                and_(
                    FoodEntry.pet_id.in_(pet_ids),
                    FoodEntry.meal_time >= today_start,
                    FoodEntry.meal_time <= today_end,
                )
            )
            .order_by(FoodEntry.meal_time)
        )
        foods = food_result.scalars().all()

        # Вода за сегодня
        water_result = await session.execute(
            select(WaterEntry)
            .where(
                and_(
                    WaterEntry.pet_id.in_(pet_ids),
                    WaterEntry.recorded_at >= today_start,
                    WaterEntry.recorded_at <= today_end,
                )
            )
            .order_by(WaterEntry.recorded_at)
        )
        waters = water_result.scalars().all()

    pet_map = {p.id: p.name for p in pets}
    lines = [f"📋 <b>Дневник за {today.strftime('%d.%m.%Y')}</b>\n"]

    if foods:
        lines.append("<b>🍽 Приёмы пищи:</b>")
        for f_entry in foods:
            lines.append(
                f"  • {escape(pet_map.get(f_entry.pet_id, '?'))}: {escape(f_entry.food_name)} "
                f"({escape(f_entry.portion) if f_entry.portion else '—'}) в {f_entry.meal_time.strftime('%H:%M')}"
            )
    else:
        lines.append("🍽 Приёмов пищи не записано")

    lines.append("")

    if waters:
        total_water: dict[int, int] = {}
        for w in waters:
            total_water[w.pet_id] = total_water.get(w.pet_id, 0) + w.amount_ml
        lines.append("<b>💧 Вода:</b>")
        for pid, total in total_water.items():
            lines.append(f"  • {escape(pet_map.get(pid, '?'))}: {total} мл")
    else:
        lines.append("💧 Записей о воде нет")

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu_kb
    )
    await callback.answer()


# ══════════════════════════════════════════════
#  ГРАФИКИ ПИТАНИЯ
# ══════════════════════════════════════════════


@router.callback_query(F.data == "food:chart:week")
async def cb_food_chart_week(callback: CallbackQuery):
    """График питания за неделю."""
    async with async_session() as session:
        pets_result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = pets_result.scalars().all()
        pet_ids = [p.id for p in pets]

        if not pet_ids:
            await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
            await callback.answer()
            return

        week_ago = datetime.now() - timedelta(days=7)

        food_result = await session.execute(
            select(FoodEntry)
            .where(FoodEntry.pet_id.in_(pet_ids), FoodEntry.meal_time >= week_ago)
            .order_by(FoodEntry.meal_time)
        )
        foods = food_result.scalars().all()

        water_result = await session.execute(
            select(WaterEntry)
            .where(WaterEntry.pet_id.in_(pet_ids), WaterEntry.recorded_at >= week_ago)
            .order_by(WaterEntry.recorded_at)
        )
        waters = water_result.scalars().all()

    if not foods and not waters:
        await callback.answer("Нет данных за последнюю неделю", show_alert=True)
        return

    pet_names = {p.id: p.name for p in pets}
    chart_bytes = generate_feeding_chart(foods, waters, pet_names, days=7)

    if chart_bytes:
        photo = BufferedInputFile(chart_bytes, filename="feeding_chart.png")
        await callback.message.answer_photo(
            photo=photo,
            caption="📊 <b>График питания за 7 дней</b>",
            parse_mode="HTML",
        )
        await callback.answer()
    else:
        await callback.answer("Недостаточно данных для графика", show_alert=True)


@router.callback_query(F.data == "food:chart:day")
async def cb_food_chart_day(callback: CallbackQuery):
    """Расписание питания за сегодня (таймлайн)."""
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    today_end = datetime(today.year, today.month, today.day, 23, 59, 59)

    async with async_session() as session:
        pets_result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = pets_result.scalars().all()
        pet_ids = [p.id for p in pets]

        if not pet_ids:
            await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
            await callback.answer()
            return

        food_result = await session.execute(
            select(FoodEntry)
            .where(
                and_(
                    FoodEntry.pet_id.in_(pet_ids),
                    FoodEntry.meal_time >= today_start,
                    FoodEntry.meal_time <= today_end,
                )
            )
            .order_by(FoodEntry.meal_time)
        )
        foods = food_result.scalars().all()

        water_result = await session.execute(
            select(WaterEntry)
            .where(
                and_(
                    WaterEntry.pet_id.in_(pet_ids),
                    WaterEntry.recorded_at >= today_start,
                    WaterEntry.recorded_at <= today_end,
                )
            )
            .order_by(WaterEntry.recorded_at)
        )
        waters = water_result.scalars().all()

    if not foods and not waters:
        await callback.answer("Нет данных за сегодня", show_alert=True)
        return

    pet_names = {p.id: p.name for p in pets}
    chart_bytes = generate_daily_timeline(foods, waters, pet_names, today)

    if chart_bytes:
        photo = BufferedInputFile(chart_bytes, filename="daily_timeline.png")
        await callback.message.answer_photo(
            photo=photo,
            caption=f"📈 <b>Расписание питания — {today.strftime('%d.%m.%Y')}</b>",
            parse_mode="HTML",
        )
        await callback.answer()
    else:
        await callback.answer("Недостаточно данных для графика", show_alert=True)
