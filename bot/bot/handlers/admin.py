"""Админ-панель: статистика, рассылка, пользователи, финансы.

Доступ только для ADMIN_IDS (см. shared.config). Вход — команда /admin.
Backend-агрегации берутся через api_client (/admin/*); выдача/отзыв подписки
переиспользует существующие grant_premium/revoke_premium.
"""

from __future__ import annotations

import asyncio
import html
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from zoo_shared.config import get_settings

from bot import api_client

logger = logging.getLogger(__name__)
router = Router()

USERS_PAGE = 8
BROADCAST_SLEEP = 0.05  # ~20 msg/s, под лимитом Telegram (30/s)
PLAN_PRICES = {"basic": 199, "pro": 299}


class BroadcastStates(StatesGroup):
    waiting_message = State()
    confirm = State()


def _is_admin(user_id: int) -> bool:
    return user_id in get_settings().ADMIN_IDS


def _home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="💰 Финансы", callback_data="admin:finance")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users:0")],
            [InlineKeyboardButton(text="📣 Рассылка", callback_data="admin:bc")],
        ]
    )


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ В меню", callback_data="admin:home")]])


def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    return iso.replace("T", " ")[:16]


# ══════════════ ВХОД ══════════════


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("🛠 <b>Админ-панель</b>\n\nВыберите раздел:", reply_markup=_home_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin:home")
async def cb_home(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_text(
        "🛠 <b>Админ-панель</b>\n\nВыберите раздел:", reply_markup=_home_kb(), parse_mode="HTML"
    )
    await callback.answer()


# ══════════════ СТАТИСТИКА ══════════════


@router.callback_query(F.data == "admin:stats")
async def cb_stats(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    d = await api_client.admin_overview()
    tiers = d.get("by_tier", {})
    species = d.get("by_species", {})
    tiers_str = ", ".join(f"{k}: {v}" for k, v in tiers.items()) or "—"
    species_str = ", ".join(f"{k}: {v}" for k, v in species.items()) or "—"
    text = (
        "📊 <b>Статистика</b>\n\n"
        f"👤 Пользователей: <b>{d.get('users_total', 0)}</b>\n"
        f"⭐ Активных подписок: <b>{d.get('premium_active', 0)}</b>\n"
        f"📦 Тарифы: {tiers_str}\n\n"
        f"🆕 Новые: сегодня {d.get('new_today', 0)} / 7д {d.get('new_7d', 0)} / 30д {d.get('new_30d', 0)}\n"
        f"🔥 Активные: сегодня {d.get('active_today', 0)} / 7д {d.get('active_7d', 0)}\n"
        f"🤖 AI-запросов сегодня: {d.get('ai_requests_today', 0)}\n"
        f"📈 Событий всего: {d.get('events_total', 0)}\n\n"
        f"🐾 Питомцев: <b>{d.get('pets_total', 0)}</b> ({species_str})"
    )
    await callback.message.edit_text(text, reply_markup=_back_kb(), parse_mode="HTML")
    await callback.answer()


# ══════════════ ФИНАНСЫ ══════════════


@router.callback_query(F.data == "admin:finance")
async def cb_finance(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    d = await api_client.admin_finance()
    cur = d.get("currency", "RUB")
    by_plan = d.get("by_plan", {})
    by_status = d.get("by_status", {})
    plan_lines = (
        "\n".join(f"  • {k}: {v.get('count', 0)} шт / {v.get('amount', 0):.0f} {cur}" for k, v in by_plan.items())
        or "  —"
    )
    status_lines = ", ".join(f"{k}: {v}" for k, v in by_status.items()) or "—"
    recent = d.get("recent", [])
    recent_lines = (
        "\n".join(
            f"  • <code>{r['user_id']}</code> {r['plan_key']} "
            f"{r['amount']} {r['currency']} ({_fmt_dt(r['created_at'])})"
            for r in recent
        )
        or "  —"
    )
    text = (
        "💰 <b>Финансы</b>\n\n"
        f"💵 Выручка всего: <b>{d.get('revenue_total', 0):.0f} {cur}</b>\n"
        f"📅 За 30 дней: <b>{d.get('revenue_30d', 0):.0f} {cur}</b>\n"
        f"✅ Успешных оплат: {d.get('paid_count', 0)} (плательщиков: {d.get('paying_users', 0)})\n\n"
        f"📦 По тарифам:\n{plan_lines}\n\n"
        f"📊 По статусам: {status_lines}\n\n"
        f"🧾 Последние оплаты:\n{recent_lines}"
    )
    await callback.message.edit_text(text, reply_markup=_back_kb(), parse_mode="HTML")
    await callback.answer()


# ══════════════ ПОЛЬЗОВАТЕЛИ ══════════════


@router.callback_query(F.data.startswith("admin:users:"))
async def cb_users(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    offset = int(callback.data.split(":")[2])
    data = await api_client.admin_users(limit=USERS_PAGE, offset=offset)
    items = data.get("items", [])
    total = data.get("total", 0)

    lines = [f"👥 <b>Пользователи</b> — всего {total}\n"]
    rows: list[list[InlineKeyboardButton]] = []
    for u in items:
        badge = "⭐" if u["is_premium"] else "▫️"
        lines.append(f"{badge} <code>{u['user_id']}</code> — {u['plan_tier']}, 🐾{u['pets']}")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{badge} {u['user_id']} ({u['plan_tier']})", callback_data=f"admin:user:{u['user_id']}"
                )
            ]
        )

    nav: list[InlineKeyboardButton] = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin:users:{max(0, offset - USERS_PAGE)}"))
    if offset + USERS_PAGE < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin:users:{offset + USERS_PAGE}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="◀️ В меню", callback_data="admin:home")])

    if not items:
        lines.append("Пусто.")
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML"
    )
    await callback.answer()


async def _render_user_detail(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    d = await api_client.admin_user_detail(user_id)
    if d is None:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ К списку", callback_data="admin:users:0")]]
        )
        return ("Пользователь не найден.", kb)

    premium = "✅" if d["is_premium"] else "❌"
    text = (
        f"👤 <b>Пользователь</b> <code>{d['user_id']}</code>\n\n"
        f"📦 Тариф: <b>{d['plan_tier']}</b>\n"
        f"⭐ Премиум: {premium} (до {_fmt_dt(d.get('premium_until'))})\n"
        f"🐾 Питомцев: {d['pets']}\n"
        f"🤖 AI сегодня: {d['ai_requests_today']}\n"
        f"💳 Оплат: {d['payments']}\n"
        f"📈 Событий: {d['events']}\n"
        f"👀 Последняя активность: {_fmt_dt(d.get('last_seen'))}\n"
        f"📅 Регистрация: {_fmt_dt(d.get('created_at'))}\n"
        f"🏙 Город: {html.escape(d.get('city') or '—')}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Выдать PRO (365 дн)", callback_data=f"admin:grant:{user_id}")],
            [InlineKeyboardButton(text="🚫 Отозвать подписку", callback_data=f"admin:revoke:{user_id}")],
            [InlineKeyboardButton(text="◀️ К списку", callback_data="admin:users:0")],
        ]
    )
    return (text, kb)


@router.callback_query(F.data.startswith("admin:user:"))
async def cb_user_detail(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    user_id = int(callback.data.split(":")[2])
    text, kb = await _render_user_detail(user_id)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:grant:"))
async def cb_grant(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    user_id = int(callback.data.split(":")[2])
    ok = await api_client.grant_premium(user_id, days=365, plan_tier="pro")
    await callback.answer("✅ PRO выдан на 365 дней" if ok else "😕 Не удалось", show_alert=True)
    text, kb = await _render_user_detail(user_id)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:revoke:"))
async def cb_revoke(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    user_id = int(callback.data.split(":")[2])
    ok = await api_client.revoke_premium(user_id)
    await callback.answer("✅ Подписка отозвана" if ok else "😕 Не удалось", show_alert=True)
    text, kb = await _render_user_detail(user_id)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


# ══════════════ РАССЫЛКА ══════════════


@router.callback_query(F.data == "admin:bc")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.set_state(BroadcastStates.waiting_message)
    await callback.message.edit_text(
        "📣 <b>Рассылка</b>\n\nПришли сообщение (с форматированием), которое разошлём всем пользователям.\n"
        "Для отмены — /cancel.",
        reply_markup=_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(BroadcastStates.waiting_message, Command("cancel"))
async def broadcast_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Рассылка отменена.", reply_markup=_home_kb())


@router.message(BroadcastStates.waiting_message, F.text | F.caption)
async def broadcast_preview(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    body = message.html_text if message.text else (message.caption or "")
    if not body.strip():
        await message.answer("Пустое сообщение — пришли текст. /cancel для отмены.")
        return
    targets = await api_client.admin_broadcast_targets()
    await state.update_data(bc_text=body)
    await state.set_state(BroadcastStates.confirm)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Отправить ({len(targets)})", callback_data="admin:bc_send")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:home")],
        ]
    )
    await message.answer(
        f"📣 <b>Предпросмотр</b> — получателей {len(targets)}:\n\n{body}", reply_markup=kb, parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:bc_send")
async def cb_broadcast_send(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    data = await state.get_data()
    body = data.get("bc_text", "")
    await state.clear()
    if not body:
        await callback.answer("Нет текста для рассылки", show_alert=True)
        return

    targets = await api_client.admin_broadcast_targets()
    await callback.message.edit_text(f"📣 Отправка на {len(targets)} получателей…", parse_mode="HTML")
    await callback.answer()

    sent = 0
    failed = 0
    for uid in targets:
        try:
            await callback.bot.send_message(uid, body, parse_mode="HTML")
            sent += 1
        except Exception as e:  # заблокировал бота / удалён / flood — не валим рассылку
            failed += 1
            logger.info("Broadcast: не доставлено %s: %s", uid, e)
        await asyncio.sleep(BROADCAST_SLEEP)

    await callback.message.answer(
        f"✅ <b>Рассылка завершена</b>\n\nДоставлено: {sent}\nНе доставлено: {failed}",
        reply_markup=_home_kb(),
        parse_mode="HTML",
    )
