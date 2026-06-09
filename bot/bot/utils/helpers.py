"""Вспомогательные функции: валидация, форматирование."""

import re
from datetime import date, datetime
from html import escape

__all__ = [
    "parse_date",
    "parse_weight",
    "parse_time",
    "parse_amount",
    "message_text",
    "format_ai_result",
    "format_date",
    "format_datetime",
    "callback_part",
    "callback_int",
]

TELEGRAM_TEXT_LIMIT = 4096
SAFE_EDIT_TEXT_LIMIT = 4000


def message_text(text: str | None) -> str:
    """Возвращает очищенный текст сообщения или пустую строку для нетекстового update."""
    return (text or "").strip()


def format_ai_result(title: str, result: str, *, footer: str = "", limit: int = SAFE_EDIT_TEXT_LIMIT) -> str:
    """Безопасно форматирует AI-ответ под HTML parse mode и лимит Telegram.

    Важно резать уже escaped-текст: после HTML escaping строка может стать длиннее исходной.
    """
    safe_result = escape(result or "")
    prefix = f"{title}\n\n"
    suffix = f"\n\n{footer}" if footer else ""
    room = max(0, limit - len(prefix) - len(suffix))
    if len(safe_result) > room:
        safe_result = safe_result[: max(0, room - 3)].rstrip() + "..."
    return f"{prefix}{safe_result}{suffix}"


def parse_date(text: str | None) -> date | None:
    """Парсит дату из строки. Поддерживает ДД.ММ.ГГГГ и ДД/ММ/ГГГГ."""
    text = message_text(text)
    if not text:
        return None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_weight(text: str | None) -> float | None:
    """Парсит вес. Допускает точку и запятую как разделитель."""
    text = message_text(text).replace(",", ".")
    if not text:
        return None
    # Убираем единицы измерения
    text = re.sub(r"\s*(кг|kg|г|g)\s*$", "", text, flags=re.IGNORECASE)
    try:
        value = float(text)
        if 0 < value < 1000:
            return value
        return None
    except ValueError:
        return None


def parse_time(text: str | None) -> tuple[int, int] | None:
    """Парсит время из строки. Поддерживает ЧЧ:ММ."""
    text = message_text(text)
    if not text:
        return None
    match = re.match(r"^(\d{1,2})[:\.](\d{2})$", text)
    if match:
        h, m = int(match.group(1)), int(match.group(2))
        if 0 <= h <= 23 and 0 <= m <= 59:
            return (h, m)
    return None


def parse_amount(text: str | None) -> int | None:
    """Парсит количество мл воды."""
    text = message_text(text)
    if not text:
        return None
    text = re.sub(r"\s*(мл|ml)\s*$", "", text, flags=re.IGNORECASE)
    try:
        value = int(text)
        if 0 < value < 10000:
            return value
        return None
    except ValueError:
        return None


def format_date(d: date | str | None) -> str:
    """Форматирует дату в ДД.ММ.ГГГГ. Принимает date, ISO-строку или None."""
    if d is None:
        return "—"
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d)
        except ValueError:
            return d
    return d.strftime("%d.%m.%Y")


def format_datetime(dt: datetime | str | None) -> str:
    """Форматирует дату-время. Принимает datetime, ISO-строку или None."""
    if dt is None or dt == "":
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    return dt.strftime("%d.%m.%Y %H:%M")


def callback_part(data: str | None, index: int) -> str | None:
    """Безопасно возвращает часть callback_data по индексу."""
    if not data:
        return None
    parts = data.split(":")
    if index < 0 or index >= len(parts):
        return None
    value = parts[index].strip()
    return value or None


def callback_int(data: str | None, index: int, *, min_value: int = 1) -> int | None:
    """Безопасно парсит целое число из callback_data."""
    raw = callback_part(data, index)
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    if value < min_value:
        return None
    return value
