"""Tests WebSocket."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
from backend.core.websocket import ConnectionManager
from backend.core.config.redis import get_redis

@pytest.fixture
def connection_manager():
    return ConnectionManager()

@pytest.fixture
def mock_redis():
    with patch('backend.core.config.redis.get_redis') as mock:
        mock_redis = Mock()
        mock_redis.publish = Mock()
        mock_redis.subscribe = Mock()
        mock_redis.get_message = Mock()
        mock.return_value = mock_redis
        yield mock_redis

@pytest.mark.asyncio
async def test_connection_manager_connect(connection_manager):
    """Test connection establishment"""
    websocket = Mock()
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"
    
    await connection_manager.connect(websocket)
    assert websocket in connection_manager.active_connections
    assert len(connection_manager.active_connections) == 1

@pytest.mark.asyncio
async def test_connection_manager_disconnect(connection_manager):
    """Test connection disconnection"""
    websocket = Mock()
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"
    
    await connection_manager.connect(websocket)
    await connection_manager.disconnect(websocket)
    assert websocket not in connection_manager.active_connections
    assert len(connection_manager.active_connections) == 0

@pytest.mark.asyncio
async def test_connection_manager_broadcast(connection_manager):
    """Test message broadcasting to all connections"""
    websocket1 = Mock()
    websocket1.client = Mock()
    websocket1.client.host = "127.0.0.1"
    websocket1.send_text = Mock()
    
    websocket2 = Mock()
    websocket2.client = Mock()
    websocket2.client.host = "127.0.0.2"
    websocket2.send_text = Mock()
    
    await connection_manager.connect(websocket1)
    await connection_manager.connect(websocket2)
    
    message = {"type": "track_detection", "data": {"track_id": "123"}}
    await connection_manager.broadcast(message)
    
    websocket1.send_text.assert_called_once_with(json.dumps(message))
    websocket2.send_text.assert_called_once_with(json.dumps(message))

@pytest.mark.asyncio
async def test_connection_manager_broadcast_with_failed_connection(connection_manager):
    """Test broadcasting with a failed connection"""
    websocket1 = Mock()
    websocket1.client = Mock()
    websocket1.client.host = "127.0.0.1"
    websocket1.send_text = Mock(side_effect=Exception("Connection lost"))
    
    websocket2 = Mock()
    websocket2.client = Mock()
    websocket2.client.host = "127.0.0.2"
    websocket2.send_text = Mock()
    
    await connection_manager.connect(websocket1)
    await connection_manager.connect(websocket2)
    
    message = {"type": "track_detection", "data": {"track_id": "123"}}
    await connection_manager.broadcast(message)
    
    # Second websocket should still receive the message
    websocket2.send_text.assert_called_once_with(json.dumps(message))
    assert websocket1 not in connection_manager.active_connections

@pytest.mark.asyncio
async def test_connection_manager_max_connections(connection_manager):
    """Test maximum connection limit"""
    connection_manager.MAX_CONNECTIONS = 2
    
    websocket1 = Mock()
    websocket1.client = Mock()
    websocket1.client.host = "127.0.0.1"
    
    websocket2 = Mock()
    websocket2.client = Mock()
    websocket2.client.host = "127.0.0.2"
    
    websocket3 = Mock()
    websocket3.client = Mock()
    websocket3.client.host = "127.0.0.3"
    
    await connection_manager.connect(websocket1)
    await connection_manager.connect(websocket2)
    
    with pytest.raises(Exception, match="Maximum connections reached"):
        await connection_manager.connect(websocket3)

@pytest.mark.asyncio
async def test_send_heartbeat(connection_manager):
    """Test heartbeat sending"""
    websocket = Mock()
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"
    websocket.send_text = Mock()
    
    await connection_manager.connect(websocket)
    await connection_manager.send_heartbeat()
    
    expected_message = {"type": "heartbeat", "data": {"status": "alive"}}
    websocket.send_text.assert_called_once_with(json.dumps(expected_message))

@pytest.mark.asyncio
async def test_process_websocket_message_heartbeat(connection_manager):
    """Test processing of heartbeat messages"""
    websocket = Mock()
    message = {"type": "heartbeat", "data": {"status": "alive"}}
    
    response = await connection_manager.process_websocket_message(websocket, json.dumps(message))
    assert response == {"type": "heartbeat", "data": {"status": "alive"}}

@pytest.mark.asyncio
async def test_process_websocket_message_invalid_json(connection_manager):
    """Test handling of invalid JSON messages"""
    websocket = Mock()
    invalid_message = "invalid json"
    
    with pytest.raises(json.JSONDecodeError):
        await connection_manager.process_websocket_message(websocket, invalid_message)

@pytest.mark.asyncio
async def test_process_websocket_message_unknown_type(connection_manager):
    """Test handling of unknown message types"""
    websocket = Mock()
    message = {"type": "unknown", "data": {}}
    
    with pytest.raises(ValueError, match="Unknown message type"):
        await connection_manager.process_websocket_message(websocket, json.dumps(message))

@pytest.mark.asyncio
async def test_process_websocket_message_validation(connection_manager):
    """Test message validation"""
    websocket = Mock()
    invalid_message = {"type": "track_detection"}  # Missing data field
    
    with pytest.raises(ValueError, match="Invalid message format"):
        await connection_manager.process_websocket_message(websocket, json.dumps(invalid_message))

@pytest.mark.asyncio
async def test_redis_integration(connection_manager, mock_redis):
    """Test Redis integration for message broadcasting"""
    websocket = Mock()
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"
    websocket.send_text = Mock()
    
    await connection_manager.connect(websocket)
    
    # Simulate Redis message
    message = {"type": "track_detection", "data": {"track_id": "123"}}
    mock_redis.publish.assert_not_called()  # Should not publish on connect
    
    await connection_manager.broadcast(message)
    mock_redis.publish.assert_called_once_with(
        "sodav_monitor:websocket",
        json.dumps(message)
    ) 