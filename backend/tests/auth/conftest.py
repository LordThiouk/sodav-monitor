"""Test configuration for auth tests."""

import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = Mock()
    settings.SECRET_KEY = "test_secret_key"
    settings.ALGORITHM = "HS256"
    settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15
    return settings

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = Mock()
    session.query = Mock()
    session.query.return_value.filter.return_value.first = Mock()
    return session 