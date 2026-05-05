"""Tests for worker.tasks.subscriptions — notification logic."""

import os
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "123456789:ABCDefGhIJKlmnoPQRstuvWXYZ012345678")
os.environ.setdefault("REDIS_URL", "")


class TestSubscriptionExpirationText:
    def test_days_left_3(self):
        days_left = 3
        text = (
            "⏳ <b>Подписка скоро закончится</b>\n\n"
            f"Осталось {days_left} дн. до окончания.\n"
            "Продлите подписку, чтобы не потерять доступ к PRO-функциям."
        )
        assert "3 дн." in text
        assert "Продлите" in text

    def test_days_left_1(self):
        days_left = 1
        text = (
            "⏳ <b>Подписка скоро закончится</b>\n\n"
            f"Осталось {days_left} дн. до окончания.\n"
            "Продлите подписку, чтобы не потерять доступ к PRO-функциям."
        )
        assert "1 дн." in text

    def test_days_left_0(self):
        text = (
            "⏰ <b>Подписка заканчивается сегодня</b>\n\n"
            "Продлите подписку, чтобы сохранить доступ к PRO-функциям."
        )
        assert "сегодня" in text

    def test_expired(self):
        text = (
            "❌ <b>Подписка истекла</b>\n\n"
            "Доступ к PRO-функциям закрыт. Вы можете продлить подписку в настройках."
        )
        assert "истекла" in text


class TestSendSubscriptionNotifications:
    @pytest.mark.asyncio
    async def test_no_users(self):
        """No premium users => no messages sent."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("worker.tasks.subscriptions.async_session", return_value=mock_session),
            patch("worker.tasks.subscriptions.send_message", new_callable=AsyncMock) as mock_send,
        ):
            from worker.tasks.subscriptions import send_subscription_expiration_notifications
            await send_subscription_expiration_notifications()
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_user_3_days_left(self):
        """User with 3 days left gets notified."""
        mock_user = MagicMock()
        mock_user.premium_until = datetime.now() + timedelta(days=3)
        mock_user.user_id = 42

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("worker.tasks.subscriptions.async_session", return_value=mock_session),
            patch("worker.tasks.subscriptions.send_message", new_callable=AsyncMock) as mock_send,
        ):
            from worker.tasks.subscriptions import send_subscription_expiration_notifications
            await send_subscription_expiration_notifications()
            mock_send.assert_called_once()
            call_text = mock_send.call_args[0][1]
            assert "скоро закончится" in call_text

    @pytest.mark.asyncio
    async def test_user_expired(self):
        """User with expired subscription gets notified."""
        mock_user = MagicMock()
        mock_user.premium_until = datetime.now() - timedelta(days=1)
        mock_user.user_id = 42

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("worker.tasks.subscriptions.async_session", return_value=mock_session),
            patch("worker.tasks.subscriptions.send_message", new_callable=AsyncMock) as mock_send,
        ):
            from worker.tasks.subscriptions import send_subscription_expiration_notifications
            await send_subscription_expiration_notifications()
            mock_send.assert_called_once()
            call_text = mock_send.call_args[0][1]
            assert "истекла" in call_text

    @pytest.mark.asyncio
    async def test_user_today(self):
        """User with subscription ending today gets notified."""
        mock_user = MagicMock()
        # Set premium_until to today so days_left == 0
        mock_user.premium_until = MagicMock()
        mock_user.premium_until.date.return_value = date.today()
        mock_user.user_id = 42

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("worker.tasks.subscriptions.async_session", return_value=mock_session),
            patch("worker.tasks.subscriptions.send_message", new_callable=AsyncMock) as mock_send,
        ):
            from worker.tasks.subscriptions import send_subscription_expiration_notifications
            await send_subscription_expiration_notifications()
            mock_send.assert_called_once()
            call_text = mock_send.call_args[0][1]
            assert "сегодня" in call_text

    @pytest.mark.asyncio
    async def test_user_no_premium_until(self):
        """User with premium_until=None => skip."""
        mock_user = MagicMock()
        mock_user.premium_until = None
        mock_user.user_id = 42

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("worker.tasks.subscriptions.async_session", return_value=mock_session),
            patch("worker.tasks.subscriptions.send_message", new_callable=AsyncMock) as mock_send,
        ):
            from worker.tasks.subscriptions import send_subscription_expiration_notifications
            await send_subscription_expiration_notifications()
            mock_send.assert_not_called()
