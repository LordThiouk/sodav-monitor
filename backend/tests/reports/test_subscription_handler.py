"""Tests for the subscription handling module."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from backend.models.models import ReportFormat, ReportSubscription, ReportType, User
from backend.reports.subscription_handler import SubscriptionHandler


@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    session = Mock(spec=Session)
    session.query = Mock(return_value=session)
    session.filter = Mock(return_value=session)
    session.first = Mock(return_value=None)
    return session


@pytest.fixture
def subscription_handler(db_session):
    """Create a SubscriptionHandler instance for testing."""
    return SubscriptionHandler(db_session)


@pytest.mark.asyncio
async def test_create_subscription(subscription_handler, db_session):
    """Test creation of report subscription."""
    subscription_data = {
        "name": "Test Subscription",
        "email": "test@example.com",
        "frequency": ReportType.DAILY,
        "format": ReportFormat.PDF,
        "user_id": 1,
    }

    subscription = await subscription_handler.create_subscription(**subscription_data)

    assert subscription is not None
    assert subscription.name == subscription_data["name"]
    assert subscription.email == subscription_data["email"]
    assert subscription.frequency == subscription_data["frequency"]
    assert subscription.format == subscription_data["format"]
    assert subscription.active is True
    assert isinstance(subscription.next_delivery, datetime)


@pytest.mark.asyncio
async def test_update_subscription(subscription_handler, db_session):
    """Test updating report subscription."""
    mock_subscription = Mock(spec=ReportSubscription)
    db_session.query.return_value.filter.return_value.first.return_value = mock_subscription

    update_data = {"name": "Updated Subscription", "format": ReportFormat.XLSX, "active": False}

    updated = await subscription_handler.update_subscription(1, **update_data)

    assert updated is True
    assert mock_subscription.name == update_data["name"]
    assert mock_subscription.format == update_data["format"]
    assert mock_subscription.active == update_data["active"]


@pytest.mark.asyncio
async def test_process_due_subscriptions(subscription_handler, db_session):
    """Test processing of due subscriptions."""
    # Mock due subscriptions
    mock_subscriptions = [
        Mock(
            id=1,
            name="Sub 1",
            email="test1@example.com",
            frequency=ReportType.DAILY,
            format=ReportFormat.PDF,
            next_delivery=datetime.now() - timedelta(minutes=5),
        ),
        Mock(
            id=2,
            name="Sub 2",
            email="test2@example.com",
            frequency=ReportType.WEEKLY,
            format=ReportFormat.XLSX,
            next_delivery=datetime.now() - timedelta(minutes=10),
        ),
    ]

    db_session.query.return_value.filter.return_value.all.return_value = mock_subscriptions

    with patch.object(subscription_handler, "_generate_and_send_report") as mock_send:
        processed = await subscription_handler.process_due_subscriptions()

        assert processed == 2
        assert mock_send.call_count == 2
        for sub in mock_subscriptions:
            assert isinstance(sub.next_delivery, datetime)
            assert sub.delivery_count == 1


@pytest.mark.asyncio
async def test_send_report(subscription_handler):
    """Test sending report to subscriber."""
    mock_subscription = Mock(email="test@example.com", name="Test User", format=ReportFormat.PDF)

    mock_report = Mock(file_path="test_report.pdf")

    with patch("backend.utils.email.send_email") as mock_send_email:
        success = await subscription_handler._send_report(mock_subscription, mock_report)

        assert success is True
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args[1]
        assert call_args["to_email"] == mock_subscription.email
        assert call_args["subject"].startswith("Your SODAV Monitor Report")
        assert mock_report.file_path in str(call_args["attachments"])


@pytest.mark.asyncio
async def test_error_handling(subscription_handler, db_session):
    """Test error handling in subscription processing."""
    # Test subscription creation error
    db_session.add.side_effect = Exception("Database error")

    with pytest.raises(Exception):
        await subscription_handler.create_subscription(
            name="Test",
            email="test@example.com",
            frequency=ReportType.DAILY,
            format=ReportFormat.PDF,
            user_id=1,
        )

    # Test subscription update error
    mock_subscription = Mock(spec=ReportSubscription)
    db_session.query.return_value.filter.return_value.first.return_value = mock_subscription
    db_session.commit.side_effect = Exception("Database error")

    updated = await subscription_handler.update_subscription(1, name="Updated")
    assert updated is False


@pytest.mark.asyncio
async def test_subscription_validation(subscription_handler):
    """Test subscription parameter validation."""
    # Test invalid email
    with pytest.raises(ValueError):
        await subscription_handler.create_subscription(
            name="Test",
            email="invalid_email",
            frequency=ReportType.DAILY,
            format=ReportFormat.PDF,
            user_id=1,
        )

    # Test invalid frequency
    with pytest.raises(ValueError):
        await subscription_handler.create_subscription(
            name="Test",
            email="test@example.com",
            frequency="invalid_frequency",
            format=ReportFormat.PDF,
            user_id=1,
        )


@pytest.mark.asyncio
async def test_calculate_next_delivery(subscription_handler):
    """Test calculation of next delivery date."""
    now = datetime.now()

    # Test daily frequency
    next_daily = subscription_handler._calculate_next_delivery(ReportType.DAILY)
    assert (next_daily - now).days == 1

    # Test weekly frequency
    next_weekly = subscription_handler._calculate_next_delivery(ReportType.WEEKLY)
    assert (next_weekly - now).days == 7

    # Test monthly frequency
    next_monthly = subscription_handler._calculate_next_delivery(ReportType.MONTHLY)
    assert next_monthly.month - now.month == 1 or (next_monthly.month == 1 and now.month == 12)
