"""Обработчики: медицинская карта (прививки, визиты, вес, документы)."""

import io
import logging
from datetime import date as date_type
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot import api_client
from bot.keyboards.keyboards import (
    add_pet_cta_kb,
    back_to_menu_kb,
    cancel_kb,
    doc_type_kb,
    med_section_kb,
    medical_menu_kb,
    pets_list_kb,
    skip_kb,
)
from bot.states.states import DocumentForm, VaccinationForm, VetVisitForm, WeightForm
from bot.utils.helpers import callback_int, format_date, parse_date, parse_weight

logger = logging.getLogger(__name__)
router = Router(name="medical")


# ──────────────────── МЕНЮ МЕДКАРТЫ ────────────────────


@router.message(F.text == "🏥 Медкарта")
async def medical_menu(message: Message):
    await message.answer(
        "🏥 <b>Медицинская карта</b>\n\nВыберите раздел:",
        parse_mode="HTML",
        reply_markup=medical_menu_kb,
    )


@router.callback_query(F.data == "med:menu")
async def cb_med_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏥 <b>Медицинская карта</b>\n\nВыберите раздел:",
        parse_mode="HTML",
        reply_markup=medical_menu_kb,
    )
    await callback.answer()


# ────── Подменю секций ──────


@router.callback_query(F.data == "med:vaccines")
async def cb_vaccines(callback: CallbackQuery):
    await callback.message.edit_text(
        "💉 <b>Прививки</b>",
        parse_mode="HTML",
        reply_markup=med_section_kb("vaccines"),
    )
    await callback.answer()


@router.callback_query(F.data == "med:vetvisits")
async def cb_vetvisits(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏥 <b>Визиты к ветеринару</b>",
        parse_mode="HTML",
        reply_markup=med_section_kb("vetvisits"),
    )
    await callback.answer()


@router.callback_query(F.data == "med:weight")
async def cb_weight(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚖️ <b>Учёт веса</b>",
        parse_mode="HTML",
        reply_markup=med_section_kb("weight"),
    )
    await callback.answer()


@router.callback_query(F.data == "med:documents")
async def cb_documents(callback: CallbackQuery):
    await callback.message.edit_text(
        "📄 <b>Документы</b>",
        parse_mode="HTML",
        reply_markup=med_section_kb("documents"),
    )
    await callback.answer()


# ══════════════════════════════════════════════
#  ПРИВИВКИ
# ══════════════════════════════════════════════


@router.callback_query(F.data == "med:vaccines:add")
async def cb_vaccine_add(callback: CallbackQuery, state: FSMContext):
    """Начало добавления прививки — выбор питомца."""
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Сначала добавьте питомца.", reply_markup=add_pet_cta_kb)
        await callback.answer()
        return

    await state.set_state(VaccinationForm.choosing_pet)
    await callback.message.edit_text(
        "💉 <b>Добавить прививку</b>\n\nВыберите питомца:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_vaccine"),
    )
    await callback.answer()


@router.callback_query(VaccinationForm.choosing_pet, F.data.startswith("pet:select_vaccine:"))
async def cb_vaccine_pet(callback: CallbackQuery, state: FSMContext):
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return
    pet = await api_client.get_pet(pet_id, callback.from_user.id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return
    await state.update_data(pet_id=pet_id)
    await state.set_state(VaccinationForm.name)
    await callback.message.edit_text(
        "Введите название прививки\n(например: «Нобивак DHPPi» или «От бешенства»):",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(VaccinationForm.name)
async def vaccine_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name or len(name) > 200:
        await message.answer("⚠️ Название от 1 до 200 символов:")
        return
    await state.update_data(vac_name=name)
    await state.set_state(VaccinationForm.date_done)
    await message.answer(
        "📅 Когда была сделана прививка?\nВведите дату (ДД.ММ.ГГГГ):",
    )


@router.message(VaccinationForm.date_done)
async def vaccine_date_done(message: Message, state: FSMContext):
    d = parse_date(message.text)
    if d is None:
        await message.answer("⚠️ Неверный формат. ДД.ММ.ГГГГ:")
        return
    await state.update_data(date_done=d.isoformat())
    await state.set_state(VaccinationForm.next_date)
    await message.answer(
        f"Дата: <b>{format_date(d)}</b> ✅\n\n"
        "📅 Когда следующая прививка? (ДД.ММ.ГГГГ)\n"
        "Или нажмите «Пропустить»:",
        parse_mode="HTML",
        reply_markup=skip_kb,
    )


@router.callback_query(VaccinationForm.next_date, F.data == "skip")
async def vaccine_next_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(next_date=None)
    await state.set_state(VaccinationForm.notes)
    await callback.message.edit_text(
        "Добавьте заметки или напишите <b>-</b> чтобы пропустить:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(VaccinationForm.next_date)
async def vaccine_next_date(message: Message, state: FSMContext):
    d = parse_date(message.text)
    if d is None:
        await message.answer("⚠️ Неверный формат. ДД.ММ.ГГГГ:")
        return
    await state.update_data(next_date=d.isoformat())
    await state.set_state(VaccinationForm.notes)
    await message.answer(
        "Добавьте заметки или напишите <b>-</b> чтобы пропустить:",
        parse_mode="HTML",
    )


@router.message(VaccinationForm.notes)
async def vaccine_notes(message: Message, state: FSMContext):
    notes = message.text.strip()
    if notes == "-":
        notes = ""
    data = await state.get_data()
    await state.clear()

    next_d = date_type.fromisoformat(data["next_date"]) if data.get("next_date") else None
    done_d = date_type.fromisoformat(data["date_done"])

    await api_client.create_vaccination(
        user_id=message.from_user.id,
        pet_id=data["pet_id"],
        name=data["vac_name"],
        date_done=done_d,
        next_date=next_d,
        notes=notes,
    )

    text = (
        "✅ <b>Прививка добавлена!</b>\n\n"
        f"💉 {escape(data['vac_name'])}\n"
        f"📅 Дата: {format_date(done_d)}\n"
        f"📅 Следующая: {format_date(next_d)}\n"
    )
    if notes:
        text += f"📝 {escape(notes)}"

    await message.answer(text, parse_mode="HTML", reply_markup=back_to_menu_kb)


@router.callback_query(F.data == "med:vaccines:list")
async def cb_vaccines_list(callback: CallbackQuery):
    """Список прививок."""
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    all_vacs = []
    pet_map = {}
    for p in pets:
        pet_map[p["id"]] = p["name"]
        vacs = await api_client.list_vaccinations(p["id"], callback.from_user.id)
        all_vacs.extend(vacs)

    if not all_vacs:
        await callback.message.edit_text(
            "💉 Записей о прививках пока нет.", reply_markup=back_to_menu_kb
        )
    else:
        lines = ["💉 <b>История прививок</b>\n"]
        for v in all_vacs[:20]:
            lines.append(
                f"• <b>{escape(v['name'])}</b> ({escape(pet_map.get(v.get('pet_id', 0), '?'))})\n"
                f"  📅 {format_date(v.get('date_done'))} → след.: {format_date(v.get('next_date'))}"
            )
        await callback.message.edit_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )
    await callback.answer()


# ══════════════════════════════════════════════
#  ВИЗИТЫ К ВЕТЕРИНАРУ
# ══════════════════════════════════════════════


@router.callback_query(F.data == "med:vetvisits:add")
async def cb_vet_add(callback: CallbackQuery, state: FSMContext):
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Сначала добавьте питомца.", reply_markup=add_pet_cta_kb)
        await callback.answer()
        return

    await state.set_state(VetVisitForm.choosing_pet)
    await callback.message.edit_text(
        "🏥 <b>Новый визит к ветеринару</b>\n\nВыберите питомца:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_vetvisit"),
    )
    await callback.answer()


@router.callback_query(VetVisitForm.choosing_pet, F.data.startswith("pet:select_vetvisit:"))
async def cb_vet_pet(callback: CallbackQuery, state: FSMContext):
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return
    pet = await api_client.get_pet(pet_id, callback.from_user.id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return
    await state.update_data(pet_id=pet_id)
    await state.set_state(VetVisitForm.visit_date)
    await callback.message.edit_text(
        "📅 Введите дату визита (ДД.ММ.ГГГГ):",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(VetVisitForm.visit_date)
async def vet_date(message: Message, state: FSMContext):
    d = parse_date(message.text)
    if d is None:
        await message.answer("⚠️ Неверный формат. ДД.ММ.ГГГГ:")
        return
    await state.update_data(visit_date=d.isoformat())
    await state.set_state(VetVisitForm.diagnosis)
    await message.answer("🩺 Диагноз (или <b>-</b> чтобы пропустить):", parse_mode="HTML")


@router.message(VetVisitForm.diagnosis)
async def vet_diagnosis(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(diagnosis="" if text == "-" else text)
    await state.set_state(VetVisitForm.treatment)
    await message.answer("💊 Назначения/лечение (или <b>-</b>):", parse_mode="HTML")


@router.message(VetVisitForm.treatment)
async def vet_treatment(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(treatment="" if text == "-" else text)
    await state.set_state(VetVisitForm.notes)
    await message.answer("📝 Заметки (или <b>-</b>):", parse_mode="HTML")


@router.message(VetVisitForm.notes)
async def vet_notes(message: Message, state: FSMContext):
    notes = message.text.strip()
    if notes == "-":
        notes = ""
    data = await state.get_data()
    await state.clear()

    visit_d = date_type.fromisoformat(data["visit_date"])
    await api_client.create_vet_visit(
        user_id=message.from_user.id,
        pet_id=data["pet_id"],
        visit_date=visit_d,
        diagnosis=data.get("diagnosis", ""),
        treatment=data.get("treatment", ""),
        notes=notes,
    )

    text = (
        "✅ <b>Визит записан!</b>\n\n"
        f"📅 Дата: {format_date(visit_d)}\n"
        f"🩺 Диагноз: {escape(data.get('diagnosis', '')) or '—'}\n"
        f"💊 Лечение: {escape(data.get('treatment', '')) or '—'}\n"
    )
    if notes:
        text += f"📝 {escape(notes)}"

    await message.answer(text, parse_mode="HTML", reply_markup=back_to_menu_kb)


@router.callback_query(F.data == "med:vetvisits:list")
async def cb_vetvisits_list(callback: CallbackQuery):
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    all_visits = []
    pet_map = {}
    for p in pets:
        pet_map[p["id"]] = p["name"]
        visits = await api_client.list_vet_visits(p["id"], callback.from_user.id)
        all_visits.extend(visits)

    if not all_visits:
        await callback.message.edit_text(
            "🏥 Записей о визитах пока нет.", reply_markup=back_to_menu_kb
        )
    else:
        lines = ["🏥 <b>История визитов к ветеринару</b>\n"]
        for v in all_visits[:15]:
            diag = v.get("diagnosis", "")
            treat = v.get("treatment", "")
            lines.append(
                f"• <b>{format_date(v.get('visit_date'))}</b> ({escape(pet_map.get(v.get('pet_id', 0), '?'))})\n"
                f"  🩺 {escape(diag) if diag else '—'} | 💊 {escape(treat) if treat else '—'}"
            )
        await callback.message.edit_text(
            "\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu_kb
        )
    await callback.answer()


# ══════════════════════════════════════════════
#  УЧЁТ ВЕСА
# ══════════════════════════════════════════════


@router.callback_query(F.data == "med:weight:add")
async def cb_weight_add(callback: CallbackQuery, state: FSMContext):
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Сначала добавьте питомца.", reply_markup=add_pet_cta_kb)
        await callback.answer()
        return

    await state.set_state(WeightForm.choosing_pet)
    await callback.message.edit_text(
        "⚖️ <b>Записать вес</b>\n\nВыберите питомца:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_weight"),
    )
    await callback.answer()


@router.callback_query(WeightForm.choosing_pet, F.data.startswith("pet:select_weight:"))
async def cb_weight_pet(callback: CallbackQuery, state: FSMContext):
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return
    pet = await api_client.get_pet(pet_id, callback.from_user.id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return
    await state.update_data(pet_id=pet_id)
    await state.set_state(WeightForm.weight)
    await callback.message.edit_text(
        "⚖️ Введите текущий вес (кг), например: <b>4.5</b>",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(WeightForm.weight)
async def weight_value(message: Message, state: FSMContext):
    w = parse_weight(message.text)
    if w is None:
        await message.answer("⚠️ Введите число (кг), например: 4.5")
        return
    data = await state.get_data()
    await state.clear()

    pet = await api_client.get_pet(data["pet_id"], message.from_user.id)
    if not pet:
        await message.answer("😕 Питомец не найден.", reply_markup=back_to_menu_kb)
        return

    record = await api_client.create_weight_record(message.from_user.id, data["pet_id"], w)
    await api_client.update_pet(data["pet_id"], message.from_user.id, weight=w)

    await message.answer(
        f"✅ Вес записан: <b>{w} кг</b>\n"
        f"📅 {format_date(record.get('recorded_at'))}",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )


@router.callback_query(F.data == "med:weight:list")
async def cb_weight_list(callback: CallbackQuery):
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    all_records = []
    pet_map = {}
    for p in pets:
        pet_map[p["id"]] = p["name"]
        records = await api_client.list_weight_records(p["id"], callback.from_user.id)
        all_records.extend([(r, p["id"]) for r in records])

    if not all_records:
        await callback.message.edit_text("⚖️ Записей веса пока нет.", reply_markup=back_to_menu_kb)
    else:
        lines = ["⚖️ <b>История веса</b>\n"]
        for r, pid in all_records[:20]:
            label = escape(pet_map.get(pid, '?'))
            dt = format_date(r.get('recorded_at'))
            lines.append(f"• {label}: <b>{r['weight']} кг</b> — {dt}")
        await callback.message.edit_text(
            "\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu_kb
        )
    await callback.answer()


@router.callback_query(F.data == "med:weight:chart")
async def cb_weight_chart(callback: CallbackQuery):
    """Генерация графика веса."""
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    all_records = []
    pet_map = {}
    for p in pets:
        pet_map[p["id"]] = p["name"]
        records = await api_client.list_weight_records(p["id"], callback.from_user.id)
        for r in records:
            r["_pet_id"] = p["id"]
        all_records.extend(records)

    if len(all_records) < 2:
        await callback.answer("Нужно минимум 2 записи для графика", show_alert=True)
        return

    try:
        from datetime import datetime

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 5))

        pet_records: dict[int, list] = {}
        for r in all_records:
            pet_records.setdefault(r["_pet_id"], []).append(r)

        for pid, recs in pet_records.items():
            dates = [datetime.fromisoformat(r["recorded_at"]) for r in recs]
            weights = [r["weight"] for r in recs]
            ax.plot(dates, weights, marker="o", label=pet_map.get(pid, f"#{pid}"))

        ax.set_xlabel("Дата")
        ax.set_ylabel("Вес (кг)")
        ax.set_title("📊 Динамика веса")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y"))
        fig.autofmt_xdate()
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150)
        buf.seek(0)
        plt.close(fig)

        photo = BufferedInputFile(buf.read(), filename="weight_chart.png")
        await callback.message.answer_photo(
            photo=photo,
            caption="📊 <b>График изменения веса</b>",
            parse_mode="HTML",
        )
    except ImportError:
        await callback.answer("Matplotlib не установлен. pip install matplotlib", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка генерации графика: {e}")
        await callback.answer("Ошибка при создании графика 😕", show_alert=True)

    await callback.answer()


# ══════════════════════════════════════════════
#  ДОКУМЕНТЫ
# ══════════════════════════════════════════════


@router.callback_query(F.data == "med:documents:add")
async def cb_doc_add(callback: CallbackQuery, state: FSMContext):
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Сначала добавьте питомца.", reply_markup=add_pet_cta_kb)
        await callback.answer()
        return

    await state.set_state(DocumentForm.choosing_pet)
    await callback.message.edit_text(
        "📄 <b>Загрузить документ</b>\n\nВыберите питомца:",
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="select_doc"),
    )
    await callback.answer()


@router.callback_query(DocumentForm.choosing_pet, F.data.startswith("pet:select_doc:"))
async def cb_doc_pet(callback: CallbackQuery, state: FSMContext):
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return
    pet = await api_client.get_pet(pet_id, callback.from_user.id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return
    await state.update_data(pet_id=pet_id)
    await state.set_state(DocumentForm.doc_type)
    await callback.message.edit_text(
        "Выберите тип документа:",
        reply_markup=doc_type_kb,
    )
    await callback.answer()


@router.callback_query(DocumentForm.doc_type, F.data.startswith("doc_type:"))
async def cb_doc_type(callback: CallbackQuery, state: FSMContext):
    doc_type = callback.data.split(":")[1]
    await state.update_data(doc_type=doc_type)
    await state.set_state(DocumentForm.photo)
    await callback.message.edit_text(
        "📷 Отправьте фото документа:",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(DocumentForm.photo, F.photo)
async def doc_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await state.update_data(file_id=photo.file_id)
    await state.set_state(DocumentForm.description)
    await message.answer(
        "📝 Добавьте описание (или <b>-</b> чтобы пропустить):",
        parse_mode="HTML",
    )


@router.message(DocumentForm.photo)
async def doc_photo_invalid(message: Message):
    await message.answer("⚠️ Пожалуйста, отправьте <b>фото</b> документа.", parse_mode="HTML")


@router.message(DocumentForm.description)
async def doc_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    if desc == "-":
        desc = ""
    data = await state.get_data()
    await state.clear()

    doc_names = {"passport": "Ветпаспорт", "certificate": "Справка", "other": "Другое"}

    await api_client.create_document(
        user_id=message.from_user.id,
        pet_id=data["pet_id"],
        doc_type=data["doc_type"],
        file_id=data["file_id"],
        description=desc,
    )

    await message.answer(
        f"✅ Документ сохранён!\n"
        f"📄 Тип: {doc_names.get(data['doc_type'], data['doc_type'])}\n"
        f"📝 {escape(desc) if desc else '—'}",
        reply_markup=back_to_menu_kb,
    )


@router.callback_query(F.data == "med:documents:list")
async def cb_docs_list(callback: CallbackQuery):
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        await callback.message.edit_text("😕 Нет питомцев.", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    all_docs = []
    pet_map = {}
    for p in pets:
        pet_map[p["id"]] = p["name"]
        docs = await api_client.list_documents(p["id"], callback.from_user.id)
        all_docs.extend(docs)

    if not all_docs:
        await callback.message.edit_text("📄 Документов пока нет.", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    doc_names = {"passport": "🪪 Ветпаспорт", "certificate": "📋 Справка", "other": "📄 Другое"}

    for doc in all_docs[:10]:
        caption = (
            f"{doc_names.get(doc.get('doc_type', ''), '📄')} | {escape(pet_map.get(doc.get('pet_id', 0), '?'))}\n"
            f"{escape(doc.get('description', '')) or '—'}"
        )
        await callback.message.answer_photo(photo=doc["file_id"], caption=caption)

    await callback.message.answer(
        f"📄 Показано документов: {min(len(all_docs), 10)}",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer()
