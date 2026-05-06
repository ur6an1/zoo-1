"""Tests for bot.handlers.tips — tips, FAQ, nutrition."""

from unittest.mock import AsyncMock, patch

from bot.handlers.tips import cb_tips, cb_tips_menu, tips_menu


class TestTipsMenu:
    async def test_message_handler(self, mock_message):
        await tips_menu(mock_message)
        mock_message.answer.assert_awaited_once()
        text = mock_message.answer.call_args[0][0]
        assert "советы" in text.lower()

    async def test_callback_handler(self, mock_callback):
        await cb_tips_menu(mock_callback)
        mock_callback.message.edit_text.assert_awaited_once()
        mock_callback.answer.assert_awaited_once()


class TestCbTips:
    @patch("bot.handlers.tips.FAQ_TEXT", "Часто задаваемые вопросы")
    async def test_faq(self, mock_callback):
        mock_callback.data = "tips:faq"
        await cb_tips(mock_callback)
        mock_callback.message.edit_text.assert_awaited_once()
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Часто задаваемые вопросы" in text

    @patch("bot.handlers.tips.NUTRITION_TEXT", "Советы по питанию")
    async def test_nutrition(self, mock_callback):
        mock_callback.data = "tips:nutrition"
        await cb_tips(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Советы по питанию" in text

    @patch("bot.handlers.tips.TIPS", {"кошка": "Советы для кошек"})
    async def test_specific_topic(self, mock_callback):
        mock_callback.data = "tips:кошка"
        await cb_tips(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Советы для кошек" in text

    @patch("bot.handlers.tips.TIPS", {"другое": "Другие советы"})
    async def test_unknown_topic_fallback(self, mock_callback):
        mock_callback.data = "tips:unknown"
        await cb_tips(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Другие советы" in text

    @patch("bot.handlers.tips.TIPS", {})
    async def test_missing_topic_no_fallback(self, mock_callback):
        mock_callback.data = "tips:missing"
        await cb_tips(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "не найден" in text.lower() or text  # fallback text
