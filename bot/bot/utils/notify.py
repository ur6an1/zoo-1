"""Уведомление администраторов (ADMIN_IDS) с анти-спам троттлингом."""

from __future__ import annotations

import logging
import time

from aiogram import Bot
from zoo_shared.config import get_settings

logger = logging.getLogger(__name__)

_last_sent: dict[str, float] = {}


async def notify_admins(bot: Bot, text: str, key: str = "", min_interval: float = 60.0) -> None:
    """Шлёт текст всем ADMIN_IDS.

    key + min_interval — троттлинг повторов: одинаковые алёрты не чаще раза
    в min_interval секунд (чтобы поток ошибок не зафлудил админа).
    """
    admins = get_settings().ADMIN_IDS
    if not admins:
        return
    if key:
        now = time.monotonic()
        if now - _last_sent.get(key, 0.0) < min_interval:
            return
        _last_sent[key] = now
    for admin_id in admins:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as e:  # noqa: BLE001 — алёрт не должен ронять основной сценарий
            logger.debug("notify_admins: не доставлено %s: %s", admin_id, e)
