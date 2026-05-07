"""Tests for bot.handlers.weight_goal — weight goal handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.handlers.weight_goal import (
    cb_weight_goal,
    cb_weight_goal_set,
    weight_goal_target_invalid,
    weight_goal_target_value,
)

PET = {"id": 1, "name": "Rex", "species": "собака",
       "species_emoji": "🐶", "weight": 5.0, "target_weight": 4.5}


def _msg(text: str = "4.5") -> MagicMock:
    m = MagicMock()
    m.text = text
    m.from_user = MagicMock(id=1)
    m.answer = AsyncMock()
    return m


def _cb(data: str = "pet:weight_goal:1") -> MagicMock:
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


# ── cb_weight_goal ──


@pytest.mark.asyncio
@patch("bot.handlers.weight_goal.api_client")
async def test_cb_weight_goal_invalid_id(mock_api: MagicMock):
    cb = _cb(data="pet:weight_goal:bad")
    await cb_weight_goal(cb)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weight_goal.api_client")
async def test_cb_weight_goal_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="pet:weight_goal:1")
    await cb_weight_goal(cb)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weight_goal.api_client")
async def test_cb_weight_goal_ok(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="pet:weight_goal:1")
    await cb_weight_goal(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.weight_goal.api_client")
async def test_cb_weight_goal_reached(mock_api: MagicMock):
    pet = {**PET, "weight": 4.5, "target_weight": 4.5}
    mock_api.get_pet = AsyncMock(return_value=pet)
    cb = _cb(data="pet:weight_goal:1")
    await cb_weight_goal(cb)
    cb.message.edit_text.assert_awaited_once()


# ── cb_weight_goal_set ──


@pytest.mark.asyncio
@patch("bot.handlers.weight_goal.api_client")
async def test_cb_weight_goal_set_invalid_id(mock_api: MagicMock):
    cb = _cb(data="weight_goal:set:bad")
    state = _state()
    await cb_weight_goal_set(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weight_goal.api_client")
async def test_cb_weight_goal_set_not_found(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=None)
    cb = _cb(data="weight_goal:set:1")
    state = _state()
    await cb_weight_goal_set(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weight_goal.api_client")
async def test_cb_weight_goal_set_ok(mock_api: MagicMock):
    mock_api.get_pet = AsyncMock(return_value=PET)
    cb = _cb(data="weight_goal:set:1")
    state = _state()
    await cb_weight_goal_set(cb, state)
    state.set_state.assert_awaited_once()
    state.update_data.assert_awaited_once()
    cb.message.edit_text.assert_awaited_once()


# ── weight_goal_target_value ──


@pytest.mark.asyncio
async def test_weight_goal_target_invalid_value():
    msg = _msg(text="abc")
    state = _state(data={"goal_pet_id": 1})
    await weight_goal_target_value(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weight_goal.api_client")
async def test_weight_goal_target_no_pet_id(mock_api: MagicMock):
    msg = _msg(text="4.5")
    state = _state(data={})
    await weight_goal_target_value(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weight_goal.api_client")
async def test_weight_goal_target_ok(mock_api: MagicMock):
    mock_api.update_pet = AsyncMock(return_value=PET)
    msg = _msg(text="4.5")
    state = _state(data={"goal_pet_id": 1})
    await weight_goal_target_value(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weight_goal.api_client")
async def test_weight_goal_target_pet_not_found(mock_api: MagicMock):
    mock_api.update_pet = AsyncMock(return_value=None)
    msg = _msg(text="4.5")
    state = _state(data={"goal_pet_id": 1})
    await weight_goal_target_value(msg, state)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.weight_goal.api_client")
async def test_weight_goal_target_error(mock_api: MagicMock):
    mock_api.update_pet = AsyncMock(side_effect=RuntimeError("fail"))
    msg = _msg(text="4.5")
    state = _state(data={"goal_pet_id": 1})
    await weight_goal_target_value(msg, state)
    msg.answer.assert_awaited_once()


# ── weight_goal_target_invalid ──


@pytest.mark.asyncio
async def test_weight_goal_target_invalid_handler():
    msg = _msg(text="not a number")
    await weight_goal_target_invalid(msg)
    msg.answer.assert_awaited_once()
