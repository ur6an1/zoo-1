"""Tests for bot.handlers.compare — food comparison handlers."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.handlers.compare import (
    cb_compare_start,
    compare_not_photo_1,
    compare_not_photo_2,
    compare_photo_1,
    compare_photo_2,
)


def _msg(text: str = "hello") -> MagicMock:
    m = MagicMock()
    m.text = text
    m.from_user = MagicMock(id=1)
    m.chat = MagicMock(id=1)
    m.answer = AsyncMock()
    photo_obj = MagicMock()
    photo_obj.file_id = "file123"
    m.photo = [photo_obj]
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


def _bot() -> MagicMock:
    bot = MagicMock()
    bot.send_chat_action = AsyncMock()
    file_mock = MagicMock()
    file_mock.file_path = "photos/file.jpg"
    bot.get_file = AsyncMock(return_value=file_mock)
    bot.download_file = AsyncMock(return_value=io.BytesIO(b"fakeimage"))
    return bot


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


# ── compare_photo_1 ──


@pytest.mark.asyncio
async def test_compare_photo_1_ok():
    msg = _msg()
    bot = _bot()
    state = _state()
    await compare_photo_1(msg, state, bot)
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_compare_photo_1_download_error():
    msg = _msg()
    bot = _bot()
    bot.get_file = AsyncMock(side_effect=RuntimeError("err"))
    state = _state()
    await compare_photo_1(msg, state, bot)
    msg.answer.assert_awaited_once()


# ── compare_photo_2 ──


@pytest.mark.asyncio
@patch("bot.handlers.compare.compare_two_foods", new_callable=AsyncMock, return_value="Food A is better")
@patch("bot.handlers.compare.api_client")
async def test_compare_photo_2_ok(mock_api, mock_compare):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state(data={"image_1": b"firstimage"})
    await compare_photo_2(msg, state, bot)
    processing.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_compare_photo_2_download_error():
    msg = _msg()
    bot = _bot()
    bot.get_file = AsyncMock(side_effect=RuntimeError("err"))
    state = _state()
    await compare_photo_2(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.compare.api_client")
async def test_compare_photo_2_no_first_image(mock_api):
    msg = _msg()
    bot = _bot()
    state = _state(data={})
    await compare_photo_2(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.compare.api_client")
async def test_compare_photo_2_ai_not_ok(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=False)
    msg = _msg()
    bot = _bot()
    state = _state(data={"image_1": b"firstimage"})
    await compare_photo_2(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.compare.api_client")
async def test_compare_photo_2_limit(mock_api):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(False, 0))
    msg = _msg()
    bot = _bot()
    state = _state(data={"image_1": b"firstimage"})
    await compare_photo_2(msg, state, bot)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.compare.compare_two_foods", new_callable=AsyncMock, side_effect=RuntimeError("err"))
@patch("bot.handlers.compare.api_client")
async def test_compare_photo_2_compare_error(mock_api, mock_compare):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    mock_api.refund_ai_limit = AsyncMock()
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state(data={"image_1": b"firstimage"})
    await compare_photo_2(msg, state, bot)
    mock_api.refund_ai_limit.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.compare.compare_two_foods", new_callable=AsyncMock, return_value="x" * 5000)
@patch("bot.handlers.compare.api_client")
async def test_compare_photo_2_long_result(mock_api, mock_compare):
    mock_api.is_ai_operational = AsyncMock(return_value=True)
    mock_api.check_ai_limit = AsyncMock(return_value=(True, 5))
    msg = _msg()
    processing = AsyncMock()
    processing.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=processing)
    bot = _bot()
    state = _state(data={"image_1": b"firstimage"})
    await compare_photo_2(msg, state, bot)
    processing.edit_text.assert_awaited_once()
