"""Обработчики: профили питомцев (добавление, просмотр, редактирование, удаление, статистика, экспорт)."""

import logging
from datetime import datetime
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import api_client
from bot.keyboards.keyboards import (
    back_to_menu_kb,
    cancel_kb,
    confirm_delete_kb,
    main_menu_kb,
    pet_edit_kb,
    pet_profile_kb,
    pets_list_kb,
    post_pet_created_kb,
    skip_kb,
    species_kb,
)
from bot.states.states import EditPetForm, PetForm
from bot.utils.helpers import callback_int, callback_part, format_date, parse_date, parse_weight

logger = logging.getLogger(__name__)
router = Router(name="pets")


def _subscription_upgrade_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐️ Подписка", callback_data="settings:subscription")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")],
        ]
    )


# ──────────────────── СПИСОК ПИТОМЦЕВ ────────────────────


@router.message(F.text == "🐾 Мои питомцы")
async def my_pets(message: Message):
    """Показать список питомцев."""
    await api_client.track_user_activity(message.from_user.id, source="pets")
    pets = await api_client.list_pets(message.from_user.id)

    if not pets:
        await message.answer(
            "🐾 У вас пока нет питомцев.\n\n"
            "Давайте добавим вашего первого друга! 🎉",
            reply_markup=pets_list_kb([], action="view"),
        )
    else:
        await message.answer(
            f"🐾 <b>Ваши питомцы</b> ({len(pets)}):\n\n"
            "Выберите питомца для просмотра профиля:",
            parse_mode="HTML",
            reply_markup=pets_list_kb(pets, action="view"),
        )


@router.callback_query(F.data == "pet:list")
async def cb_pet_list(callback: CallbackQuery):
    """Список питомцев (inline)."""
    pets = await api_client.list_pets(callback.from_user.id)

    if not pets:
        text = "🐾 У вас пока нет питомцев.\nДобавьте первого! 🎉"
    else:
        text = f"🐾 <b>Ваши питомцы</b> ({len(pets)}):"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=pets_list_kb(pets, action="view"),
    )
    await callback.answer()


# ──────────────────── ПРОСМОТР ПРОФИЛЯ ────────────────────


@router.callback_query(F.data.startswith("pet:view:"))
async def cb_pet_view(callback: CallbackQuery):
    """Просмотр профиля питомца."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return
    pet = await api_client.get_pet(pet_id, callback.from_user.id)

    if not pet:
        await callback.answer("Питомец не найден 😕", show_alert=True)
        return

    text = (
        f"{pet['species_emoji']} <b>{escape(pet['name'])}</b>\n\n"
        f"📋 Вид: {escape(pet['species'])}\n"
        f"🐾 Порода: {escape(pet['breed']) if pet['breed'] else 'не указана'}\n"
        f"📅 Дата рождения: {format_date(pet.get('birth_date'))}\n"
        f"🎂 Возраст: {pet.get('age_str', 'не указан')}\n"
        f"⚖️ Вес: {str(pet['weight']) + ' кг' if pet.get('weight') else 'не указан'}\n"
    )

    if pet.get("photo_file_id"):
        await callback.message.answer_photo(
            photo=pet["photo_file_id"],
            caption=text,
            parse_mode="HTML",
            reply_markup=pet_profile_kb(pet["id"]),
        )
        try:
            await callback.message.delete()
        except Exception:
            pass
    else:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=pet_profile_kb(pet["id"]),
        )
    await callback.answer()


# ──────────────────── ДОБАВЛЕНИЕ ПИТОМЦА ────────────────────


@router.callback_query(F.data == "pet:add")
async def cb_pet_add(callback: CallbackQuery, state: FSMContext):
    """Начало добавления питомца."""
    allowed, _remaining = await api_client.check_pet_limit(callback.from_user.id)
    if not allowed:
        plan_tier = await api_client.get_plan_tier(callback.from_user.id)
        current_limit = 5 if plan_tier == "basic" else 2
        await callback.message.edit_text(
            "🔒 <b>Достигнут лимит питомцев</b>\n\n"
            f"На вашем тарифе можно добавить до <b>{current_limit}</b> питомцев.\n"
            "Подключите или повысьте подписку, чтобы добавить больше.",
            parse_mode="HTML",
            reply_markup=_subscription_upgrade_kb(),
        )
        await callback.answer("Достигнут лимит питомцев", show_alert=True)
        return

    await api_client.track_event(callback.from_user.id, "onboarding_started", source="pet_add")
    await state.set_state(PetForm.name)
    await callback.message.edit_text(
        "🐾 <b>Добавление питомца</b>\n\n"
        "Как зовут вашего питомца? Введите имя:",
        parse_mode="HTML",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(PetForm.name)
async def pet_name(message: Message, state: FSMContext):
    """Получаем имя питомца."""
    name = message.text.strip()
    if len(name) > 100:
        await message.answer("⚠️ Имя слишком длинное (макс. 100 символов). Попробуйте ещё раз:")
        return
    if len(name) < 1:
        await message.answer("⚠️ Введите имя питомца:")
        return

    await state.update_data(name=name)
    await state.set_state(PetForm.species)
    await message.answer(
        f"Отлично! <b>{name}</b> — замечательное имя! 🥰\n\n"
        "Выберите вид питомца:",
        parse_mode="HTML",
        reply_markup=species_kb,
    )


@router.callback_query(PetForm.species, F.data.startswith("species:"))
async def pet_species(callback: CallbackQuery, state: FSMContext):
    """Получаем вид питомца."""
    species = callback.data.split(":")[1]
    await state.update_data(species=species)
    await state.set_state(PetForm.breed)
    await callback.message.edit_text(
        f"Вид: <b>{species}</b> ✅\n\n"
        "Какой породы ваш питомец?\n"
        "Напишите породу или нажмите «Пропустить»:",
        parse_mode="HTML",
        reply_markup=skip_kb,
    )
    await callback.answer()


@router.callback_query(PetForm.breed, F.data == "skip")
async def pet_breed_skip(callback: CallbackQuery, state: FSMContext):
    """Пропуск породы."""
    await state.update_data(breed="")
    await state.set_state(PetForm.birth_date)
    await callback.message.edit_text(
        "Порода: пропущено ✅\n\n"
        "📅 Когда родился ваш питомец?\n"
        "Введите дату в формате <b>ДД.ММ.ГГГГ</b>\n"
        "или нажмите «Пропустить»:",
        parse_mode="HTML",
        reply_markup=skip_kb,
    )
    await callback.answer()


@router.message(PetForm.breed)
async def pet_breed(message: Message, state: FSMContext):
    """Получаем породу."""
    breed = message.text.strip()
    if len(breed) > 100:
        await message.answer("⚠️ Слишком длинное название (макс. 100 символов). Попробуйте ещё раз:")
        return
    await state.update_data(breed=breed)
    await state.set_state(PetForm.birth_date)
    await message.answer(
        f"Порода: <b>{breed}</b> ✅\n\n"
        "📅 Когда родился ваш питомец?\n"
        "Введите дату в формате <b>ДД.ММ.ГГГГ</b>\n"
        "или нажмите «Пропустить»:",
        parse_mode="HTML",
        reply_markup=skip_kb,
    )


@router.callback_query(PetForm.birth_date, F.data == "skip")
async def pet_birth_skip(callback: CallbackQuery, state: FSMContext):
    """Пропуск даты рождения."""
    await state.update_data(birth_date=None)
    await state.set_state(PetForm.weight)
    await callback.message.edit_text(
        "Дата рождения: пропущено ✅\n\n"
        "⚖️ Сколько весит ваш питомец (в кг)?\n"
        "Например: <b>4.5</b>\n"
        "или нажмите «Пропустить»:",
        parse_mode="HTML",
        reply_markup=skip_kb,
    )
    await callback.answer()


@router.message(PetForm.birth_date)
async def pet_birth_date(message: Message, state: FSMContext):
    """Получаем дату рождения."""
    d = parse_date(message.text)
    if d is None:
        await message.answer(
            "⚠️ Неверный формат даты.\n"
            "Введите дату в формате <b>ДД.ММ.ГГГГ</b> (например, 15.03.2020):",
            parse_mode="HTML",
            reply_markup=skip_kb,
        )
        return

    await state.update_data(birth_date=d.isoformat())
    await state.set_state(PetForm.weight)
    await message.answer(
        f"Дата рождения: <b>{format_date(d)}</b> ✅\n\n"
        "⚖️ Сколько весит ваш питомец (в кг)?\n"
        "Например: <b>4.5</b>\n"
        "или нажмите «Пропустить»:",
        parse_mode="HTML",
        reply_markup=skip_kb,
    )


@router.callback_query(PetForm.weight, F.data == "skip")
async def pet_weight_skip(callback: CallbackQuery, state: FSMContext):
    """Пропуск веса."""
    await state.update_data(weight=None)
    await state.set_state(PetForm.photo)
    await callback.message.edit_text(
        "Вес: пропущено ✅\n\n"
        "📷 Отправьте фото вашего питомца\n"
        "или нажмите «Пропустить»:",
        parse_mode="HTML",
        reply_markup=skip_kb,
    )
    await callback.answer()


@router.message(PetForm.weight)
async def pet_weight(message: Message, state: FSMContext):
    """Получаем вес."""
    w = parse_weight(message.text)
    if w is None:
        await message.answer(
            "⚠️ Неверный формат веса.\n"
            "Введите число от 0.01 до 999 (в кг), например: <b>4.5</b>",
            parse_mode="HTML",
            reply_markup=skip_kb,
        )
        return

    await state.update_data(weight=w)
    await state.set_state(PetForm.photo)
    await message.answer(
        f"Вес: <b>{w} кг</b> ✅\n\n"
        "📷 Отправьте фото вашего питомца\n"
        "или нажмите «Пропустить»:",
        parse_mode="HTML",
        reply_markup=skip_kb,
    )


@router.callback_query(PetForm.photo, F.data == "skip")
async def pet_photo_skip(callback: CallbackQuery, state: FSMContext):
    """Пропуск фото — сохраняем питомца."""
    await state.update_data(photo_file_id=None)
    await _save_pet(callback.message, state, callback.from_user.id)
    await callback.answer()


@router.message(PetForm.photo, F.photo)
async def pet_photo(message: Message, state: FSMContext):
    """Получаем фото."""
    photo = message.photo[-1]
    await state.update_data(photo_file_id=photo.file_id)
    await _save_pet(message, state, message.from_user.id)


@router.message(PetForm.photo)
async def pet_photo_invalid(message: Message):
    """Невалидный ввод вместо фото."""
    await message.answer(
        "⚠️ Пожалуйста, отправьте <b>фото</b> или нажмите «Пропустить».",
        parse_mode="HTML",
        reply_markup=skip_kb,
    )


async def _save_pet(message: Message, state: FSMContext, user_id: int):
    """Сохранение питомца через backend API."""
    data = await state.get_data()
    await state.clear()

    from datetime import date as date_type

    birth_date = None
    if data.get("birth_date"):
        birth_date = date_type.fromisoformat(data["birth_date"])

    pet = await api_client.create_pet(
        user_id=user_id,
        name=data["name"],
        species=data["species"],
        breed=data.get("breed", ""),
        birth_date=birth_date,
        weight=data.get("weight"),
        photo_file_id=data.get("photo_file_id"),
    )

    pet_count = await api_client.get_pet_count(user_id)

    logger.info("Питомец '%s' (id=%s) добавлен пользователем %s", pet["name"], pet["id"], user_id)
    await api_client.track_event(user_id, "pet_created", source="pets", payload={"pet_id": pet["id"]})
    if pet_count == 1:
        await api_client.track_event(user_id, "first_value_reached", source="first_pet", payload={"pet_id": pet["id"]})

    text = (
        f"🎉 <b>Питомец добавлен!</b>\n\n"
        f"{pet['species_emoji']} <b>{escape(pet['name'])}</b>\n"
        f"📋 Вид: {escape(pet['species'])}\n"
        f"🐾 Порода: {escape(pet['breed']) if pet['breed'] else 'не указана'}\n"
        f"📅 Дата рождения: {format_date(pet.get('birth_date'))}\n"
        f"⚖️ Вес: {str(pet['weight']) + ' кг' if pet.get('weight') else 'не указан'}\n"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=pet_profile_kb(pet["id"]),
    )
    await message.answer(
        "Следующий шаг: поставьте первое напоминание или цель по весу, чтобы бот начал приносить регулярную пользу.",
        reply_markup=post_pet_created_kb(pet["id"]),
    )


# ──────────────────── РЕДАКТИРОВАНИЕ ────────────────────


@router.callback_query(F.data.startswith("pet:edit:"))
async def cb_pet_edit(callback: CallbackQuery):
    """Меню редактирования."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return
    pet = await api_client.get_pet(pet_id, callback.from_user.id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return
    await callback.message.edit_text(
        "✏️ <b>Редактирование</b>\n\nВыберите, что хотите изменить:",
        parse_mode="HTML",
        reply_markup=pet_edit_kb(pet_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pet:edit_field:"))
async def cb_edit_field(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования конкретного поля."""
    field = callback_part(callback.data, 2)
    pet_id = callback_int(callback.data, 3)
    if not field or pet_id is None:
        await callback.answer("Некорректные параметры", show_alert=True)
        return
    pet = await api_client.get_pet(pet_id, callback.from_user.id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return
    await state.update_data(edit_pet_id=pet_id)

    prompts = {
        "name": ("📝 Введите новое имя:", EditPetForm.editing_name),
        "breed": ("🐾 Введите новую породу:", EditPetForm.editing_breed),
        "birth": ("📅 Введите новую дату рождения (ДД.ММ.ГГГГ):", EditPetForm.editing_birth_date),
        "weight": ("⚖️ Введите новый вес (кг):", EditPetForm.editing_weight),
        "photo": ("📷 Отправьте новое фото:", EditPetForm.editing_photo),
    }

    prompt, new_state = prompts[field]
    await state.set_state(new_state)
    await callback.message.edit_text(
        prompt,
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(EditPetForm.editing_name)
async def edit_name(message: Message, state: FSMContext):
    """Сохранение нового имени."""
    name = message.text.strip()
    if not name or len(name) > 100:
        await message.answer("⚠️ Имя должно быть от 1 до 100 символов:")
        return
    data = await state.get_data()
    pet_id = data["edit_pet_id"]
    await state.clear()

    pet = await api_client.update_pet(pet_id, message.from_user.id, name=name)
    if not pet:
        await message.answer("😕 Питомец не найден.", reply_markup=back_to_menu_kb)
        return

    await message.answer(f"✅ Имя изменено на <b>{escape(name)}</b>", parse_mode="HTML", reply_markup=main_menu_kb)


@router.message(EditPetForm.editing_breed)
async def edit_breed(message: Message, state: FSMContext):
    """Сохранение новой породы."""
    breed = message.text.strip()
    data = await state.get_data()
    pet_id = data["edit_pet_id"]
    await state.clear()

    pet = await api_client.update_pet(pet_id, message.from_user.id, breed=breed)
    if not pet:
        await message.answer("😕 Питомец не найден.", reply_markup=back_to_menu_kb)
        return

    await message.answer(f"✅ Порода изменена на <b>{escape(breed)}</b>", parse_mode="HTML", reply_markup=main_menu_kb)


@router.message(EditPetForm.editing_birth_date)
async def edit_birth(message: Message, state: FSMContext):
    """Сохранение новой даты рождения."""
    d = parse_date(message.text)
    if d is None:
        await message.answer("⚠️ Неверный формат. Введите дату в формате ДД.ММ.ГГГГ:")
        return
    data = await state.get_data()
    pet_id = data["edit_pet_id"]
    await state.clear()

    pet = await api_client.update_pet(pet_id, message.from_user.id, birth_date=d.isoformat())
    if not pet:
        await message.answer("😕 Питомец не найден.", reply_markup=back_to_menu_kb)
        return

    await message.answer(f"✅ Дата рождения: <b>{format_date(d)}</b>", parse_mode="HTML", reply_markup=main_menu_kb)


@router.message(EditPetForm.editing_weight)
async def edit_weight(message: Message, state: FSMContext):
    """Сохранение нового веса."""
    w = parse_weight(message.text)
    if w is None:
        await message.answer("⚠️ Неверный формат. Введите вес в кг (например, 4.5):")
        return
    data = await state.get_data()
    pet_id = data["edit_pet_id"]
    await state.clear()

    pet = await api_client.update_pet(pet_id, message.from_user.id, weight=w)
    if not pet:
        await message.answer("😕 Питомец не найден.", reply_markup=back_to_menu_kb)
        return

    await message.answer(f"✅ Вес изменён: <b>{w} кг</b>", parse_mode="HTML", reply_markup=main_menu_kb)


@router.message(EditPetForm.editing_photo, F.photo)
async def edit_photo(message: Message, state: FSMContext):
    """Сохранение нового фото."""
    photo = message.photo[-1]
    data = await state.get_data()
    pet_id = data["edit_pet_id"]
    await state.clear()

    pet = await api_client.update_pet(pet_id, message.from_user.id, photo_file_id=photo.file_id)
    if not pet:
        await message.answer("😕 Питомец не найден.", reply_markup=back_to_menu_kb)
        return

    await message.answer("✅ Фото обновлено!", reply_markup=main_menu_kb)


# ──────────────────── УДАЛЕНИЕ ────────────────────


@router.callback_query(F.data.startswith("pet:confirm_delete:"))
async def cb_confirm_delete(callback: CallbackQuery):
    """Подтверждение удаления."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return
    pet = await api_client.get_pet(pet_id, callback.from_user.id)
    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить <b>{pet['name']}</b>?\n\n"
        "Все данные питомца (медкарта, напоминания, дневник) будут удалены!",
        parse_mode="HTML",
        reply_markup=confirm_delete_kb(pet_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pet:delete:"))
async def cb_delete_pet(callback: CallbackQuery):
    """Удаление питомца."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return

    pet = await api_client.get_pet(pet_id, callback.from_user.id)
    if pet:
        deleted = await api_client.delete_pet(pet_id, callback.from_user.id)
        if deleted:
            logger.info("Питомец '%s' (id=%s) удалён", pet["name"], pet_id)
            await callback.message.edit_text(
                f"🗑 Питомец <b>{pet['name']}</b> удалён.",
                parse_mode="HTML",
                reply_markup=back_to_menu_kb,
            )
        else:
            await callback.message.edit_text(
                "😕 Питомец не найден.",
                reply_markup=back_to_menu_kb,
            )
    else:
        await callback.message.edit_text(
            "😕 Питомец не найден.",
            reply_markup=back_to_menu_kb,
        )
    await callback.answer()


# ══════════════════════════════════════════════
#  СТАТИСТИКА ПИТОМЦА
# ══════════════════════════════════════════════


@router.callback_query(F.data.startswith("pet:stats:"))
async def cb_pet_stats(callback: CallbackQuery):
    """Дашборд со статистикой питомца."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return

    stats = await api_client.get_pet_stats(pet_id, callback.from_user.id)
    if not stats:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    pet = stats["pet"]
    counts = stats["counts"]

    text = (
        f"📊 <b>Статистика: {pet['species_emoji']} {pet['name']}</b>\n\n"
        f"📋 <b>Профиль:</b>\n"
        f"   Вид: {pet['species']} | Порода: {pet['breed'] or '—'}\n"
        f"   Возраст: {pet.get('age_str', '—')} | Вес: {str(pet['weight']) + ' кг' if pet.get('weight') else '—'}\n\n"
        f"📈 <b>Записи:</b>\n"
        f"   💉 Прививки: {counts['vaccinations']}\n"
        f"   🏥 Визиты к ветеринару: {counts['vet_visits']}\n"
        f"   ⚖️ Записей веса: {counts['weight_records']}\n"
        f"   🍽 Приёмов пищи: {counts['food_entries']}\n"
        f"   💧 Записей воды: {counts['water_entries']}\n"
        f"   ⚠️ Аллергии: {counts['allergies']}\n"
        f"   📄 Документы: {counts['documents']}\n"
        f"   ⏰ Активных напоминаний: {counts['active_reminders']}\n\n"
        f"📅 <b>Важные даты:</b>\n"
    )

    last_vac = stats.get("last_vaccination")
    next_vac = stats.get("next_vaccination")
    last_visit = stats.get("last_visit")
    last_weight = stats.get("last_weight")

    if last_vac:
        text += f"   💉 Последняя прививка: {format_date(last_vac['date_done'])} ({last_vac['name']})\n"
    if next_vac:
        text += f"   💉 Следующая прививка: {format_date(next_vac['next_date'])} ({next_vac['name']})\n"
    if last_visit:
        text += f"   🏥 Последний визит: {format_date(last_visit['visit_date'])}\n"
    if last_weight:
        text += f"   ⚖️ Последний вес: {last_weight['weight']} кг ({format_date(last_weight['recorded_at'])})\n"

    if not any([last_vac, next_vac, last_visit, last_weight]):
        text += "   Пока нет записей. Начните вести учёт! 📝\n"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
    )
    await callback.answer()


# ══════════════════════════════════════════════
#  ЭКСПОРТ ДАННЫХ ПИТОМЦА
# ══════════════════════════════════════════════


@router.callback_query(F.data.startswith("pet:export:"))
async def cb_pet_export(callback: CallbackQuery):
    """Экспорт данных питомца в текстовый файл."""
    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return

    export = await api_client.get_pet_export(pet_id, callback.from_user.id)
    if not export:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    pet = export["pet"]

    lines = []
    lines.append(f"{'='*50}")
    lines.append(f"КАРТОЧКА ПИТОМЦА: {pet['name']}")
    lines.append(f"Экспорт: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    lines.append(f"{'='*50}\n")

    lines.append("[ПРОФИЛЬ]")
    lines.append(f"Имя: {pet['name']}")
    lines.append(f"Вид: {pet['species']}")
    lines.append(f"Порода: {pet['breed'] or '—'}")
    lines.append(f"Дата рождения: {format_date(pet.get('birth_date'))}")
    lines.append(f"Возраст: {pet.get('age_str', '—')}")
    lines.append(f"Вес: {str(pet['weight']) + ' кг' if pet.get('weight') else '—'}")

    vaccinations = export.get("vaccinations", [])
    if vaccinations:
        lines.append(f"\n[ПРИВИВКИ] ({len(vaccinations)})")
        for v in vaccinations:
            lines.append(f"  {format_date(v['date_done'])} — {v['name']} (след.: {format_date(v.get('next_date'))})")
            if v.get("notes"):
                lines.append(f"    Заметки: {v['notes']}")

    visits = export.get("vet_visits", [])
    if visits:
        lines.append(f"\n[ВИЗИТЫ К ВЕТЕРИНАРУ] ({len(visits)})")
        for v in visits:
            lines.append(f"  {format_date(v['visit_date'])}")
            if v.get("diagnosis"):
                lines.append(f"    Диагноз: {v['diagnosis']}")
            if v.get("treatment"):
                lines.append(f"    Лечение: {v['treatment']}")

    weights = export.get("weight_records", [])
    if weights:
        lines.append(f"\n[ИСТОРИЯ ВЕСА] ({len(weights)})")
        for w in weights:
            lines.append(f"  {format_date(w['recorded_at'])} — {w['weight']} кг")

    allergies = export.get("allergies", [])
    if allergies:
        lines.append(f"\n[АЛЛЕРГИИ] ({len(allergies)})")
        for a in allergies:
            lines.append(f"  {a['allergen']} — {a.get('reaction') or '—'}")

    lines.append(f"\n{'='*50}")
    lines.append("Сгенерировано ботом ZooBuddy")

    content = "\n".join(lines)
    file = BufferedInputFile(
        content.encode("utf-8"),
        filename=f"{pet['name']}_карточка.txt",
    )

    await callback.message.answer_document(
        document=file,
        caption=f"📤 Карточка питомца <b>{pet['name']}</b>",
        parse_mode="HTML",
    )
    await callback.answer("Экспорт готов! ✅")


# ══════════════════════════════════════════════
#  ЭКСПОРТ В PDF
# ══════════════════════════════════════════════


@router.callback_query(F.data.startswith("pet:export_pdf:"))
async def cb_pet_export_pdf(callback: CallbackQuery):
    """Экспорт данных питомца в PDF."""
    if not await api_client.can_use_pdf_export(callback.from_user.id):
        await callback.message.answer(
            "🔒 <b>PDF-экспорт доступен только в тарифе PRO.</b>\n\n"
            "Подключите или повысьте подписку, чтобы скачать PDF-карточку.",
            parse_mode="HTML",
            reply_markup=_subscription_upgrade_kb(),
        )
        await callback.answer("Доступно только в PRO", show_alert=True)
        return

    pet_id = callback_int(callback.data, 2)
    if pet_id is None:
        await callback.answer("Некорректный питомец", show_alert=True)
        return

    export = await api_client.get_pet_export(pet_id, callback.from_user.id)
    if not export:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    pet = export["pet"]

    from backend.backend.services.pdf_export import generate_pet_pdf

    pet_data = {
        "name": pet["name"],
        "species": pet["species"],
        "breed": pet.get("breed", ""),
        "birth_date": format_date(pet.get("birth_date")),
        "age": pet.get("age_str", ""),
        "weight": pet.get("weight"),
        "target_weight": pet.get("target_weight"),
    }

    vac_data = [{"name": v["name"], "date_done": format_date(v["date_done"]),
                 "next_date": format_date(v.get("next_date")), "notes": v.get("notes", "")}
                for v in export.get("vaccinations", [])]
    visit_data = [{"visit_date": format_date(v["visit_date"]), "diagnosis": v.get("diagnosis", ""),
                   "treatment": v.get("treatment", "")}
                  for v in export.get("vet_visits", [])]
    weight_data = [{"weight": w["weight"], "recorded_at": format_date(w["recorded_at"])}
                   for w in export.get("weight_records", [])]
    allergy_data = [{"allergen": a["allergen"], "reaction": a.get("reaction", "")}
                    for a in export.get("allergies", [])]

    pdf_bytes = generate_pet_pdf(pet_data, vac_data, visit_data, weight_data, allergy_data)

    if pdf_bytes:
        file = BufferedInputFile(pdf_bytes, filename=f"{pet['name']}_карточка.pdf")
        await callback.message.answer_document(
            document=file,
            caption=f"📄 PDF-карточка питомца <b>{pet['name']}</b>",
            parse_mode="HTML",
        )
        await api_client.track_event(
            callback.from_user.id,
            "premium_feature_used",
            source="pdf_export",
            payload={"pet_id": pet["id"]},
        )
        await callback.answer("PDF готов! ✅")
    else:
        await callback.answer("Ошибка генерации PDF. Попробуйте TXT-экспорт.", show_alert=True)
