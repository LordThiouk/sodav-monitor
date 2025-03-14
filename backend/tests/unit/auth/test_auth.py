"""Authentication tests."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from jose import JWTError, jwt

# Test settings
TEST_SETTINGS = {
    "SECRET_KEY": "test_secret_key",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": 15,
}

from backend.utils.auth.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = Mock()
    session.query = Mock()
    session.query.return_value.filter.return_value.first = Mock()
    return session


@pytest.fixture
def mock_user():
    """Mock user for testing."""
    user = Mock()
    user.username = "testuser"
    user.hashed_password = get_password_hash("testpassword")
    return user


def test_verify_password():
    """Test password verification."""
    password = "testpassword"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_get_password_hash():
    """Test password hashing."""
    password = "testpassword"
    hashed = get_password_hash(password)
    assert hashed != password
    assert isinstance(hashed, str)
    assert len(hashed) > 0


def test_create_access_token():
    """Test access token creation."""
    data = {"sub": "test@example.com"}
    token = create_access_token(data, settings_override=TEST_SETTINGS)
    assert isinstance(token, str)

    # Verify token contents
    payload = jwt.decode(
        token, TEST_SETTINGS["SECRET_KEY"], algorithms=[TEST_SETTINGS["ALGORITHM"]]
    )
    assert payload["sub"] == "test@example.com"
    assert "exp" in payload


def test_create_access_token_with_expiry():
    """Test access token creation with custom expiry."""
    data = {"sub": "test@example.com"}
    expires_delta = timedelta(minutes=30)
    token = create_access_token(data, expires_delta, settings_override=TEST_SETTINGS)

    # Verify token expiry
    payload = jwt.decode(
        token, TEST_SETTINGS["SECRET_KEY"], algorithms=[TEST_SETTINGS["ALGORITHM"]]
    )
    exp = datetime.fromtimestamp(payload["exp"])
    now = datetime.utcnow()
    assert (exp - now).total_seconds() > 29 * 60  # Almost 30 minutes


def test_get_current_user_valid(mock_db_session, mock_user):
    """Test getting current user with valid token."""
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user

    # Create a valid token
    token = create_access_token({"sub": mock_user.username}, settings_override=TEST_SETTINGS)
    user = get_current_user(mock_db_session, token, settings_override=TEST_SETTINGS)
    assert user == mock_user


def test_get_current_user_invalid_token(mock_db_session):
    """Test getting current user with invalid token."""
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(mock_db_session, "invalid_token", settings_override=TEST_SETTINGS)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in str(exc_info.value.detail)


def test_get_current_user_missing_username(mock_db_session):
    """Test getting current user with token missing username."""
    token = create_access_token({}, settings_override=TEST_SETTINGS)  # No username in payload
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(mock_db_session, token, settings_override=TEST_SETTINGS)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in str(exc_info.value.detail)


def test_get_current_user_user_not_found(mock_db_session):
    """Test getting current user when user not found in database."""
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    token = create_access_token({"sub": "nonexistent@example.com"}, settings_override=TEST_SETTINGS)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(mock_db_session, token, settings_override=TEST_SETTINGS)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in str(exc_info.value.detail)


def test_get_current_user_expired_token(mock_db_session):
    """Test getting current user with expired token."""
    # Create an expired token
    data = {"sub": "test@example.com"}
    expires_delta = timedelta(minutes=-1)  # Expired 1 minute ago
    token = create_access_token(data, expires_delta, settings_override=TEST_SETTINGS)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(mock_db_session, token, settings_override=TEST_SETTINGS)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in str(exc_info.value.detail)
