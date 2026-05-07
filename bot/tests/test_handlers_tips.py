"""Tests for bot.handlers.tips — tips/FAQ handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from bot.handlers.tips import cb_tips, cb_tips_menu, tips_menu


def _msg(text: str = "💡 Советы") -> MagicMock:
    m = MagicMock()
    m.text = text
    m.from_user = MagicMock(id=1)
    m.answer = AsyncMock()
    return m


def _cb(data: str = "tips:menu") -> MagicMock:
    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock(id=1)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


@pytest.mark.asyncio
async def test_tips_menu():
    msg = _msg()
    await tips_menu(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_tips_menu():
    cb = _cb()
    await cb_tips_menu(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
async def test_cb_tips_faq():
    cb = _cb(data="tips:faq")
    await cb_tips(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
async def test_cb_tips_nutrition():
    cb = _cb(data="tips:nutrition")
    await cb_tips(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_tips_unknown():
    cb = _cb(data="tips:unknown_topic")
    await cb_tips(cb)
    cb.message.edit_text.assert_awaited_once()
