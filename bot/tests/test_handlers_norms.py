"""Tests for bot.handlers.norms — food/water norms handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.handlers.norms import cb_food_norms


def _cb(data: str = "food:norms") -> MagicMock:
    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock(id=1)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


@pytest.mark.asyncio
@patch("bot.handlers.norms.api_client")
async def test_cb_food_norms_no_pets(mock_api: MagicMock):
    mock_api.get_norms = AsyncMock(return_value={"no_pets": True})
    cb = _cb()
    await cb_food_norms(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.norms.api_client")
async def test_cb_food_norms_with_data(mock_api: MagicMock):
    mock_api.get_norms = AsyncMock(return_value={"text": "Norma: 200g"})
    cb = _cb()
    await cb_food_norms(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.norms.api_client")
async def test_cb_food_norms_error(mock_api: MagicMock):
    mock_api.get_norms = AsyncMock(side_effect=RuntimeError("fail"))
    cb = _cb()
    await cb_food_norms(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()
