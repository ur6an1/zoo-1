"""Обработчики оплаты: ЮKassa + Telegram Stars."""

import logging

from aiogram import Bot, F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from zoo_shared.config import get_settings

from bot import api_client
from bot.keyboards.keyboards import main_menu_kb
from bot.utils.helpers import callback_part

logger = logging.getLogger(__name__)
router = Router(name="payment")

PLANS = {
    "basic": {
        "name": "🐾 Базовый",
        "price": 199,
        "days": 30,
        "stars": 150,
        "tier": "basic",
    },
    "pro": {
        "name": "⭐ PRO",
        "price": 299,
        "days": 30,
        "stars": 200,
        "tier": "pro",
    },
}


def _normalize_money_value(value: str | int | float | None) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value).strip()


def _payment_methods_note(card_available: bool) -> str:
    if card_available:
        return (
            "Можно оплатить картой или Telegram Stars.\n"
            "Доступ активируется автоматически после подтверждения оплаты."
        )
    return (
        "Оплата сейчас доступна только через Telegram Stars.\n"
        "Банковская карта временно отключена, чтобы не вести в нерабочий сценарий."
    )


async def _send_card_success_message(bot: Bot, user_id: int, plan_name: str, until: str) -> None:
    await bot.send_message(
        chat_id=user_id,
        text=(
            f"✅ Подписка <b>{plan_name}</b> активирована!\n"
            f"Действует до {until}.\n\n"
            "Главное меню ниже."
        ),
        parse_mode="HTML",
        reply_markup=main_menu_kb,
    )


async def _reconcile_card_payment(
    payment_id: str,
    *,
    bot: Bot | None = None,
    expected_user_id: int | None = None,
    expected_plan_key: str | None = None,
    notify_user: bool = False,
) -> tuple[str, str]:
    plan = PLANS.get(expected_plan_key) if expected_plan_key else None
    expected_amount = _normalize_money_value(plan["price"]) if plan else None

    try:
        result = await api_client.reconcile_yookassa_payment(
            payment_id=payment_id,
            expected_user_id=expected_user_id,
            expected_plan_key=expected_plan_key,
            expected_amount=str(expected_amount) if expected_amount else None,
        )
    except Exception as e:
        logger.exception("Backend reconcile error: %s", e)
        if expected_user_id is not None:
            await api_client.track_event(
                expected_user_id, "payment_failed",
                source="yookassa_check",
                payload={"payment_id": payment_id, "reason": "provider_check_error"},
            )
        return "error", "Не удалось проверить оплату. Попробуйте позже."

    if not result.get("ok"):
        error = result.get("error", "unknown")
        await api_client.update_pending_payment(
            "yookassa", payment_id, status="error", last_error=error,
        )
        if expected_user_id is not None:
            await api_client.track_event(
                expected_user_id, "payment_failed",
                source="yookassa",
                payload={"payment_id": payment_id, "reason": error},
            )
        error_messages = {
            "metadata_missing": "Не удалось подтвердить параметры платежа. Обратитесь в поддержку.",
            "user_mismatch": "Этот платёж привязан к другому пользователю.",
            "plan_mismatch": "Этот платёж привязан к другому тарифу.",
            "amount_mismatch": "Сумма или валюта платежа не совпали с тарифом.",
        }
        return "error", error_messages.get(error, "Не удалось проверить оплату. Попробуйте позже.")

    payment_status = result.get("status", "pending")
    if payment_status != "succeeded":
        await api_client.update_pending_payment(
            "yookassa", payment_id,
            status=payment_status,
            completed=payment_status == "canceled",
        )
        if payment_status == "canceled":
            if expected_user_id is not None:
                await api_client.track_event(
                    expected_user_id, "payment_canceled",
                    source="yookassa",
                    payload={"payment_id": payment_id},
                )
            return "canceled", "Платёж отменён."
        return "pending", "Оплата ещё не поступила. Попробуйте снова через несколько секунд."

    meta_user_id = result.get("metadata_user_id", "")
    meta_plan_key = result.get("metadata_plan_key", "")
    plan = PLANS.get(meta_plan_key)
    if not plan:
        await api_client.update_pending_payment(
            "yookassa", payment_id, status="error", last_error="unknown_plan",
        )
        if expected_user_id is not None:
            await api_client.track_event(
                expected_user_id, "payment_failed",
                source="yookassa",
                payload={"payment_id": payment_id, "reason": "unknown_plan"},
            )
        return "error", "Неизвестный тариф платежа."

    user_id = int(meta_user_id)
    mark_result = await api_client.mark_payment_processed(
        provider="yookassa",
        payment_id=payment_id,
        user_id=user_id,
        plan_key=meta_plan_key,
    )
    if not mark_result.get("success"):
        await api_client.update_pending_payment(
            "yookassa", payment_id, status="succeeded", completed=True,
        )
        sub = await api_client.get_subscription_status(user_id)
        until = sub.get("premium_until_str", "бессрочно")
        return "already_processed", until

    await api_client.grant_premium(user_id, days=plan["days"], plan_tier=plan["tier"])
    await api_client.update_pending_payment(
        "yookassa", payment_id, status="succeeded", completed=True,
    )
    await api_client.track_event(
        user_id, "payment_succeeded",
        source="yookassa",
        payload={"plan_key": meta_plan_key, "payment_id": payment_id},
    )

    sub = await api_client.get_subscription_status(user_id)
    until = sub.get("premium_until_str", "бессрочно")

    if bot and notify_user:
        try:
            await _send_card_success_message(bot, user_id, plan["name"], until)
        except Exception as e:
            logger.warning("Не удалось отправить авто-подтверждение оплаты %s: %s", payment_id, e)

    return "succeeded", until


async def reconcile_pending_card_payments(bot: Bot) -> None:
    """Фоновая проверка созданных платежей YooKassa."""
    card_ok = await api_client.is_card_payment_operational()
    if not card_ok:
        logger.info("Пропуск reconcile_pending_card_payments: YooKassa недоступна")
        return

    pending_payments = await api_client.list_pending_payments("yookassa")

    processed = 0
    for pending in pending_payments:
        status, _details = await _reconcile_card_payment(
            pending["payment_id"],
            bot=bot,
            expected_user_id=pending.get("user_id"),
            expected_plan_key=pending.get("plan_key"),
            notify_user=True,
        )
        if status in {"succeeded", "already_processed", "canceled"}:
            processed += 1

    if pending_payments:
        logger.info(
            "Фоновая сверка YooKassa: проверено %s, завершено %s",
            len(pending_payments), processed,
        )


def payment_plans_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🐾 Базовый — 199 ₽ / 30 дней", callback_data="zoo_sub:basic")],
            [InlineKeyboardButton(text="⭐ PRO — 299 ₽ / 30 дней", callback_data="zoo_sub:pro")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
        ]
    )


def payment_methods_kb(plan_key: str, card_available: bool) -> InlineKeyboardMarkup:
    rows = []
    if card_available:
        rows.append([InlineKeyboardButton(text="💳 Банковская карта", callback_data=f"zoo_pay_card:{plan_key}")])

    rows.extend(
        [
            [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"zoo_pay_stars:{plan_key}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="zoo_back_plans")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "settings:subscription")
async def show_plans_cb(callback: CallbackQuery):
    sub = await api_client.get_subscription_status(callback.from_user.id)
    ai_available = await api_client.is_ai_operational()
    await api_client.track_event(callback.from_user.id, "paywall_view", source="settings")

    sub_info = sub.get("formatted_info", "")
    ai_basic_line = "• Безлимит AI-запросов" if ai_available else "• AI-функции (временно недоступны)"
    ai_pro_line = "• Безлимит AI + питомцев" if ai_available else "• AI-функции (временно недоступны)"
    maintenance_note = (
        "\n\n⚠️ <b>Важно:</b> сейчас AI-провайдеры недоступны. "
        "Подписка активируется штатно, AI заработает после восстановления."
        if not ai_available
        else ""
    )

    text = (
        f"{sub_info}\n\n"
        "📋 <b>Сравнение тарифов</b>\n\n"
        "🐾 <b>Базовый — 199 ₽ за 30 дней</b>\n"
        f"{ai_basic_line}\n"
        "• До 5 питомцев\n"
        "• Без автопродления\n\n"
        "⭐ <b>PRO — 299 ₽ за 30 дней</b>\n"
        f"{ai_pro_line}\n"
        "• PDF-экспорт\n"
        "• Погодные уведомления\n"
        "• Голосовые заметки\n"
        "• Без автопродления"
        f"{maintenance_note}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=payment_plans_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "zoo_back_plans")
async def back_to_plans(callback: CallbackQuery):
    await show_plans_cb(callback)


@router.callback_query(F.data.startswith("zoo_sub:"))
async def choose_plan(callback: CallbackQuery):
    plan_key = callback_part(callback.data, 1)
    if not plan_key:
        await callback.answer("Ошибка параметров тарифа", show_alert=True)
        return
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return
    await api_client.track_event(
        callback.from_user.id, "plan_selected",
        source="paywall", payload={"plan_key": plan_key},
    )

    card_available = await api_client.is_card_payment_operational()
    await callback.message.edit_text(
        f"Оплата тарифа <b>{plan['name']}</b> — {plan['price']} ₽ за 30 дней\n\n"
        f"{_payment_methods_note(card_available)}",
        reply_markup=payment_methods_kb(plan_key, card_available=card_available),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "zoo_pay_card_unavailable")
async def card_unavailable(callback: CallbackQuery):
    await callback.answer("Оплата картой временно недоступна. Используйте Telegram Stars.", show_alert=True)


@router.callback_query(F.data.startswith("zoo_pay_card:"))
async def pay_card(callback: CallbackQuery):
    plan_key = callback_part(callback.data, 1)
    if not plan_key:
        await callback.answer("Ошибка параметров тарифа", show_alert=True)
        return
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    card_ok = await api_client.is_card_payment_operational()
    if not card_ok:
        await api_client.track_event(
            callback.from_user.id, "payment_failed",
            source="yookassa",
            payload={"plan_key": plan_key, "reason": "card_unavailable"},
        )
        await callback.answer("Оплата картой временно недоступна. Выберите Stars.", show_alert=True)
        return

    try:
        return_url = get_settings().PAYMENT_RETURN_URL
        if not return_url:
            bot_info = await callback.bot.get_me()
            return_url = f"https://t.me/{bot_info.username}" if bot_info.username else "https://t.me"

        create_result = await api_client.create_yookassa_payment(
            plan_key=plan_key,
            plan_price=plan["price"],
            plan_name=plan["name"],
            user_id=callback.from_user.id,
            return_url=return_url,
            receipt_email=get_settings().RECEIPT_EMAIL,
        )
    except Exception as e:
        logger.exception("Backend create payment error: %s", e)
        await api_client.track_event(
            callback.from_user.id, "payment_failed",
            source="yookassa",
            payload={"plan_key": plan_key, "reason": "create_error"},
        )
        await callback.answer("Не удалось создать платёж. Попробуйте позже.", show_alert=True)
        return

    if not create_result.get("ok"):
        await api_client.track_event(
            callback.from_user.id, "payment_failed",
            source="yookassa",
            payload={"plan_key": plan_key, "reason": "create_error"},
        )
        await callback.answer("Не удалось создать платёж. Попробуйте позже.", show_alert=True)
        return

    pay_url = create_result["confirmation_url"]
    pid = create_result["payment_id"]
    await api_client.upsert_pending_payment(
        provider="yookassa",
        payment_id=pid,
        user_id=callback.from_user.id,
        plan_key=plan_key,
        amount_value=_normalize_money_value(plan["price"]),
        currency="RUB",
    )
    await api_client.track_event(
        callback.from_user.id, "payment_started",
        source="yookassa",
        payload={"plan_key": plan_key, "payment_id": pid},
    )

    await callback.message.edit_text(
        "💳 <b>Оплата картой</b>\n\n"
        f"Тариф: <b>{plan['name']}</b> — {plan['price']} ₽\n\n"
        f"<a href=\"{pay_url}\">➡️ Перейти к оплате</a>\n\n"
        "Обычно подписка активируется автоматически после оплаты.\n"
        "Если этого не произошло сразу, нажмите «Проверить оплату».",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Проверить оплату",
                        callback_data=f"zoo_check_card:{pid}:{plan_key}",
                    )
                ],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="zoo_back_plans")],
            ]
        ),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("zoo_check_card:"))
async def check_card(callback: CallbackQuery):
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer("Ошибка параметров оплаты", show_alert=True)
        return

    pid, plan_key = parts[1], parts[2]
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    card_ok = await api_client.is_card_payment_operational()
    if not card_ok:
        await callback.answer("Проверка оплаты временно недоступна", show_alert=True)
        return

    status, details = await _reconcile_card_payment(
        pid,
        bot=callback.bot,
        expected_user_id=callback.from_user.id,
        expected_plan_key=plan_key,
        notify_user=False,
    )
    if status == "pending":
        await api_client.track_event(
            callback.from_user.id, "payment_pending",
            source="yookassa",
            payload={"plan_key": plan_key, "payment_id": pid},
        )
        await callback.answer(details, show_alert=True)
        return
    if status == "canceled":
        await api_client.track_event(
            callback.from_user.id, "payment_canceled",
            source="yookassa",
            payload={"plan_key": plan_key, "payment_id": pid},
        )
        card_available = await api_client.is_card_payment_operational()
        await callback.message.edit_text(
            "❌ Платёж был отменён. Вы можете выбрать способ оплаты заново.",
            reply_markup=payment_methods_kb(plan_key, card_available=card_available),
        )
        await callback.answer("Платёж отменён", show_alert=True)
        return
    if status == "error":
        await api_client.track_event(
            callback.from_user.id, "payment_failed",
            source="yookassa",
            payload={"plan_key": plan_key, "payment_id": pid},
        )
        await callback.answer(details, show_alert=True)
        return
    if status == "already_processed":
        await callback.message.edit_text(
            f"ℹ️ Этот платёж уже обработан ранее.\nТекущий срок подписки: {details}.",
            parse_mode="HTML",
        )
        await callback.answer("Платёж уже обработан", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ Подписка <b>{plan['name']}</b> активирована!\n"
        f"Действует до {details}.",
        parse_mode="HTML",
    )
    await callback.message.answer("Главное меню 👇", reply_markup=main_menu_kb)
    await callback.answer()


@router.callback_query(F.data.startswith("zoo_pay_stars:"))
async def pay_stars(callback: CallbackQuery, bot: Bot):
    plan_key = callback_part(callback.data, 1)
    if not plan_key:
        await callback.answer("Ошибка параметров тарифа", show_alert=True)
        return
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    payload = f"zoo:{plan_key}:{callback.from_user.id}"
    description = (
        "Zoo Bot: тариф Базовый на 30 дней"
        if plan_key == "basic"
        else "Zoo Bot: тариф PRO на 30 дней"
    )
    try:
        await bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=f"Подписка {plan['name']} — 1 месяц",
            description=description,
            payload=payload,
            currency="XTR",
            prices=[LabeledPrice(label=f"{plan['name']} — 1 мес", amount=plan["stars"])],
            provider_token="",
        )
    except Exception as e:
        logger.exception("Stars invoice error: %s", e)
        await api_client.track_event(
            callback.from_user.id, "payment_failed",
            source="stars",
            payload={"plan_key": plan_key, "reason": "invoice_error"},
        )
        await callback.answer("Не удалось выставить счёт Stars. Попробуйте позже.", show_alert=True)
        return

    await api_client.track_event(
        callback.from_user.id, "payment_started",
        source="stars",
        payload={"plan_key": plan_key},
    )
    await callback.answer("Счёт отправлен")


@router.pre_checkout_query()
async def pre_checkout(pcq: PreCheckoutQuery):
    payload = pcq.invoice_payload or ""
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "zoo":
        await api_client.track_event(
            pcq.from_user.id, "payment_failed", source="stars_pre_checkout", payload={"reason": "bad_payload"}
        )
        await pcq.answer(ok=False, error_message="Неверный платёж.")
        return

    _prefix, plan_key, payload_user_id = parts
    if plan_key not in PLANS:
        await api_client.track_event(
            pcq.from_user.id, "payment_failed", source="stars_pre_checkout", payload={"reason": "bad_plan"}
        )
        await pcq.answer(ok=False, error_message="Неверный тариф.")
        return
    if str(pcq.from_user.id) != payload_user_id:
        await api_client.track_event(
            pcq.from_user.id, "payment_failed", source="stars_pre_checkout", payload={"reason": "user_mismatch"}
        )
        await pcq.answer(ok=False, error_message="Платёж привязан к другому пользователю.")
        return

    await pcq.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    pay = message.successful_payment
    payload = pay.invoice_payload or ""
    if not payload.startswith("zoo:"):
        return

    parts = payload.split(":")
    if len(parts) != 3:
        return

    _, plan_key, payload_user_id = parts
    if str(message.from_user.id) != payload_user_id:
        logger.warning("Payment payload user mismatch: payload=%s actual=%s", payload_user_id, message.from_user.id)
        await api_client.track_event(
            message.from_user.id, "payment_failed",
            source="stars",
            payload={"reason": "payload_user_mismatch"},
        )
        return

    plan = PLANS.get(plan_key)
    if not plan:
        return
    if pay.currency != "XTR" or pay.total_amount != plan["stars"]:
        logger.warning(
            "Stars payment mismatch user=%s expected=%s XTR actual=%s %s",
            message.from_user.id, plan["stars"], pay.total_amount, pay.currency,
        )
        await api_client.track_event(
            message.from_user.id, "payment_failed",
            source="stars",
            payload={"reason": "amount_mismatch"},
        )
        return

    payment_id = pay.telegram_payment_charge_id or pay.provider_payment_charge_id or payload
    result = await api_client.mark_payment_processed(
        provider="stars",
        payment_id=payment_id,
        user_id=message.from_user.id,
        plan_key=plan_key,
    )
    if not result.get("success"):
        logger.info("Duplicate Stars payment ignored: %s", payment_id)
        return

    await api_client.grant_premium(
        message.from_user.id,
        days=plan["days"],
        plan_tier=plan["tier"],
    )
    await api_client.track_event(
        message.from_user.id, "payment_succeeded",
        source="stars",
        payload={"plan_key": plan_key, "payment_id": payment_id},
    )
    sub = await api_client.get_subscription_status(message.from_user.id)
    until = sub.get("premium_until_str", "бессрочно")

    await message.answer(
        f"✅ Подписка <b>{plan['name']}</b> активирована!\n"
        f"Действует до {until}.",
        reply_markup=main_menu_kb,
        parse_mode="HTML",
    )
