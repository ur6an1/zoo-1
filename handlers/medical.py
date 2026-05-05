"""Обработчики: медицинская карта (прививки, визиты, вес, документы)."""

import io
import logging
from datetime import date as date_type
from html import escape

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database import async_session
from models.models import Pet, Vaccination, VetVisit, WeightRecord, Document
from states.states import VaccinationForm, VetVisitForm, WeightForm, DocumentForm
from keyboards.keyboards import (
    add_pet_cta_kb,
    medical_menu_kb,
    med_section_kb,
    pets_list_kb,
    skip_kb,
    cancel_kb,
    back_to_menu_kb,
    doc_type_kb,
)
from services.access import get_owned_pet
from utils.helpers import callback_int, format_date, parse_date, parse_weight

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
    async with async_session() as session:
        result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = result.scalars().all()

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
    async with async_session() as session:
        pet = await get_owned_pet(session, callback.from_user.id, pet_id)
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

    vac = Vaccination(
        pet_id=data["pet_id"],
        name=data["vac_name"],
        date_done=date_type.fromisoformat(data["date_done"]),
        next_date=next_d,
        notes=notes,
    )

    async with async_session() as session:
        session.add(vac)
        await session.commit()

    text = (
        "✅ <b>Прививка добавлена!</b>\n\n"
        f"💉 {escape(vac.name)}\n"
        f"📅 Дата: {format_date(vac.date_done)}\n"
        f"📅 Следующая: {format_date(vac.next_date)}\n"
    )
    if notes:
        text += f"📝 {escape(notes)}"

    await message.answer(text, parse_mode="HTML", reply_markup=back_to_menu_kb)


@router.callback_query(F.data == "med:vaccines:list")
async def cb_vaccines_list(callback: CallbackQuery):
    """Список прививок."""
    async with async_session() as session:
        # Получаем питомцев пользователя
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
            select(Vaccination)
            .where(Vaccination.pet_id.in_(pet_ids))
            .order_by(Vaccination.date_done.desc())
        )
        vaccinations = result.scalars().all()

    if not vaccinations:
        await callback.message.edit_text(
            "💉 Записей о прививках пока нет.", reply_markup=back_to_menu_kb
        )
    else:
        pet_map = {p.id: p.name for p in pets}
        lines = ["💉 <b>История прививок</b>\n"]
        for v in vaccinations[:20]:
            lines.append(
                f"• <b>{escape(v.name)}</b> ({escape(pet_map.get(v.pet_id, '?'))})\n"
                f"  📅 {format_date(v.date_done)} → след.: {format_date(v.next_date)}"
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
    async with async_session() as session:
        result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = result.scalars().all()

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
    async with async_session() as session:
        pet = await get_owned_pet(session, callback.from_user.id, pet_id)
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

    visit = VetVisit(
        pet_id=data["pet_id"],
        visit_date=date_type.fromisoformat(data["visit_date"]),
        diagnosis=data.get("diagnosis", ""),
        treatment=data.get("treatment", ""),
        notes=notes,
    )

    async with async_session() as session:
        session.add(visit)
        await session.commit()

    text = (
        "✅ <b>Визит записан!</b>\n\n"
        f"📅 Дата: {format_date(visit.visit_date)}\n"
        f"🩺 Диагноз: {escape(visit.diagnosis) if visit.diagnosis else '—'}\n"
        f"💊 Лечение: {escape(visit.treatment) if visit.treatment else '—'}\n"
    )
    if notes:
        text += f"📝 {escape(notes)}"

    await message.answer(text, parse_mode="HTML", reply_markup=back_to_menu_kb)


@router.callback_query(F.data == "med:vetvisits:list")
async def cb_vetvisits_list(callback: CallbackQuery):
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
            select(VetVisit)
            .where(VetVisit.pet_id.in_(pet_ids))
            .order_by(VetVisit.visit_date.desc())
        )
        visits = result.scalars().all()

    if not visits:
        await callback.message.edit_text(
            "🏥 Записей о визитах пока нет.", reply_markup=back_to_menu_kb
        )
    else:
        pet_map = {p.id: p.name for p in pets}
        lines = ["🏥 <b>История визитов к ветеринару</b>\n"]
        for v in visits[:15]:
            lines.append(
                f"• <b>{format_date(v.visit_date)}</b> ({escape(pet_map.get(v.pet_id, '?'))})\n"
                f"  🩺 {escape(v.diagnosis) if v.diagnosis else '—'} | 💊 {escape(v.treatment) if v.treatment else '—'}"
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
    async with async_session() as session:
        result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = result.scalars().all()

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
    async with async_session() as session:
        pet = await get_owned_pet(session, callback.from_user.id, pet_id)
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

    async with async_session() as session:
        pet = await get_owned_pet(session, message.from_user.id, data["pet_id"])
        if not pet:
            await message.answer("😕 Питомец не найден.", reply_markup=back_to_menu_kb)
            return
        record = WeightRecord(pet_id=data["pet_id"], weight=w)
        session.add(record)
        pet.weight = w
        await session.commit()

    await message.answer(
        f"✅ Вес записан: <b>{w} кг</b>\n"
        f"📅 {format_date(record.recorded_at)}",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )


@router.callback_query(F.data == "med:weight:list")
async def cb_weight_list(callback: CallbackQuery):
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
            select(WeightRecord)
            .where(WeightRecord.pet_id.in_(pet_ids))
            .order_by(WeightRecord.recorded_at.desc())
        )
        records = result.scalars().all()

    if not records:
        await callback.message.edit_text("⚖️ Записей веса пока нет.", reply_markup=back_to_menu_kb)
    else:
        pet_map = {p.id: p.name for p in pets}
        lines = ["⚖️ <b>История веса</b>\n"]
        for r in records[:20]:
            lines.append(f"• {escape(pet_map.get(r.pet_id, '?'))}: <b>{r.weight} кг</b> — {format_date(r.recorded_at)}")
        await callback.message.edit_text(
            "\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu_kb
        )
    await callback.answer()


@router.callback_query(F.data == "med:weight:chart")
async def cb_weight_chart(callback: CallbackQuery):
    """Генерация графика веса."""
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
            select(WeightRecord)
            .where(WeightRecord.pet_id.in_(pet_ids))
            .order_by(WeightRecord.recorded_at)
        )
        records = result.scalars().all()

    if len(records) < 2:
        await callback.answer("Нужно минимум 2 записи для графика", show_alert=True)
        return

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        pet_map = {p.id: p.name for p in pets}

        fig, ax = plt.subplots(figsize=(10, 5))

        # Группируем по питомцам
        pet_records: dict[int, list] = {}
        for r in records:
            pet_records.setdefault(r.pet_id, []).append(r)

        for pid, recs in pet_records.items():
            dates = [r.recorded_at for r in recs]
            weights = [r.weight for r in recs]
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
    async with async_session() as session:
        result = await session.execute(
            select(Pet).where(Pet.user_id == callback.from_user.id)
        )
        pets = result.scalars().all()

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
    async with async_session() as session:
        pet = await get_owned_pet(session, callback.from_user.id, pet_id)
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

    doc = Document(
        pet_id=data["pet_id"],
        doc_type=data["doc_type"],
        file_id=data["file_id"],
        description=desc,
    )

    async with async_session() as session:
        session.add(doc)
        await session.commit()

    await message.answer(
        f"✅ Документ сохранён!\n"
        f"📄 Тип: {doc_names.get(doc.doc_type, doc.doc_type)}\n"
        f"📝 {escape(desc) if desc else '—'}",
        reply_markup=back_to_menu_kb,
    )


@router.callback_query(F.data == "med:documents:list")
async def cb_docs_list(callback: CallbackQuery):
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
            select(Document)
            .where(Document.pet_id.in_(pet_ids))
            .order_by(Document.uploaded_at.desc())
        )
        docs = result.scalars().all()

    if not docs:
        await callback.message.edit_text("📄 Документов пока нет.", reply_markup=back_to_menu_kb)
        await callback.answer()
        return

    doc_names = {"passport": "🪪 Ветпаспорт", "certificate": "📋 Справка", "other": "📄 Другое"}
    pet_map = {p.id: p.name for p in pets}

    # Отправляем каждый документ как фото
    for doc in docs[:10]:
        caption = (
            f"{doc_names.get(doc.doc_type, '📄')} | {escape(pet_map.get(doc.pet_id, '?'))}\n"
            f"{escape(doc.description) if doc.description else '—'}"
        )
        await callback.message.answer_photo(photo=doc.file_id, caption=caption)

    await callback.message.answer(
        f"📄 Показано документов: {min(len(docs), 10)}",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer()
