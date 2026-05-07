"""Tests for bot.handlers.compare — food comparison handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.compare import (
    cb_compare_start,
    compare_not_photo_1,
    compare_not_photo_2,
)


def _msg(text: str = "hello") -> MagicMock:
    m = MagicMock()
    m.text = text
    m.from_user = MagicMock(id=1)
    m.answer = AsyncMock()
    return m


def _cb(data: str = "photo:compare") -> MagicMock:
    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock(id=1)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _state(data: dict | None = None) -> MagicMock:
    s = MagicMock()
    s.clear = AsyncMock()
    s.set_state = AsyncMock()
    s.update_data = AsyncMock()
    s.get_data = AsyncMock(return_value=data or {})
    return s


# ── cb_compare_start ──


@pytest.mark.asyncio
@patch("bot.handlers.compare.api_client")
async def test_cb_compare_start_ai_not_ok(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    cb = _cb()
    state = _state()
    await cb_compare_start(cb, state)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.compare.api_client")
async def test_cb_compare_start_ok(mock_api: MagicMock):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    cb = _cb()
    state = _state()
    await cb_compare_start(cb, state)
    state.set_state.assert_awaited_once()
    cb.message.edit_text.assert_awaited_once()


# ── not-photo handlers ──


@pytest.mark.asyncio
async def test_compare_not_photo_1():
    msg = _msg()
    await compare_not_photo_1(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_compare_not_photo_2():
    msg = _msg()
    await compare_not_photo_2(msg)
    msg.answer.assert_awaited_once()
