"""Tests for bot.handlers.payment — payment utilities and plan constants."""

from bot.handlers.payment import PLANS, _normalize_money_value, _payment_methods_note


class TestNormalizeMoneyValue:
    def test_none(self):
        assert _normalize_money_value(None) == ""

    def test_empty_string(self):
        assert _normalize_money_value("") == ""

    def test_int(self):
        assert _normalize_money_value(199) == "199.00"

    def test_float(self):
        assert _normalize_money_value(199.50) == "199.50"

    def test_string_number(self):
        assert _normalize_money_value("299") == "299.00"

    def test_string_float(self):
        assert _normalize_money_value("199.99") == "199.99"

    def test_invalid_string(self):
        assert _normalize_money_value("abc") == "abc"


class TestPaymentMethodsNote:
    def test_card_available(self):
        text = _payment_methods_note(True)
        assert "картой" in text
        assert "Stars" in text

    def test_card_unavailable(self):
        text = _payment_methods_note(False)
        assert "Stars" in text
        assert "отключена" in text


class TestPlansConfig:
    def test_basic_plan(self):
        assert "basic" in PLANS
        plan = PLANS["basic"]
        assert plan["price"] > 0
        assert plan["days"] > 0
        assert plan["tier"] == "basic"

    def test_pro_plan(self):
        assert "pro" in PLANS
        plan = PLANS["pro"]
        assert plan["price"] > 0
        assert plan["tier"] == "pro"

    def test_pro_more_expensive(self):
        assert PLANS["pro"]["price"] > PLANS["basic"]["price"]
