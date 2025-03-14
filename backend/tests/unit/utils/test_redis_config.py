"""Tests for Redis configuration."""

from unittest.mock import Mock, patch

import pytest
import redis
from redis.exceptions import ConnectionError, TimeoutError

from backend.core.config.redis import (
    check_redis_connection,
    clear_redis_data,
    get_redis,
    get_test_redis,
)


@pytest.fixture(autouse=True)
def clear_lru_cache():
    """Clear the LRU cache before each test."""
    get_redis.cache_clear()
    yield


@pytest.fixture
def mock_redis_client():
    """Mock Redis client with successful connection."""
    mock_client = Mock()
    mock_client.ping = Mock(return_value=True)
    mock_client.set = Mock(return_value=True)
    mock_client.get = Mock(return_value="test_value")
    mock_client.delete = Mock(return_value=True)
    mock_client.flushdb = Mock(return_value=True)
    return mock_client


@pytest.fixture
def mock_redis_error_client():
    """Mock Redis client with connection error."""
    mock_client = Mock()
    mock_client.ping = Mock(side_effect=redis.ConnectionError("Connection refused"))
    return mock_client


@pytest.fixture
def mock_settings():
    """Mock settings for Redis configuration."""
    with patch("backend.core.config.redis.settings") as mock:
        mock.REDIS_HOST = "localhost"
        mock.REDIS_PORT = 6379
        mock.REDIS_DB = 0
        mock.REDIS_PASSWORD = None
        yield mock


def test_get_redis_success(mock_redis_client, mock_settings):
    """Test successful Redis client creation."""
    with patch("redis.Redis", return_value=mock_redis_client):
        client = get_redis()
        assert client == mock_redis_client
        # Test connection check
        assert check_redis_connection(client) is True
        mock_redis_client.ping.assert_called_once()


def test_get_redis_with_password(mock_redis_client, mock_settings):
    """Test Redis client creation with password."""
    mock_settings.REDIS_PASSWORD = "test_password"
    with patch("redis.Redis", return_value=mock_redis_client):
        client = get_redis()
        assert client == mock_redis_client
        # Test connection check
        assert check_redis_connection(client) is True
        mock_redis_client.ping.assert_called_once()


def test_get_redis_connection_error(mock_redis_error_client):
    """Test Redis client creation with connection error."""
    with pytest.raises(redis.ConnectionError, match="Connection refused"):
        mock_redis_error_client.ping()


def test_get_redis_invalid_settings(mock_settings):
    """Test Redis client creation with invalid settings."""
    mock_settings.REDIS_PORT = "invalid_port"
    with patch("redis.Redis") as mock_redis:
        mock_redis.side_effect = ValueError("Invalid port number")
        with pytest.raises(ValueError):
            get_redis()


def test_get_redis_timeout(mock_redis_client):
    """Test Redis client creation with timeout."""
    mock_redis_client.ping.side_effect = redis.TimeoutError("Connection timeout")
    with pytest.raises(redis.TimeoutError):
        mock_redis_client.ping()


def test_get_test_redis(mock_redis_client):
    """Test getting test Redis connection."""
    with patch("redis.Redis", return_value=mock_redis_client) as mock_redis:
        redis_client = get_test_redis()
        assert redis_client == mock_redis_client
        mock_redis.assert_called_once_with(host="localhost", port=6379, db=1, decode_responses=True)


def test_check_redis_connection_success(mock_redis_client):
    """Test successful Redis connection check."""
    assert check_redis_connection(mock_redis_client) is True
    mock_redis_client.ping.assert_called_once()


def test_check_redis_connection_failure(mock_redis_error_client):
    """Test failed Redis connection check."""
    assert check_redis_connection(mock_redis_error_client) is False


def test_check_redis_connection_no_client(mock_redis_client):
    """Test Redis connection check with no client."""
    with patch("backend.core.config.redis.get_redis", return_value=mock_redis_client):
        assert check_redis_connection(None) is True
        mock_redis_client.ping.assert_called_once()


def test_redis_connection_with_password(mock_redis_client, mock_settings):
    """Test Redis connection with password."""
    mock_settings.REDIS_PASSWORD = "test_password"
    with patch("redis.Redis", return_value=mock_redis_client):
        client = get_redis()
        assert client == mock_redis_client
        # Test connection check
        assert check_redis_connection(client) is True
        mock_redis_client.ping.assert_called_once()


def test_clear_redis_data(mock_redis_client):
    """Test clearing Redis data."""
    clear_redis_data(mock_redis_client)
    mock_redis_client.flushdb.assert_called_once()


def test_clear_redis_data_no_client(mock_redis_client):
    """Test clearing Redis data with no client."""
    with patch("backend.core.config.redis.get_redis", return_value=mock_redis_client):
        clear_redis_data()
        mock_redis_client.flushdb.assert_called_once()


def test_clear_redis_data_error(mock_redis_error_client):
    """Test clearing Redis data with connection error."""
    clear_redis_data(mock_redis_error_client)  # Should not raise an exception


def test_redis_operations(mock_redis_client):
    """Test basic Redis operations."""
    client = mock_redis_client

    # Test set operation
    client.set("test_key", "test_value")
    mock_redis_client.set.assert_called_once_with("test_key", "test_value")

    # Test get operation
    value = client.get("test_key")
    assert value == "test_value"
    mock_redis_client.get.assert_called_once_with("test_key")

    # Test delete operation
    client.delete("test_key")
    mock_redis_client.delete.assert_called_once_with("test_key")


def test_redis_pubsub(mock_redis_client):
    """Test Redis pub/sub functionality"""
    pubsub = Mock()
    pubsub.subscribe = Mock()
    pubsub.get_message = Mock(return_value={"type": "message", "data": b'{"type": "test"}'})
    mock_redis_client.pubsub.return_value = pubsub

    ps = mock_redis_client.pubsub()
    ps.subscribe("test_channel")
    pubsub.subscribe.assert_called_once_with("test_channel")


def test_redis_connection_pool(mock_redis_client):
    """Test Redis connection pool configuration"""
    pool_instance = Mock()
    mock_redis_client.connection_pool = pool_instance
    with patch("redis.Redis", return_value=mock_redis_client):
        client = get_redis()
        assert client == mock_redis_client
        assert client.connection_pool == pool_instance


def test_redis_decode_responses(mock_redis_client):
    """Test Redis decode_responses configuration"""
    with patch("redis.Redis", return_value=mock_redis_client) as mock_redis:
        client = get_redis()
        assert client == mock_redis_client
        mock_redis.assert_called_once_with(
            host="localhost", port=6379, db=0, password=None, decode_responses=True
        )


def test_redis_connection(mock_redis_client):
    """Test Redis connection."""
    with patch("redis.Redis", return_value=mock_redis_client):
        client = get_redis()
        assert client is not None
        assert check_redis_connection(client) is True


def test_redis_clear_data(mock_redis_client):
    """Test clearing Redis data."""
    client = mock_redis_client

    # Set some test data
    client.set("test_key1", "value1")
    client.set("test_key2", "value2")

    # Clear data
    clear_redis_data(client)
    mock_redis_client.flushdb.assert_called_once()
