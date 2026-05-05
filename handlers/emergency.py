"""Обработчики: экстренная помощь (SOS) + поиск ветклиник с рейтингами."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.keyboards import back_to_menu_kb, clinic_radius_kb, emergency_kb, location_kb, main_menu_kb
from services.clinics import search_and_format
from services.content import (
    EMERGENCY_GENERAL,
    EMERGENCY_INJURY,
    EMERGENCY_OVERHEAT,
    EMERGENCY_POISONING,
)
from states.states import ClinicSearchForm
from utils.helpers import callback_int

logger = logging.getLogger(__name__)
router = Router(name="emergency")


@router.message(F.text == "🆘 Экстренная помощь")
async def emergency_menu(message: Message):
    await message.answer(
        "🆘 <b>Экстренная помощь</b>\n\n"
        "Выберите ситуацию или найдите ближайшую ветклинику:",
        parse_mode="HTML",
        reply_markup=emergency_kb,
    )


@router.callback_query(F.data == "sos:menu")
async def emergency_menu_cb(callback: CallbackQuery):
    await callback.message.edit_text(
        "🆘 <b>Экстренная помощь</b>\n\n"
        "Выберите ситуацию или найдите ближайшую ветклинику:",
        parse_mode="HTML",
        reply_markup=emergency_kb,
    )
    await callback.answer()


@router.callback_query(F.data == "sos:clinic")
async def cb_sos_clinic(callback: CallbackQuery, state: FSMContext):
    """Быстрый поиск ветклиник — отправьте геолокацию."""
    await state.set_state(ClinicSearchForm.waiting_location)
    await state.update_data(clinic_radius=5000)
    await callback.message.answer(
        "🏥 <b>Поиск ветклиники</b>\n\n"
        "Отправьте ваше местоположение — я найду ближайшие ветклиники "
        "с адресами, телефонами и ссылками на карты.\n\n"
        "📍 Нажмите кнопку ниже:",
        parse_mode="HTML",
        reply_markup=location_kb,
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data == "sos:clinic_rated")
async def cb_sos_clinic_rated(callback: CallbackQuery, state: FSMContext):
    """Поиск клиник с выбором радиуса."""
    await state.set_state(ClinicSearchForm.waiting_filters)
    await callback.message.edit_text(
        "🏥 <b>Поиск ветклиник</b>\n\n"
        "Выберите радиус поиска:",
        parse_mode="HTML",
        reply_markup=clinic_radius_kb,
    )
    await callback.answer()


@router.callback_query(ClinicSearchForm.waiting_filters, F.data.startswith("clinic:r:"))
async def cb_clinic_radius(callback: CallbackQuery, state: FSMContext):
    """Выбран радиус — просим геолокацию."""
    radius = callback_int(callback.data, 2, min_value=500)
    if radius is None:
        await callback.answer("Некорректный радиус", show_alert=True)
        return
    await state.update_data(clinic_radius=radius)
    await state.set_state(ClinicSearchForm.waiting_location)
    await callback.message.answer(
        f"🏥 Радиус: <b>{radius // 1000} км</b>\n\n"
        "📍 Теперь отправьте местоположение:",
        parse_mode="HTML",
        reply_markup=location_kb,
    )
    await callback.answer()


@router.message(ClinicSearchForm.waiting_location, F.location)
async def handle_location(message: Message, state: FSMContext):
    """Обработка геолокации — поиск ветклиник через Overpass API."""
    lat = message.location.latitude
    lon = message.location.longitude

    data = await state.get_data()
    radius = data.get("clinic_radius", 5000)
    await state.clear()

    processing_msg = await message.answer(
        "🔍 <b>Ищу ветклиники рядом...</b>",
        parse_mode="HTML",
    )

    result = await search_and_format(lat, lon, radius)

    await processing_msg.edit_text(
        result,
        parse_mode="HTML",
        reply_markup=back_to_menu_kb,
        disable_web_page_preview=True,
    )

    # Также показываем ссылки на карты
    yandex_url = f"https://yandex.ru/maps/?ll={lon},{lat}&z=14&text=ветеринарная клиника"
    google_url = f"https://www.google.com/maps/search/vet+clinic/@{lat},{lon},14z"

    await message.answer(
        f"🗺 <b>Карты с ветклиниками:</b>\n"
        f'• <a href="{yandex_url}">Яндекс Карты</a>\n'
        f'• <a href="{google_url}">Google Maps</a>\n\n'
        f"📞 <b>В критической ситуации — звоните в ближайшую клинику!</b>",
        parse_mode="HTML",
        reply_markup=main_menu_kb,
        disable_web_page_preview=True,
    )


@router.message(ClinicSearchForm.waiting_location)
async def location_expected(message: Message):
    await message.answer(
        "📍 Сейчас я жду именно <b>геолокацию</b>.\n\n"
        "Нажмите кнопку «Отправить местоположение» ниже или вернитесь в меню.",
        parse_mode="HTML",
        reply_markup=location_kb,
    )


@router.callback_query(F.data == "sos:poisoning")
async def cb_sos_poisoning(callback: CallbackQuery):
    await callback.message.edit_text(EMERGENCY_POISONING, parse_mode="HTML", reply_markup=back_to_menu_kb)
    await callback.answer()


@router.callback_query(F.data == "sos:injury")
async def cb_sos_injury(callback: CallbackQuery):
    await callback.message.edit_text(EMERGENCY_INJURY, parse_mode="HTML", reply_markup=back_to_menu_kb)
    await callback.answer()


@router.callback_query(F.data == "sos:overheat")
async def cb_sos_overheat(callback: CallbackQuery):
    await callback.message.edit_text(EMERGENCY_OVERHEAT, parse_mode="HTML", reply_markup=back_to_menu_kb)
    await callback.answer()


@router.callback_query(F.data == "sos:general")
async def cb_sos_general(callback: CallbackQuery):
    await callback.message.edit_text(EMERGENCY_GENERAL, parse_mode="HTML", reply_markup=back_to_menu_kb)
    await callback.answer()
