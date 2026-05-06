"""Tests for bot.handlers.norms — daily food/water norms display."""

from unittest.mock import AsyncMock, patch

from bot.handlers.norms import cb_food_norms


class TestCbFoodNorms:
    @patch("bot.handlers.norms.api_client")
    async def test_no_pets(self, mock_api, mock_callback):
        mock_api.get_norms = AsyncMock(return_value={"no_pets": True})
        await cb_food_norms(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "нет питомцев" in text
        mock_callback.answer.assert_awaited()

    @patch("bot.handlers.norms.api_client")
    async def test_with_norms(self, mock_api, mock_callback):
        mock_api.get_norms = AsyncMock(return_value={"text": "Нормы: 200г"})
        await cb_food_norms(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Нормы" in text
        mock_callback.answer.assert_awaited()

    @patch("bot.handlers.norms.api_client")
    async def test_no_text(self, mock_api, mock_callback):
        mock_api.get_norms = AsyncMock(return_value={})
        await cb_food_norms(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Нет данных" in text

    @patch("bot.handlers.norms.api_client")
    async def test_error(self, mock_api, mock_callback):
        mock_api.get_norms = AsyncMock(side_effect=Exception("fail"))
        await cb_food_norms(mock_callback)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "ошибка" in text.lower() or "Ошибка" in text or "Попробуйте позже" in text
        mock_callback.answer.assert_awaited()
