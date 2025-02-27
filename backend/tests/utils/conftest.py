"""Test configuration for auth tests."""

import pytest
from unittest.mock import Mock, MagicMock

@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = MagicMock()
    settings.SECRET_KEY = "test_secret_key"
    settings.ALGORITHM = "HS256"
    settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15
    return settings

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session 