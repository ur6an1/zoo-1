"""Обработчики оплаты: ЮKassa + Telegram Stars."""

import logging
import uuid
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from yookassa import Configuration
from yookassa import Payment as YooPayment

from config import PAYMENT_RETURN_URL, RECEIPT_EMAIL, YOOKASSA_SECRET_KEY, YOOKASSA_SHOP_ID
from database import async_session
from keyboards.keyboards import main_menu_kb
from models.models import PendingPayment, ProcessedPayment
from services.analytics import track_event
from services.provider_health import is_ai_operational, is_card_payment_operational
from services.subscription import (
    format_subscription_info,
    get_or_create_settings,
    grant_premium,
)
from utils.helpers import callback_part

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


async def _mark_payment_processed(provider: str, payment_id: str, user_id: int, plan_key: str) -> bool:
    """Фиксирует обработанный платёж. Возвращает False при дубле."""
    if not payment_id:
        return False

    async with async_session() as session:
        session.add(
            ProcessedPayment(
                provider=provider,
                payment_id=payment_id,
                user_id=user_id,
                plan_key=plan_key,
            )
        )
        try:
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False


async def _upsert_pending_payment(
    provider: str,
    payment_id: str,
    user_id: int,
    plan_key: str,
    amount_value: str,
    currency: str,
    status: str = "pending",
) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(PendingPayment).where(
                PendingPayment.provider == provider,
                PendingPayment.payment_id == payment_id,
            )
        )
        pending = result.scalar_one_or_none()
        if not pending:
            pending = PendingPayment(
                provider=provider,
                payment_id=payment_id,
                user_id=user_id,
                plan_key=plan_key,
                amount_value=amount_value,
                currency=currency,
            )
            session.add(pending)

        pending.user_id = user_id
        pending.plan_key = plan_key
        pending.amount_value = amount_value
        pending.currency = currency
        pending.status = status
        pending.last_error = ""
        await session.commit()


async def _update_pending_payment(
    provider: str,
    payment_id: str,
    *,
    status: str,
    last_error: str = "",
    completed: bool = False,
) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(PendingPayment).where(
                PendingPayment.provider == provider,
                PendingPayment.payment_id == payment_id,
            )
        )
        pending = result.scalar_one_or_none()
        if not pending:
            return

        pending.status = status
        pending.last_checked_at = datetime.utcnow()
        pending.last_error = last_error[:1000]
        if completed:
            pending.completed_at = datetime.utcnow()
        await session.commit()


async def _get_pending_payment(provider: str, payment_id: str) -> PendingPayment | None:
    async with async_session() as session:
        result = await session.execute(
            select(PendingPayment).where(
                PendingPayment.provider == provider,
                PendingPayment.payment_id == payment_id,
            )
        )
        return result.scalar_one_or_none()


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
    Configuration.account_id = YOOKASSA_SHOP_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY

    try:
        payment = YooPayment.find_one(payment_id)
    except Exception as e:
        logger.exception("YooKassa check payment error: %s", e)
        if expected_user_id is not None:
            await track_event(
                expected_user_id,
                "payment_failed",
                source="yookassa_check",
                payload={"payment_id": payment_id, "reason": "provider_check_error"},
            )
        return "error", "Не удалось проверить оплату. Попробуйте позже."

    payment_status = str(getattr(payment, "status", "") or "").strip()
    if payment_status != "succeeded":
        await _update_pending_payment(
            "yookassa",
            payment_id,
            status=payment_status or "pending",
            completed=payment_status == "canceled",
        )
        if payment_status == "canceled":
            if expected_user_id is not None:
                await track_event(
                    expected_user_id,
                    "payment_canceled",
                    source="yookassa",
                    payload={"payment_id": payment_id},
                )
            return "canceled", "Платёж отменён."
        return "pending", "Оплата ещё не поступила. Попробуйте снова через несколько секунд."

    metadata_raw = getattr(payment, "metadata", {}) or {}
    metadata = metadata_raw if hasattr(metadata_raw, "get") else {}
    meta_user_id = str(metadata.get("user_id", "")).strip()
    meta_plan_key = str(metadata.get("plan_key", "")).strip()

    pending = await _get_pending_payment("yookassa", payment_id)
    if expected_user_id is None and pending:
        expected_user_id = pending.user_id
    if expected_plan_key is None and pending:
        expected_plan_key = pending.plan_key

    if not meta_user_id or not meta_plan_key:
        await _update_pending_payment(
            "yookassa",
            payment_id,
            status="error",
            last_error="metadata_missing",
        )
        logger.warning("YooKassa metadata missing for payment id=%s", payment_id)
        if expected_user_id is not None:
            await track_event(
                expected_user_id,
                "payment_failed",
                source="yookassa",
                payload={"payment_id": payment_id, "reason": "metadata_missing"},
            )
        return "error", "Не удалось подтвердить параметры платежа. Обратитесь в поддержку."

    if expected_user_id is not None and meta_user_id != str(expected_user_id):
        await _update_pending_payment(
            "yookassa",
            payment_id,
            status="error",
            last_error="user_mismatch",
        )
        logger.warning(
            "YooKassa metadata user mismatch: payment=%s expected=%s actual=%s",
            payment_id,
            expected_user_id,
            meta_user_id,
        )
        if expected_user_id is not None:
            await track_event(
                expected_user_id,
                "payment_failed",
                source="yookassa",
                payload={"payment_id": payment_id, "reason": "user_mismatch"},
            )
        return "error", "Этот платёж привязан к другому пользователю."

    if expected_plan_key is not None and meta_plan_key != expected_plan_key:
        await _update_pending_payment(
            "yookassa",
            payment_id,
            status="error",
            last_error="plan_mismatch",
        )
        logger.warning(
            "YooKassa metadata plan mismatch: payment=%s expected=%s actual=%s",
            payment_id,
            expected_plan_key,
            meta_plan_key,
        )
        if expected_user_id is not None:
            await track_event(
                expected_user_id,
                "payment_failed",
                source="yookassa",
                payload={"payment_id": payment_id, "reason": "plan_mismatch"},
            )
        return "error", "Этот платёж привязан к другому тарифу."

    plan = PLANS.get(meta_plan_key)
    if not plan:
        await _update_pending_payment(
            "yookassa",
            payment_id,
            status="error",
            last_error="unknown_plan",
        )
        if expected_user_id is not None:
            await track_event(
                expected_user_id,
                "payment_failed",
                source="yookassa",
                payload={"payment_id": payment_id, "reason": "unknown_plan"},
            )
        return "error", "Неизвестный тариф платежа."

    amount_raw = getattr(getattr(payment, "amount", None), "value", "")
    currency_raw = getattr(getattr(payment, "amount", None), "currency", "")
    amount_value = _normalize_money_value(amount_raw)
    expected_amount = _normalize_money_value(plan["price"])
    currency_value = str(currency_raw or "").strip().upper()
    if amount_value != expected_amount or currency_value != "RUB":
        await _update_pending_payment(
            "yookassa",
            payment_id,
            status="error",
            last_error=f"amount_mismatch:{amount_value}:{currency_value}",
        )
        logger.warning(
            "YooKassa amount mismatch: payment=%s expected=%s RUB actual=%s %s",
            payment_id,
            expected_amount,
            amount_value,
            currency_value,
        )
        if expected_user_id is not None:
            await track_event(
                expected_user_id,
                "payment_failed",
                source="yookassa",
                payload={"payment_id": payment_id, "reason": "amount_mismatch"},
            )
        return "error", "Сумма или валюта платежа не совпали с тарифом."

    user_id = int(meta_user_id)
    marked = await _mark_payment_processed(
        provider="yookassa",
        payment_id=payment_id,
        user_id=user_id,
        plan_key=meta_plan_key,
    )
    if not marked:
        await _update_pending_payment(
            "yookassa",
            payment_id,
            status="succeeded",
            completed=True,
        )
        settings = await get_or_create_settings(user_id)
        until = settings.premium_until.strftime("%d.%m.%Y") if settings.premium_until else "бессрочно"
        return "already_processed", until

    await grant_premium(user_id, days=plan["days"], plan_tier=plan["tier"])
    await _update_pending_payment(
        "yookassa",
        payment_id,
        status="succeeded",
        completed=True,
    )
    await track_event(
        user_id,
        "payment_succeeded",
        source="yookassa",
        payload={"plan_key": meta_plan_key, "payment_id": payment_id},
    )

    settings = await get_or_create_settings(user_id)
    until = settings.premium_until.strftime("%d.%m.%Y") if settings.premium_until else "бессрочно"

    if bot and notify_user:
        try:
            await _send_card_success_message(bot, user_id, plan["name"], until)
        except Exception as e:
            logger.warning("Не удалось отправить авто-подтверждение оплаты %s: %s", payment_id, e)

    return "succeeded", until


async def reconcile_pending_card_payments(bot: Bot) -> None:
    """Фоновая проверка созданных платежей YooKassa."""
    if not await is_card_payment_operational(force=True):
        logger.info("Пропуск reconcile_pending_card_payments: YooKassa недоступна")
        return

    async with async_session() as session:
        result = await session.execute(
            select(PendingPayment)
            .where(
                PendingPayment.provider == "yookassa",
                PendingPayment.status.in_(("pending", "waiting_for_capture")),
            )
            .order_by(PendingPayment.created_at.asc())
            .limit(25)
        )
        pending_payments = result.scalars().all()

    processed = 0
    for pending in pending_payments:
        status, _details = await _reconcile_card_payment(
            pending.payment_id,
            bot=bot,
            expected_user_id=pending.user_id,
            expected_plan_key=pending.plan_key,
            notify_user=True,
        )
        if status in {"succeeded", "already_processed", "canceled"}:
            processed += 1

    if pending_payments:
        logger.info(
            "Фоновая сверка YooKassa: проверено %s, завершено %s",
            len(pending_payments),
            processed,
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
    settings = await get_or_create_settings(callback.from_user.id)
    ai_available = await is_ai_operational()
    await track_event(callback.from_user.id, "paywall_view", source="settings")

    ai_basic_line = "• Безлимит AI-запросов" if ai_available else "• AI-функции (временно недоступны)"
    ai_pro_line = "• Безлимит AI + питомцев" if ai_available else "• AI-функции (временно недоступны)"
    maintenance_note = (
        "\n\n⚠️ <b>Важно:</b> сейчас AI-провайдеры недоступны. "
        "Подписка активируется штатно, AI заработает после восстановления."
        if not ai_available
        else ""
    )

    text = (
        f"{format_subscription_info(settings)}\n\n"
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
    await track_event(callback.from_user.id, "plan_selected", source="paywall", payload={"plan_key": plan_key})

    card_available = await is_card_payment_operational()
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

    if not await is_card_payment_operational(force=True):
        await track_event(
            callback.from_user.id,
            "payment_failed",
            source="yookassa",
            payload={"plan_key": plan_key, "reason": "card_unavailable"},
        )
        await callback.answer("Оплата картой временно недоступна. Выберите Stars.", show_alert=True)
        return

    Configuration.account_id = YOOKASSA_SHOP_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY

    try:
        return_url = PAYMENT_RETURN_URL
        if not return_url:
            bot_info = await callback.bot.get_me()
            return_url = f"https://t.me/{bot_info.username}" if bot_info.username else "https://t.me"

        payment_request = {
            "amount": {"value": f"{plan['price']}.00", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "capture": True,
            "description": f"Zoo Bot — {plan['name']}, 1 месяц",
            "metadata": {
                "user_id": str(callback.from_user.id),
                "plan_key": plan_key,
            },
        }
        if RECEIPT_EMAIL:
            payment_request["receipt"] = {
                "customer": {"email": RECEIPT_EMAIL},
                "items": [
                    {
                        "description": f"Подписка {plan['name']} Zoo Bot",
                        "quantity": "1.00",
                        "amount": {"value": f"{plan['price']}.00", "currency": "RUB"},
                        "vat_code": 1,
                        "payment_subject": "service",
                        "payment_mode": "full_payment",
                    }
                ],
            }

        payment = YooPayment.create(payment_request, uuid.uuid4().hex)
    except Exception as e:
        logger.exception("YooKassa create payment error: %s", e)
        await track_event(
            callback.from_user.id,
            "payment_failed",
            source="yookassa",
            payload={"plan_key": plan_key, "reason": "create_error"},
        )
        await callback.answer("Не удалось создать платёж. Попробуйте позже.", show_alert=True)
        return

    pay_url = payment.confirmation.confirmation_url
    pid = payment.id
    await _upsert_pending_payment(
        provider="yookassa",
        payment_id=pid,
        user_id=callback.from_user.id,
        plan_key=plan_key,
        amount_value=_normalize_money_value(plan["price"]),
        currency="RUB",
    )
    await track_event(
        callback.from_user.id,
        "payment_started",
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

    if not await is_card_payment_operational(force=True):
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
        await track_event(
            callback.from_user.id,
            "payment_pending",
            source="yookassa",
            payload={"plan_key": plan_key, "payment_id": pid},
        )
        await callback.answer(details, show_alert=True)
        return
    if status == "canceled":
        await track_event(
            callback.from_user.id,
            "payment_canceled",
            source="yookassa",
            payload={"plan_key": plan_key, "payment_id": pid},
        )
        card_available = await is_card_payment_operational()
        await callback.message.edit_text(
            "❌ Платёж был отменён. Вы можете выбрать способ оплаты заново.",
            reply_markup=payment_methods_kb(plan_key, card_available=card_available),
        )
        await callback.answer("Платёж отменён", show_alert=True)
        return
    if status == "error":
        await track_event(
            callback.from_user.id,
            "payment_failed",
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
        await track_event(
            callback.from_user.id,
            "payment_failed",
            source="stars",
            payload={"plan_key": plan_key, "reason": "invoice_error"},
        )
        await callback.answer("Не удалось выставить счёт Stars. Попробуйте позже.", show_alert=True)
        return

    await track_event(
        callback.from_user.id,
        "payment_started",
        source="stars",
        payload={"plan_key": plan_key},
    )
    await callback.answer("Счёт отправлен")


@router.pre_checkout_query()
async def pre_checkout(pcq: PreCheckoutQuery):
    payload = pcq.invoice_payload or ""
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "zoo":
        await track_event(
            pcq.from_user.id, "payment_failed", source="stars_pre_checkout", payload={"reason": "bad_payload"}
        )
        await pcq.answer(ok=False, error_message="Неверный платёж.")
        return

    _prefix, plan_key, payload_user_id = parts
    if plan_key not in PLANS:
        await track_event(
            pcq.from_user.id, "payment_failed", source="stars_pre_checkout", payload={"reason": "bad_plan"}
        )
        await pcq.answer(ok=False, error_message="Неверный тариф.")
        return
    if str(pcq.from_user.id) != payload_user_id:
        await track_event(
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
        await track_event(
            message.from_user.id,
            "payment_failed",
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
            message.from_user.id,
            plan["stars"],
            pay.total_amount,
            pay.currency,
        )
        await track_event(
            message.from_user.id,
            "payment_failed",
            source="stars",
            payload={"reason": "amount_mismatch"},
        )
        return

    payment_id = pay.telegram_payment_charge_id or pay.provider_payment_charge_id or payload
    marked = await _mark_payment_processed(
        provider="stars",
        payment_id=payment_id,
        user_id=message.from_user.id,
        plan_key=plan_key,
    )
    if not marked:
        logger.info("Duplicate Stars payment ignored: %s", payment_id)
        return

    await grant_premium(
        message.from_user.id,
        days=plan["days"],
        plan_tier=plan["tier"],
    )
    await track_event(
        message.from_user.id,
        "payment_succeeded",
        source="stars",
        payload={"plan_key": plan_key, "payment_id": payment_id},
    )
    settings = await get_or_create_settings(message.from_user.id)
    until = settings.premium_until.strftime("%d.%m.%Y") if settings.premium_until else "бессрочно"

    await message.answer(
        f"✅ Подписка <b>{plan['name']}</b> активирована!\n"
        f"Действует до {until}.",
        reply_markup=main_menu_kb,
        parse_mode="HTML",
    )
