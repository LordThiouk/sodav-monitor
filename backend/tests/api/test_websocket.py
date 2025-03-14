"""Tests WebSocket."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from backend.core.config.redis import get_redis
from backend.core.websocket import ConnectionManager


@pytest.fixture
def connection_manager():
    return ConnectionManager()


@pytest.fixture
def mock_redis():
    with patch("backend.core.websocket.get_redis") as mock:
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock()
        mock_redis.subscribe = AsyncMock()
        mock_redis.get_message = AsyncMock()
        mock.return_value = mock_redis
        yield mock_redis


@pytest.mark.asyncio
async def test_connection_manager_connect(connection_manager):
    """Test connection establishment"""
    websocket = AsyncMock()
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"
    client_id = "test_client"
    user_id = "test_user"

    await connection_manager.connect(websocket, client_id, user_id)
    assert websocket in connection_manager.active_connections[client_id]
    assert websocket in connection_manager.user_connections[user_id]
    assert len(connection_manager.active_connections) == 1
    assert len(connection_manager.user_connections) == 1


@pytest.mark.asyncio
async def test_connection_manager_disconnect(connection_manager):
    """Test connection disconnection"""
    websocket = AsyncMock()
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"
    client_id = "test_client"
    user_id = "test_user"

    await connection_manager.connect(websocket, client_id, user_id)
    connection_manager.disconnect(websocket, client_id, user_id)
    assert client_id not in connection_manager.active_connections
    assert user_id not in connection_manager.user_connections


@pytest.mark.asyncio
async def test_connection_manager_broadcast(connection_manager, mock_redis):
    """Test message broadcasting to all connections"""
    websocket1 = AsyncMock()
    websocket1.client = Mock()
    websocket1.client.host = "127.0.0.1"

    websocket2 = AsyncMock()
    websocket2.client = Mock()
    websocket2.client.host = "127.0.0.2"

    await connection_manager.connect(websocket1, "client1", "user1")
    await connection_manager.connect(websocket2, "client2", "user2")

    message = {"type": "track_detection", "data": {"track_id": "123"}}
    await connection_manager.broadcast(message)

    websocket1.send_json.assert_called_once_with(message)
    websocket2.send_json.assert_called_once_with(message)
    mock_redis.publish.assert_called_once_with("sodav_monitor:websocket", json.dumps(message))


@pytest.mark.asyncio
async def test_connection_manager_broadcast_with_failed_connection(connection_manager, mock_redis):
    """Test broadcasting with a failed connection"""
    websocket1 = AsyncMock()
    websocket1.client = Mock()
    websocket1.client.host = "127.0.0.1"
    websocket1.send_json.side_effect = Exception("Connection lost")

    websocket2 = AsyncMock()
    websocket2.client = Mock()
    websocket2.client.host = "127.0.0.2"

    await connection_manager.connect(websocket1, "client1", "user1")
    await connection_manager.connect(websocket2, "client2", "user2")

    message = {"type": "track_detection", "data": {"track_id": "123"}}
    await connection_manager.broadcast(message)

    # Second websocket should still receive the message
    websocket2.send_json.assert_called_once_with(message)
    mock_redis.publish.assert_called_once_with("sodav_monitor:websocket", json.dumps(message))


@pytest.mark.asyncio
async def test_send_personal_message(connection_manager):
    """Test sending personal message to a specific client"""
    websocket = AsyncMock()
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"
    client_id = "test_client"

    await connection_manager.connect(websocket, client_id)
    message = {"type": "notification", "data": "test message"}
    await connection_manager.send_personal_message(message, client_id)

    websocket.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_broadcast_to_users(connection_manager):
    """Test broadcasting to specific users"""
    websocket = AsyncMock()
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"
    user_id = "test_user"

    await connection_manager.connect(websocket, "client1", user_id)
    message = {"type": "notification", "data": "test message"}
    await connection_manager.broadcast_to_users(message, [user_id])

    websocket.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_send_detection_update(connection_manager, mock_redis):
    """Test sending detection update"""
    websocket = AsyncMock()
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"

    await connection_manager.connect(websocket, "client1", "user1")
    detection_data = {"track_id": "123", "confidence": 0.95}
    await connection_manager.send_detection_update(detection_data)

    assert websocket.send_json.call_args[0][0]["type"] == "detection_update"
    assert websocket.send_json.call_args[0][0]["data"] == detection_data
    assert mock_redis.publish.called


@pytest.mark.asyncio
async def test_send_station_health_update(connection_manager, mock_redis):
    """Test sending station health update"""
    websocket = AsyncMock()
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"

    await connection_manager.connect(websocket, "client1", "user1")
    health_data = {"status": "online", "latency": 100}
    await connection_manager.send_station_health_update(1, health_data)

    assert websocket.send_json.call_args[0][0]["type"] == "station_health_update"
    assert websocket.send_json.call_args[0][0]["data"] == health_data
    assert mock_redis.publish.called


@pytest.mark.asyncio
async def test_send_error_notification(connection_manager):
    """Test sending error notification"""
    websocket = AsyncMock()
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"
    client_id = "test_client"

    await connection_manager.connect(websocket, client_id)
    await connection_manager.send_error_notification(client_id, "Test error")

    assert websocket.send_json.call_args[0][0]["type"] == "error_notification"
    assert websocket.send_json.call_args[0][0]["message"] == "Test error"


@pytest.mark.asyncio
async def test_redis_integration(connection_manager, mock_redis):
    """Test Redis integration for message broadcasting"""
    websocket = AsyncMock()
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"
    client_id = "test_client"

    # Mock Redis publish method
    mock_redis.publish = AsyncMock()

    await connection_manager.connect(websocket, client_id)

    # Simulate Redis message
    message = {"type": "track_detection", "data": {"track_id": "123"}}
    mock_redis.publish.assert_not_called()  # Should not publish on connect

    await connection_manager.broadcast(message)
    mock_redis.publish.assert_called_once_with("sodav_monitor:websocket", json.dumps(message))
