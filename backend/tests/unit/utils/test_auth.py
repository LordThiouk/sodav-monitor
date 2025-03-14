"""Tests for the authentication utility module."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from jose import JWTError, jwt


@pytest.fixture(autouse=True)
def mock_settings_module(mock_settings):
    """Automatically mock settings for all tests."""
    with patch("backend.core.config.settings.get_settings", return_value=mock_settings):
        yield


from backend.utils.auth.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)


@pytest.fixture
def mock_user():
    """Mock user fixture."""
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


@patch("jose.jwt.encode")
@patch("datetime.datetime")
def test_create_access_token(mock_datetime, mock_jwt_encode):
    """Test creating an access token."""
    # Set up mock datetime
    fixed_time = datetime(2025, 1, 1, 12, 0)
    mock_datetime.now.return_value = fixed_time

    # Set up test data
    data = {"sub": "test@example.com"}

    # Create token
    token = create_access_token(data)

    # Verify JWT encode was called with correct arguments
    mock_jwt_encode.assert_called_once()
    args = mock_jwt_encode.call_args[0]
    assert args[0]["sub"] == "test@example.com"
    assert isinstance(args[0]["exp"], int)
    assert args[0]["exp"] == int(fixed_time.timestamp()) + 15 * 60  # 15 minutes from fixed time


@patch("jose.jwt.encode")
@patch("datetime.datetime")
def test_create_access_token_with_expiry(mock_datetime, mock_jwt_encode):
    """Test creating an access token with custom expiry."""
    # Set up mock datetime
    fixed_time = datetime(2025, 1, 1, 12, 0)
    mock_datetime.now.return_value = fixed_time

    # Set up test data
    data = {"sub": "test@example.com"}
    expires_delta = timedelta(minutes=30)

    # Create token
    token = create_access_token(data, expires_delta)

    # Verify JWT encode was called with correct arguments
    mock_jwt_encode.assert_called_once()
    args = mock_jwt_encode.call_args[0]
    assert args[0]["sub"] == "test@example.com"
    assert isinstance(args[0]["exp"], int)
    assert args[0]["exp"] == int(fixed_time.timestamp()) + 30 * 60  # 30 minutes from fixed time


@patch("jose.jwt.decode")
def test_get_current_user_valid(mock_jwt_decode, mock_db_session, mock_user):
    """Test getting current user with valid token."""
    mock_jwt_decode.return_value = {"sub": mock_user.username}
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user

    user = get_current_user(mock_db_session, "valid_token")
    assert user == mock_user


def test_get_current_user_invalid_token(mock_db_session):
    """Test getting current user with invalid token."""
    with pytest.raises(JWTError):
        get_current_user(mock_db_session, "invalid_token")


def test_get_current_user_missing_username(mock_db_session):
    """Test getting current user with token missing username."""
    with patch("jose.jwt.decode", return_value={}):
        with pytest.raises(Exception) as exc_info:
            get_current_user(mock_db_session, "token_without_username")
        assert "Could not validate credentials" in str(exc_info.value)


def test_get_current_user_user_not_found(mock_db_session):
    """Test getting current user when user not found in database."""
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    with patch("jose.jwt.decode", return_value={"sub": "nonexistent@example.com"}):
        with pytest.raises(Exception) as exc_info:
            get_current_user(mock_db_session, "token_with_nonexistent_user")
        assert "Could not validate credentials" in str(exc_info.value)


def test_get_current_user_expired_token(mock_db_session):
    """Test getting current user with expired token."""
    with patch("jose.jwt.decode", side_effect=JWTError("Token expired")):
        with pytest.raises(Exception) as exc_info:
            get_current_user(mock_db_session, "expired_token")
        assert "Could not validate credentials" in str(exc_info.value)
