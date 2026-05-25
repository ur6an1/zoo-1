"""Tests for worker.tasks.payments — reconciliation placeholder."""

import pytest

from worker.tasks.payments import reconcile_pending_payments


@pytest.mark.asyncio
async def test_reconcile_pending_payments():
    await reconcile_pending_payments()
