"""Tests for the Redis configuration module."""

import pytest
from unittest.mock import Mock, patch
import redis
from redis.exceptions import ConnectionError, TimeoutError
from backend.utils.redis_config import get_redis, get_test_redis, check_redis_connection, clear_redis_data

@pytest.fixture
def mock_redis_client():
    with patch('redis.Redis') as mock:
        mock_client = Mock()
        mock_client.ping = Mock(return_value=True)
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_redis_error_client():
    with patch('redis.Redis') as mock:
        mock_client = Mock()
        mock_client.ping = Mock(side_effect=redis.ConnectionError("Connection refused"))
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_settings():
    with patch('backend.utils.redis_config.settings') as mock:
        mock.REDIS_HOST = 'localhost'
        mock.REDIS_PORT = 6379
        mock.REDIS_DB = 0
        mock.REDIS_PASSWORD = None
        yield mock

def test_get_redis_success(mock_redis_client):
    """Test successful Redis client creation"""
    client = get_redis()
    assert client == mock_redis_client
    mock_redis_client.ping.assert_called_once()

def test_get_redis_with_password(mock_redis_client):
    """Test Redis client creation with password"""
    with patch('os.getenv', return_value='test_password'):
        client = get_redis()
        assert client == mock_redis_client
        mock_redis_client.ping.assert_called_once()

def test_get_redis_connection_error(mock_redis_error_client):
    """Test Redis client creation with connection error"""
    with pytest.raises(redis.ConnectionError, match="Connection refused"):
        get_redis()

def test_get_redis_invalid_settings():
    """Test Redis client creation with invalid settings"""
    with patch('os.getenv', return_value='invalid_port'):
        with pytest.raises(ValueError, match="Invalid Redis port"):
            get_redis()

def test_get_redis_timeout():
    """Test Redis client creation with timeout"""
    with patch('redis.Redis.ping', side_effect=redis.TimeoutError("Connection timeout")):
        with pytest.raises(redis.TimeoutError, match="Connection timeout"):
            get_redis()

def test_get_test_redis(mock_redis_client):
    """Test getting test Redis connection."""
    redis_client = get_test_redis()
    assert redis_client is not None
    mock_redis_client.assert_called_once_with(
        host='localhost',
        port=6379,
        db=1,
        decode_responses=True
    )

def test_check_redis_connection_success(mock_redis_client):
    """Test successful Redis connection check"""
    assert check_redis_connection(mock_redis_client) is True
    mock_redis_client.ping.assert_called_once()

def test_check_redis_connection_failure(mock_redis_error_client):
    """Test failed Redis connection check"""
    assert check_redis_connection(mock_redis_error_client) is False
    mock_redis_error_client.ping.assert_called_once()

def test_check_redis_connection_no_client():
    """Test Redis connection check with no client"""
    assert check_redis_connection(None) is False

def test_redis_connection_with_invalid_settings():
    """Test Redis connection with invalid settings."""
    mock_client = Mock()
    mock_client.ping.side_effect = ConnectionError()
    assert check_redis_connection(mock_client) is False

def test_redis_connection_timeout():
    """Test Redis connection timeout."""
    mock_client = Mock()
    mock_client.ping.side_effect = TimeoutError()
    with pytest.raises(TimeoutError):
        check_redis_connection(mock_client)

def test_redis_connection_with_password(mock_redis_client, mock_settings):
    """Test Redis connection with password."""
    with patch('backend.utils.redis_config.settings') as mock_settings:
        mock_settings.REDIS_HOST = 'localhost'
        mock_settings.REDIS_PORT = 6379
        mock_settings.REDIS_DB = 0
        mock_settings.REDIS_PASSWORD = 'test_password'
        
        # Clear the lru_cache to ensure we get a fresh Redis instance
        get_redis.cache_clear()
        
        redis_client = get_redis()
        assert redis_client is not None
        mock_redis_client.assert_called_once_with(
            host='localhost',
            port=6379,
            db=0,
            password='test_password',
            decode_responses=True
        )

def test_clear_redis_data():
    """Test clearing Redis data."""
    mock_client = Mock()
    clear_redis_data(mock_client)
    mock_client.flushdb.assert_called_once()

@pytest.mark.asyncio
async def test_redis_pubsub(mock_redis_client):
    """Test Redis pub/sub functionality"""
    pubsub = Mock()
    pubsub.subscribe = Mock()
    pubsub.get_message = Mock(return_value={"type": "message", "data": b'{"type": "test"}'})
    mock_redis_client.pubsub.return_value = pubsub
    
    client = get_redis()
    ps = client.pubsub()
    
    # Test subscribe
    ps.subscribe("test_channel")
    pubsub.subscribe.assert_called_once_with("test_channel")
    
    # Test message retrieval
    message = ps.get_message()
    assert message["type"] == "message"
    assert message["data"] == b'{"type": "test"}'

def test_redis_cache_clear():
    """Test Redis cache clearing"""
    get_redis.cache_clear()  # Should not raise any exception

@pytest.mark.asyncio
async def test_redis_connection_pool(mock_redis_client):
    """Test Redis connection pool configuration"""
    with patch('redis.ConnectionPool') as mock_pool:
        mock_pool.return_value = Mock()
        client = get_redis()
        assert client == mock_redis_client
        mock_pool.assert_called_once()

def test_redis_ssl_config(mock_redis_client):
    """Test Redis SSL configuration"""
    with patch('os.getenv', return_value='true'):
        client = get_redis()
        assert client == mock_redis_client
        # Verify SSL settings were passed to Redis client creation

def test_redis_max_connections(mock_redis_client):
    """Test Redis max connections configuration"""
    with patch('os.getenv', return_value='100'):
        client = get_redis()
        assert client == mock_redis_client
        # Verify max connections setting was passed to connection pool

def test_redis_decode_responses(mock_redis_client):
    """Test Redis decode_responses configuration"""
    client = get_redis()
    assert client == mock_redis_client
    # Verify decode_responses was set to True in Redis client creation 