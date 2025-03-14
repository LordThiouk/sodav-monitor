"""Tests for the validators module."""

from datetime import datetime, timedelta

import pytest

from backend.models.models import ReportFormat, ReportType
from backend.utils.validators import (
    validate_date_range,
    validate_email,
    validate_report_format,
    validate_subscription_frequency,
)


def test_validate_email():
    """Test email validation."""
    # Valid email addresses
    assert validate_email("test@example.com") is True
    assert validate_email("user.name+tag@domain.co.uk") is True
    assert validate_email("test.email@subdomain.domain.com") is True

    # Invalid email addresses
    assert validate_email("invalid.email") is False
    assert validate_email("@domain.com") is False
    assert validate_email("test@.com") is False
    assert validate_email("test@domain.") is False
    assert validate_email("") is False


def test_validate_date_range():
    """Test date range validation."""
    now = datetime.now()

    # Valid date ranges
    assert validate_date_range(now - timedelta(days=7), now) is True

    assert validate_date_range(now, now + timedelta(days=30)) is True

    # Invalid date ranges
    assert validate_date_range(now, now - timedelta(days=1)) is False

    assert validate_date_range(None, now) is False

    assert validate_date_range(now, None) is False


def test_validate_report_format():
    """Test report format validation."""
    # Valid formats
    assert validate_report_format(ReportFormat.CSV) is True
    assert validate_report_format(ReportFormat.XLSX) is True
    assert validate_report_format(ReportFormat.PDF) is True

    # Invalid formats
    assert validate_report_format("invalid_format") is False
    assert validate_report_format(None) is False
    assert validate_report_format("") is False


def test_validate_subscription_frequency():
    """Test subscription frequency validation."""
    # Valid frequencies
    assert validate_subscription_frequency(ReportType.DAILY) is True
    assert validate_subscription_frequency(ReportType.WEEKLY) is True
    assert validate_subscription_frequency(ReportType.MONTHLY) is True

    # Invalid frequencies
    assert validate_subscription_frequency("invalid_frequency") is False
    assert validate_subscription_frequency(None) is False
    assert validate_subscription_frequency("") is False


def test_validate_email_with_special_cases():
    """Test email validation with special cases."""
    # RFC 5322 compliant email addresses
    assert validate_email("user+mailbox@example.com") is True
    assert validate_email("customer/department=shipping@example.com") is True
    assert validate_email("$A12345@example.com") is True
    assert validate_email("!def!xyz%abc@example.com") is True

    # Invalid special cases
    assert validate_email(" space@domain.com") is False
    assert validate_email("test@domain.com ") is False
    assert validate_email("test@@domain.com") is False
    assert validate_email("test@domain..com") is False
    assert validate_email(".test@domain.com") is False
    assert validate_email("test.@domain.com") is False
    assert validate_email("te..st@domain.com") is False


def test_validate_date_range_edge_cases():
    """Test date range validation edge cases."""
    now = datetime.now()

    # Same start and end date
    assert validate_date_range(now, now) is True

    # Very far future date
    assert validate_date_range(now, now + timedelta(days=3650)) is True  # 10 years

    # Very far past date
    assert validate_date_range(now - timedelta(days=3650), now) is True  # 10 years

    # Microsecond difference
    future = now + timedelta(microseconds=1)
    assert validate_date_range(now, future) is True

    past = now - timedelta(microseconds=1)
    assert validate_date_range(now, past) is False
