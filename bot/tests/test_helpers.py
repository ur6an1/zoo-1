"""Tests for bot.utils.helpers — date/weight/time parsing, formatting."""

from datetime import date, datetime

from bot.utils.helpers import (
    callback_int,
    callback_part,
    format_date,
    format_datetime,
    parse_amount,
    parse_date,
    parse_time,
    parse_weight,
)


class TestParseDate:
    def test_dd_mm_yyyy_dot(self):
        assert parse_date("15.03.2024") == date(2024, 3, 15)

    def test_dd_mm_yyyy_slash(self):
        assert parse_date("15/03/2024") == date(2024, 3, 15)

    def test_iso(self):
        assert parse_date("2024-03-15") == date(2024, 3, 15)

    def test_invalid(self):
        assert parse_date("not-a-date") is None

    def test_empty(self):
        assert parse_date("") is None

    def test_whitespace(self):
        assert parse_date("  15.03.2024  ") == date(2024, 3, 15)


class TestParseWeight:
    def test_integer(self):
        assert parse_weight("5") == 5.0

    def test_float_dot(self):
        assert parse_weight("5.5") == 5.5

    def test_float_comma(self):
        assert parse_weight("5,5") == 5.5

    def test_with_kg(self):
        assert parse_weight("5.5 кг") == 5.5

    def test_with_kg_latin(self):
        assert parse_weight("5.5kg") == 5.5

    def test_zero(self):
        assert parse_weight("0") is None

    def test_negative(self):
        assert parse_weight("-5") is None

    def test_too_large(self):
        assert parse_weight("1000") is None

    def test_999(self):
        assert parse_weight("999") == 999.0

    def test_invalid(self):
        assert parse_weight("abc") is None

    def test_with_grams(self):
        assert parse_weight("500 г") == 500.0


class TestParseTime:
    def test_hh_mm_colon(self):
        assert parse_time("14:30") == (14, 30)

    def test_hh_mm_dot(self):
        assert parse_time("14.30") == (14, 30)

    def test_single_digit_hour(self):
        assert parse_time("9:05") == (9, 5)

    def test_midnight(self):
        assert parse_time("0:00") == (0, 0)

    def test_23_59(self):
        assert parse_time("23:59") == (23, 59)

    def test_invalid_hour(self):
        assert parse_time("25:00") is None

    def test_invalid_minute(self):
        assert parse_time("12:60") is None

    def test_garbage(self):
        assert parse_time("abc") is None

    def test_whitespace(self):
        assert parse_time("  14:30  ") == (14, 30)


class TestParseAmount:
    def test_integer(self):
        assert parse_amount("250") == 250

    def test_with_ml(self):
        assert parse_amount("250 мл") == 250

    def test_with_ml_latin(self):
        assert parse_amount("250ml") == 250

    def test_zero(self):
        assert parse_amount("0") is None

    def test_too_large(self):
        assert parse_amount("10000") is None

    def test_9999(self):
        assert parse_amount("9999") == 9999

    def test_invalid(self):
        assert parse_amount("abc") is None


class TestFormatDate:
    def test_valid(self):
        assert format_date(date(2024, 3, 15)) == "15.03.2024"

    def test_none(self):
        assert format_date(None) == "—"


class TestFormatDatetime:
    def test_valid(self):
        dt = datetime(2024, 3, 15, 14, 30)
        assert format_datetime(dt) == "15.03.2024 14:30"

    def test_none(self):
        assert format_datetime(None) == "—"


class TestCallbackPart:
    def test_basic(self):
        assert callback_part("action:123:456", 1) == "123"

    def test_first(self):
        assert callback_part("action:123", 0) == "action"

    def test_out_of_range(self):
        assert callback_part("action:123", 5) is None

    def test_negative(self):
        assert callback_part("action", -1) is None

    def test_none_data(self):
        assert callback_part(None, 0) is None

    def test_empty_part(self):
        assert callback_part("action::end", 1) is None


class TestCallbackInt:
    def test_basic(self):
        assert callback_int("pet:42:edit", 1) == 42

    def test_none_data(self):
        assert callback_int(None, 0) is None

    def test_non_numeric(self):
        assert callback_int("action:abc", 1) is None

    def test_below_min(self):
        assert callback_int("action:0", 1, min_value=1) is None

    def test_custom_min(self):
        assert callback_int("action:0", 1, min_value=0) == 0
