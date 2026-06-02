"""Обработчики: дневник питания (еда, вода, аллергии, графики)."""

import logging
from datetime import date, datetime
from html import escape
from types import SimpleNamespace

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot import api_client
from bot.keyboards.keyboards import (
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
from bot.states.states import AllergyForm, FoodForm, WaterForm
from bot.utils.helpers import callback_int, format_datetime, parse_amount

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
        "📊 <b>Аналитика питания</b>\n\nВыберите, что хотите посмотреть:",
        parse_mode="HTML",
        reply_markup=food_analytics_kb,
    )
    await callback.answer()


# ══════════════════════════════════════════════
#  ПРИЁМЫ ПИЩИ
# ══════════════════════════════════════════════


@router.callback_query(F.data == "food:meal:add")
async def cb_meal_add(callback: CallbackQuery, state: FSMContext):
    pets = await api_client.list_pets(callback.from_user.id)

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
    pet = await api_client.get_pet(pet_id, callback.from_user.id)
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
        "⚖️ Укажите порцию (например: «100 г», «1/2 пакетика»)\nили напишите <b>-</b> чтобы пропустить:",
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

    entry = await api_client.create_food_entry(
        user_id=message.from_user.id,
        pet_id=data["pet_id"],
        food_name=data["food_name"],
        portion=data.get("portion", ""),
        notes=notes,
    )

    await message.answer(
        f"✅ <b>Приём пищи записан!</b>\n\n"
        f"🍽 {escape(data['food_name'])}\n"
        f"⚖️ Порция: {escape(data.get('portion', '')) or '—'}\n"
        f"🕐 {format_datetime(entry.get('meal_time', ''))}",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )


@router.callback_query(F.data == "food:meal:list")
async def cb_meal_list(callback: CallbackQuery):
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    all_entries = []
    pet_map = {}
    for p in pets:
        pet_map[p["id"]] = p["name"]
        entries = await api_client.list_food_entries(p["id"], callback.from_user.id)
        all_entries.extend(entries)

    if not all_entries:
        await callback.message.edit_text("🍽 Записей нет.", reply_markup=back_to_menu_kb)
    else:
        lines = ["🍽 <b>История приёмов пищи</b>\n"]
        for e in all_entries[:20]:
            lines.append(
                f"• <b>{escape(e['food_name'])}</b> ({escape(pet_map.get(e.get('pet_id', 0), '?'))})\n"
                f"  ⚖️ {escape(e.get('portion', '')) or '—'} | 🕐 {format_datetime(e.get('meal_time', ''))}"
            )
        await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu_kb)
    await callback.answer()


# ══════════════════════════════════════════════
#  УЧЁТ ВОДЫ
# ══════════════════════════════════════════════


@router.callback_query(F.data == "food:water:add")
async def cb_water_add(callback: CallbackQuery, state: FSMContext):
    pets = await api_client.list_pets(callback.from_user.id)

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
    pet = await api_client.get_pet(pet_id, callback.from_user.id)
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

    entry = await api_client.create_water_entry(message.from_user.id, data["pet_id"], amount)

    await message.answer(
        f"✅ Записано: <b>{amount} мл</b> воды\n🕐 {format_datetime(entry.get('recorded_at', ''))}",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )


@router.callback_query(F.data == "food:water:list")
async def cb_water_list(callback: CallbackQuery):
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    all_entries = []
    pet_map = {}
    for p in pets:
        pet_map[p["id"]] = p["name"]
        entries = await api_client.list_water_entries(p["id"], callback.from_user.id)
        all_entries.extend(entries)

    if not all_entries:
        await callback.message.edit_text("💧 Записей нет.", reply_markup=back_to_menu_kb)
    else:
        lines = ["💧 <b>История потребления воды</b>\n"]
        for e in all_entries[:20]:
            pet_label = escape(pet_map.get(e.get("pet_id", 0), "?"))
            dt_str = format_datetime(e.get("recorded_at", ""))
            lines.append(f"• {pet_label}: <b>{e['amount_ml']} мл</b> — {dt_str}")
        await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu_kb)
    await callback.answer()


# ══════════════════════════════════════════════
#  АЛЛЕРГИИ
# ══════════════════════════════════════════════


@router.callback_query(F.data == "food:allergy:add")
async def cb_allergy_add(callback: CallbackQuery, state: FSMContext):
    pets = await api_client.list_pets(callback.from_user.id)

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
    pet = await api_client.get_pet(pet_id, callback.from_user.id)
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

    await api_client.create_allergy(
        user_id=message.from_user.id,
        pet_id=data["pet_id"],
        allergen=data["allergen"],
        reaction=data.get("reaction", ""),
        notes=notes,
    )

    await message.answer(
        f"✅ <b>Аллергия записана!</b>\n\n"
        f"⚠️ {escape(data['allergen'])}\n"
        f"🤒 Реакция: {escape(data.get('reaction', '')) or '—'}\n"
        f"📝 {escape(notes) if notes else '—'}",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )


@router.callback_query(F.data == "food:allergy:list")
async def cb_allergy_list(callback: CallbackQuery):
    allergies = await api_client.list_allergies_by_user(callback.from_user.id)

    if not allergies:
        await callback.message.edit_text("⚠️ Аллергий не зарегистрировано.", reply_markup=back_to_menu_kb)
    else:
        lines = ["⚠️ <b>Аллергии и непереносимости</b>\n"]
        for a in allergies:
            lines.append(f"• <b>{escape(a['allergen'])}</b>\n  🤒 {escape(a.get('reaction', '')) or '—'}")
        lines.append("\n🗑 <i>Нажмите, чтобы удалить:</i>")
        await callback.message.edit_text(
            "\n".join(lines), parse_mode="HTML", reply_markup=allergy_list_kb([SimpleNamespace(**a) for a in allergies])
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

    deleted = await api_client.delete_allergy(allergy_id, callback.from_user.id)
    if deleted:
        await callback.answer("🗑 Аллергия удалена", show_alert=True)
    else:
        await callback.answer("Запись не найдена", show_alert=True)
        return

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
    pets = await api_client.list_pets(callback.from_user.id)
    for p in pets:
        await api_client.clear_food_entries(p["id"], callback.from_user.id)

    await callback.message.edit_text(
        "🗑 Записи удалены.",
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
    pets = await api_client.list_pets(callback.from_user.id)
    for p in pets:
        await api_client.clear_water_entries(p["id"], callback.from_user.id)

    await callback.message.edit_text(
        "🗑 Записи удалены.",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer("Очищено ✅")


# ──────────────────── ИСТОРИЯ ЗА СЕГОДНЯ ────────────────────


@router.callback_query(F.data == "food:today")
async def cb_food_today(callback: CallbackQuery):
    """Показать все записи за сегодня."""
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    today = date.today()
    lines = [f"📋 <b>Дневник за {today.strftime('%d.%m.%Y')}</b>\n"]

    has_food = False
    has_water = False

    for p in pets:
        summary = await api_client.get_daily_summary(p["id"], callback.from_user.id)
        food_entries = summary.get("food_entries", [])
        water_entries = summary.get("water_entries", [])

        if food_entries:
            has_food = True
            for fe in food_entries:
                mt = fe.get("meal_time", "")
                time_str = mt.split("T")[1][:5] if "T" in str(mt) else ""
                lines.append(
                    f"  🍽 {escape(p['name'])}: {escape(fe['food_name'])} "
                    f"({escape(fe.get('portion', '') or '—')}) в {time_str}"
                )

        if water_entries:
            has_water = True

    if not has_food:
        lines.append("🍽 Приёмов пищи не записано")

    lines.append("")

    if has_water:
        lines.append("<b>💧 Вода:</b>")
        for p in pets:
            summary = await api_client.get_daily_summary(p["id"], callback.from_user.id)
            total_ml = summary.get("total_ml", 0)
            if total_ml:
                lines.append(f"  • {escape(p['name'])}: {total_ml} мл")
    else:
        lines.append("💧 Записей о воде нет")

    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu_kb)
    await callback.answer()


# ══════════════════════════════════════════════
#  ГРАФИКИ ПИТАНИЯ
# ══════════════════════════════════════════════


@router.callback_query(F.data == "food:chart:week")
async def cb_food_chart_week(callback: CallbackQuery):
    """График питания за неделю."""
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    all_food = []
    all_water = []
    pet_names = {}
    for p in pets:
        pet_names[p["id"]] = p["name"]
        foods = await api_client.list_food_entries(p["id"], callback.from_user.id, days=7)
        for f in foods:
            f["_pet_id"] = p["id"]
        all_food.extend(foods)
        waters = await api_client.list_water_entries(p["id"], callback.from_user.id, days=7)
        for w in waters:
            w["_pet_id"] = p["id"]
        all_water.extend(waters)

    if not all_food and not all_water:
        await callback.answer("Нет данных за последнюю неделю", show_alert=True)
        return

    food_ns = [
        SimpleNamespace(
            pet_id=f.get("_pet_id", f.get("pet_id")),
            food_name=f.get("food_name", ""),
            portion=f.get("portion", ""),
            portion_grams=f.get("portion_grams"),
            meal_time=datetime.fromisoformat(f["meal_time"]),
        )
        for f in all_food
        if f.get("meal_time")
    ]
    water_ns = [
        SimpleNamespace(
            pet_id=w.get("_pet_id", w.get("pet_id")),
            amount_ml=w.get("amount_ml", 0),
            recorded_at=datetime.fromisoformat(w["recorded_at"]),
        )
        for w in all_water
        if w.get("recorded_at")
    ]

    from backend.services.charts import generate_feeding_chart

    chart_bytes = generate_feeding_chart(food_ns, water_ns, pet_names, days=7)

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
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    today = date.today()
    summary_food = []
    summary_water = []
    pet_names = {}
    for p in pets:
        pet_names[p["id"]] = p["name"]
        summary = await api_client.get_daily_summary(p["id"], callback.from_user.id)
        for fe in summary.get("food_entries", []):
            fe["_pet_id"] = p["id"]
            summary_food.append(fe)
        for we in summary.get("water_entries", []):
            we["_pet_id"] = p["id"]
            summary_water.append(we)

    if not summary_food and not summary_water:
        await callback.answer("Нет данных за сегодня", show_alert=True)
        return

    food_ns = [
        SimpleNamespace(
            pet_id=f.get("_pet_id", f.get("pet_id")),
            food_name=f.get("food_name", ""),
            portion=f.get("portion", ""),
            meal_time=datetime.fromisoformat(f["meal_time"]),
        )
        for f in summary_food
        if f.get("meal_time")
    ]
    water_ns = [
        SimpleNamespace(
            pet_id=w.get("_pet_id", w.get("pet_id")),
            amount_ml=w.get("amount_ml", 0),
            recorded_at=datetime.fromisoformat(w["recorded_at"]),
        )
        for w in summary_water
        if w.get("recorded_at")
    ]

    from backend.services.charts import generate_daily_timeline

    chart_bytes = generate_daily_timeline(food_ns, water_ns, pet_names, today)

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
