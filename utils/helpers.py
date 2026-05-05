"""Вспомогательные функции: валидация, форматирование."""

import re
from datetime import date, datetime

__all__ = [
    "parse_date",
    "parse_weight",
    "parse_time",
    "parse_amount",
    "format_date",
    "format_datetime",
    "callback_part",
    "callback_int",
]


def parse_date(text: str) -> date | None:
    """Парсит дату из строки. Поддерживает ДД.ММ.ГГГГ и ДД/ММ/ГГГГ."""
    text = text.strip()
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_weight(text: str) -> float | None:
    """Парсит вес. Допускает точку и запятую как разделитель."""
    text = text.strip().replace(",", ".")
    # Убираем единицы измерения
    text = re.sub(r"\s*(кг|kg|г|g)\s*$", "", text, flags=re.IGNORECASE)
    try:
        value = float(text)
        if 0 < value < 1000:
            return value
        return None
    except ValueError:
        return None


def parse_time(text: str) -> tuple[int, int] | None:
    """Парсит время из строки. Поддерживает ЧЧ:ММ."""
    text = text.strip()
    match = re.match(r"^(\d{1,2})[:\.](\d{2})$", text)
    if match:
        h, m = int(match.group(1)), int(match.group(2))
        if 0 <= h <= 23 and 0 <= m <= 59:
            return (h, m)
    return None


def parse_amount(text: str) -> int | None:
    """Парсит количество мл воды."""
    text = text.strip()
    text = re.sub(r"\s*(мл|ml)\s*$", "", text, flags=re.IGNORECASE)
    try:
        value = int(text)
        if 0 < value < 10000:
            return value
        return None
    except ValueError:
        return None


def format_date(d: date | None) -> str:
    """Форматирует дату в ДД.ММ.ГГГГ."""
    if d is None:
        return "—"
    return d.strftime("%d.%m.%Y")


def format_datetime(dt: datetime | None) -> str:
    """Форматирует дату-время."""
    if dt is None:
        return "—"
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
