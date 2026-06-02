"""Юридические документы и поддержка: /terms, /privacy, /support, /delete_me.

⚠️ ПЕРЕД ЗАПУСКОМ ЗАПОЛНИТЬ реквизиты продавца и контакт поддержки ниже.
Тексты — рабочие шаблоны под подписочный инфосервис в РФ; при росте оборота
показать юристу.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import api_client

logger = logging.getLogger(__name__)
router = Router(name="legal")

# ═══════════ РЕКВИЗИТЫ — ЗАПОЛНИТЬ ПЕРЕД ПЛАТНЫМ ТРАФИКОМ ═══════════
SELLER_NAME = "Самозанятый (НПД) [ФИО — ЗАПОЛНИТЬ]"
SELLER_INN = "[ИНН — ЗАПОЛНИТЬ]"
SUPPORT_CONTACT = "@zoobuddy_support"  # TODO: реальный телеграм поддержки
SUPPORT_EMAIL = "[email — ЗАПОЛНИТЬ]"
# ═══════════════════════════════════════════════════════════════════

OFFER_TEXT = (
    "📄 <b>Публичная оферта</b>\n\n"
    f"Продавец: {SELLER_NAME}, ИНН {SELLER_INN}.\n"
    "Сервис: Telegram-бот <b>ZooBuddy</b> — информационный помощник по уходу за питомцами "
    "(карточка питомца, напоминания, AI-подсказки).\n\n"
    "<b>1. Предмет.</b> Продавец предоставляет доступ к платным функциям бота на условиях подписки. "
    "Оплата подписки означает полное принятие настоящей оферты.\n\n"
    "<b>2. Тарифы.</b> Базовый — 199 ₽ / 150 ⭐ за 30 дней; PRO — 299 ₽ / 200 ⭐ за 30 дней. "
    "Оплата разовая за период; автопродление не производится.\n\n"
    "<b>3. Активация.</b> Доступ открывается сразу после поступления оплаты. "
    "Подписка действует 30 дней с момента активации.\n\n"
    "<b>4. Возврат.</b> Поскольку доступ к цифровым функциям предоставляется немедленно, "
    "возврат возможен только при технической невозможности оказания услуги. "
    "Запрос на возврат — через поддержку.\n\n"
    "<b>5. Важно.</b> Бот носит справочный характер и <b>не заменяет очную консультацию ветеринара</b>. "
    "При острых симптомах немедленно обратитесь в ветклинику.\n\n"
    f"<b>6. Поддержка:</b> {SUPPORT_CONTACT}\n"
    "Принимая оферту, вы соглашаетесь с Политикой конфиденциальности (/privacy)."
)

PRIVACY_TEXT = (
    "🔒 <b>Политика конфиденциальности</b> (152-ФЗ)\n\n"
    f"Оператор: {SELLER_NAME}, ИНН {SELLER_INN}.\n\n"
    "<b>1. Какие данные.</b> Telegram ID и имя; данные о питомцах, которые вы вводите "
    "(кличка, вид, вес, медзаписи); город (для погоды); история оплат.\n\n"
    "<b>2. Зачем.</b> Для работы функций бота: карточка питомца, напоминания, AI-подсказки, "
    "подписки. Без этих данных сервис не работает.\n\n"
    "<b>3. AI-обработка.</b> Текст/фото для AI-функций передаются провайдеру OpenRouter "
    "для генерации ответа. Не используйте бота для передачи чужих персональных данных.\n\n"
    "<b>4. Хранение.</b> Данные хранятся на сервере оператора в РФ, пока вы пользуетесь ботом.\n\n"
    "<b>5. Передача третьим лицам.</b> Не передаём и не продаём, кроме платёжных систем "
    "(YooKassa / Telegram) для проведения оплаты и AI-провайдера для генерации ответов.\n\n"
    "<b>6. Ваши права.</b> Вы можете удалить все свои данные командой /delete_me. "
    f"Вопросы по данным: {SUPPORT_CONTACT}, {SUPPORT_EMAIL}."
)


@router.message(Command("terms"))
async def cmd_terms(message: Message) -> None:
    await message.answer(OFFER_TEXT, parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("privacy"))
async def cmd_privacy(message: Message) -> None:
    await message.answer(PRIVACY_TEXT, parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("support"))
async def cmd_support(message: Message) -> None:
    await message.answer(
        "🛟 <b>Поддержка</b>\n\n"
        f"Telegram: {SUPPORT_CONTACT}\n"
        f"Email: {SUPPORT_EMAIL}\n\n"
        "Опишите проблему — ответим как можно скорее.\n\n"
        "📄 Оферта — /terms · 🔒 Политика — /privacy",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.message(Command("delete_me"))
async def cmd_delete_me(message: Message) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Да, удалить все мои данные", callback_data="legal:delete_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="legal:delete_cancel")],
        ]
    )
    await message.answer(
        "🗑 <b>Удаление данных</b>\n\n"
        "Будут <b>безвозвратно</b> удалены: все питомцы и их записи, напоминания, "
        "история, настройки и подписка.\n\n"
        "Действие необратимо. Подтвердить?",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "legal:delete_cancel")
async def cb_delete_cancel(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Отменено. Ваши данные на месте.")
    await callback.answer()


@router.callback_query(F.data == "legal:delete_confirm")
async def cb_delete_confirm(callback: CallbackQuery) -> None:
    try:
        deleted = await api_client.delete_user_data(callback.from_user.id)
        logger.info("Пользователь %s удалил свои данные: %s", callback.from_user.id, deleted)
        await callback.message.edit_text("✅ Все ваши данные удалены.\n\nЧтобы начать заново — отправьте /start.")
    except Exception as e:  # noqa: BLE001
        logger.error("Ошибка удаления данных пользователя %s: %s", callback.from_user.id, e)
        await callback.message.edit_text("😕 Не удалось удалить данные. Напишите в поддержку: /support")
    await callback.answer()
