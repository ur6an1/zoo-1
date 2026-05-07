"""Tests for worker/worker/tasks/vaccinations.py."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
@patch("worker.tasks.vaccinations.send_message", new_callable=AsyncMock)
@patch("worker.tasks.vaccinations.async_session")
async def test_check_vaccination_schedule_overdue(
    mock_session_maker: MagicMock,
    mock_send: AsyncMock,
):
    from worker.tasks.vaccinations import check_vaccination_schedule

    today = date.today()
    overdue_date = today - timedelta(days=3)

    pet = MagicMock()
    pet.user_id = 42
    pet.name = "Rex"

    vacc = MagicMock()
    vacc.pet_id = 1
    vacc.name = "Rabies"
    vacc.next_date = overdue_date

    session = AsyncMock()
    overdue_result = MagicMock()
    overdue_result.scalars.return_value.all.return_value = [vacc]
    upcoming_result = MagicMock()
    upcoming_result.scalars.return_value.all.return_value = []

    session.execute = AsyncMock(side_effect=[overdue_result, upcoming_result])
    session.get = AsyncMock(return_value=pet)

    mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

    await check_vaccination_schedule()

    mock_send.assert_awaited_once()
    call_args = mock_send.call_args[0]
    assert call_args[0] == 42
    assert "просрочена" in call_args[1]
    assert "Rex" in call_args[1]


@pytest.mark.asyncio
@patch("worker.tasks.vaccinations.send_message", new_callable=AsyncMock)
@patch("worker.tasks.vaccinations.async_session")
async def test_check_vaccination_schedule_upcoming(
    mock_session_maker: MagicMock,
    mock_send: AsyncMock,
):
    from worker.tasks.vaccinations import check_vaccination_schedule

    today = date.today()
    upcoming_date = today + timedelta(days=3)

    pet = MagicMock()
    pet.user_id = 10
    pet.name = "Whiskers"

    vacc = MagicMock()
    vacc.pet_id = 2
    vacc.name = "FeLV"
    vacc.next_date = upcoming_date

    session = AsyncMock()
    overdue_result = MagicMock()
    overdue_result.scalars.return_value.all.return_value = []
    upcoming_result = MagicMock()
    upcoming_result.scalars.return_value.all.return_value = [vacc]

    session.execute = AsyncMock(side_effect=[overdue_result, upcoming_result])
    session.get = AsyncMock(return_value=pet)

    mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

    await check_vaccination_schedule()

    mock_send.assert_awaited_once()
    call_args = mock_send.call_args[0]
    assert call_args[0] == 10
    assert "через 3 дн" in call_args[1]


@pytest.mark.asyncio
@patch("worker.tasks.vaccinations.send_message", new_callable=AsyncMock)
@patch("worker.tasks.vaccinations.async_session")
async def test_check_vaccination_schedule_today(
    mock_session_maker: MagicMock,
    mock_send: AsyncMock,
):
    from worker.tasks.vaccinations import check_vaccination_schedule

    today = date.today()

    pet = MagicMock()
    pet.user_id = 5
    pet.name = "Buddy"

    vacc = MagicMock()
    vacc.pet_id = 3
    vacc.name = "Distemper"
    vacc.next_date = today

    session = AsyncMock()
    overdue_result = MagicMock()
    overdue_result.scalars.return_value.all.return_value = []
    upcoming_result = MagicMock()
    upcoming_result.scalars.return_value.all.return_value = [vacc]

    session.execute = AsyncMock(side_effect=[overdue_result, upcoming_result])
    session.get = AsyncMock(return_value=pet)

    mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

    await check_vaccination_schedule()

    mock_send.assert_awaited_once()
    call_args = mock_send.call_args[0]
    assert "сегодня" in call_args[1]


@pytest.mark.asyncio
@patch("worker.tasks.vaccinations.send_message", new_callable=AsyncMock)
@patch("worker.tasks.vaccinations.async_session")
async def test_check_vaccination_schedule_no_pet(
    mock_session_maker: MagicMock,
    mock_send: AsyncMock,
):
    from worker.tasks.vaccinations import check_vaccination_schedule

    today = date.today()

    vacc = MagicMock()
    vacc.pet_id = 99
    vacc.name = "Test"
    vacc.next_date = today - timedelta(days=1)

    session = AsyncMock()
    overdue_result = MagicMock()
    overdue_result.scalars.return_value.all.return_value = [vacc]
    upcoming_result = MagicMock()
    upcoming_result.scalars.return_value.all.return_value = []

    session.execute = AsyncMock(side_effect=[overdue_result, upcoming_result])
    session.get = AsyncMock(return_value=None)

    mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

    await check_vaccination_schedule()

    mock_send.assert_not_awaited()


@pytest.mark.asyncio
@patch("worker.tasks.vaccinations.send_message", new_callable=AsyncMock)
@patch("worker.tasks.vaccinations.async_session")
async def test_check_vaccination_schedule_no_vaccinations(
    mock_session_maker: MagicMock,
    mock_send: AsyncMock,
):
    from worker.tasks.vaccinations import check_vaccination_schedule

    session = AsyncMock()
    overdue_result = MagicMock()
    overdue_result.scalars.return_value.all.return_value = []
    upcoming_result = MagicMock()
    upcoming_result.scalars.return_value.all.return_value = []

    session.execute = AsyncMock(side_effect=[overdue_result, upcoming_result])

    mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

    await check_vaccination_schedule()

    mock_send.assert_not_awaited()
