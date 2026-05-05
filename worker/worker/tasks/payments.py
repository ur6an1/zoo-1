"""Payment reconciliation — background check for pending card payments."""

import logging

logger = logging.getLogger(__name__)


async def reconcile_pending_payments():
    """Placeholder: фоновая сверка карточных платежей YooKassa.

    Будет полностью реализована в Фазе 2 при разделении payment handler.
    """
    logger.debug("Payment reconciliation check (placeholder)")
