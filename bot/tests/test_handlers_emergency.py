"""Tests for bot.handlers.emergency — SOS/emergency handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.emergency import (
    cb_clinic_radius,
    cb_sos_clinic,
    cb_sos_clinic_rated,
    cb_sos_general,
    cb_sos_injury,
    cb_sos_overheat,
    cb_sos_poisoning,
    emergency_menu,
    emergency_menu_cb,
    handle_location,
    location_expected,
)


def _msg(text: str = "🆘 Экстренная помощь") -> MagicMock:
    m = MagicMock()
    m.text = text
    m.from_user = MagicMock(id=1)
    m.answer = AsyncMock()
    return m


def _cb(data: str = "sos:menu") -> MagicMock:
    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock(id=1)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _state(data: dict | None = None) -> MagicMock:
    s = MagicMock()
    s.clear = AsyncMock()
    s.set_state = AsyncMock()
    s.update_data = AsyncMock()
    s.get_data = AsyncMock(return_value=data or {})
    return s


# ── menu handlers ──


@pytest.mark.asyncio
async def test_emergency_menu():
    msg = _msg()
    await emergency_menu(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_emergency_menu_cb():
    cb = _cb()
    await emergency_menu_cb(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


# ── clinic search ──


@pytest.mark.asyncio
async def test_cb_sos_clinic():
    cb = _cb(data="sos:clinic")
    state = _state()
    await cb_sos_clinic(cb, state)
    state.set_state.assert_awaited_once()
    cb.message.answer.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
async def test_cb_sos_clinic_rated():
    cb = _cb(data="sos:clinic_rated")
    state = _state()
    await cb_sos_clinic_rated(cb, state)
    state.set_state.assert_awaited_once()
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_clinic_radius_invalid():
    cb = _cb(data="clinic:r:bad")
    state = _state()
    await cb_clinic_radius(cb, state)
    cb.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_clinic_radius_valid():
    cb = _cb(data="clinic:r:3000")
    state = _state()
    await cb_clinic_radius(cb, state)
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once()


# ── location handling ──


@pytest.mark.asyncio
@patch("bot.handlers.emergency.search_and_format", new_callable=AsyncMock)
async def test_handle_location(mock_search: AsyncMock):
    mock_search.return_value = "Found 3 clinics"
    msg = _msg()
    msg.location = MagicMock(latitude=55.75, longitude=37.62)
    state = _state(data={"clinic_radius": 5000})
    await handle_location(msg, state)
    msg.answer.assert_awaited()


@pytest.mark.asyncio
async def test_location_expected():
    msg = _msg(text="not a location")
    await location_expected(msg)
    msg.answer.assert_awaited_once()


# ── emergency info callbacks ──


@pytest.mark.asyncio
async def test_cb_sos_poisoning():
    cb = _cb(data="sos:poisoning")
    await cb_sos_poisoning(cb)
    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited()


@pytest.mark.asyncio
async def test_cb_sos_injury():
    cb = _cb(data="sos:injury")
    await cb_sos_injury(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_sos_overheat():
    cb = _cb(data="sos:overheat")
    await cb_sos_overheat(cb)
    cb.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_cb_sos_general():
    cb = _cb(data="sos:general")
    await cb_sos_general(cb)
    cb.message.edit_text.assert_awaited_once()
