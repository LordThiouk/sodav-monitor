"""Tests for the WebSocket module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json

from backend.utils.streams.websocket import (
    WebSocketManager,
    broadcast_track_detection,
    broadcast_station_update
)

@pytest.fixture
def mock_websocket():
    """Fixture for mocked WebSocket connection."""
    websocket = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.send_text = AsyncMock()
    return websocket

@pytest.fixture
def connection_manager():
    """Fixture for ConnectionManager instance."""
    return ConnectionManager()

@pytest.mark.asyncio
async def test_connection_manager_connect(connection_manager, mock_websocket):
    """Test WebSocket connection establishment."""
    await connection_manager.connect(mock_websocket)
    
    assert mock_websocket in connection_manager.active_connections
    mock_websocket.accept.assert_called_once()

@pytest.mark.asyncio
async def test_connection_manager_disconnect(connection_manager, mock_websocket):
    """Test WebSocket disconnection."""
    await connection_manager.connect(mock_websocket)
    connection_manager.disconnect(mock_websocket)
    
    assert mock_websocket not in connection_manager.active_connections

@pytest.mark.asyncio
async def test_connection_manager_broadcast(connection_manager, mock_websocket):
    """Test broadcasting messages to all connections."""
    await connection_manager.connect(mock_websocket)
    test_message = {"type": "test", "data": "test message"}
    
    await connection_manager.broadcast(test_message)
    
    mock_websocket.send_json.assert_called_once_with(test_message)

@pytest.mark.asyncio
async def test_broadcast_track_detection(mock_websocket):
    """Test broadcasting track detection."""
    track_data = {
        "station_id": 1,
        "track_id": 1,
        "title": "Test Song",
        "artist": "Test Artist"
    }
    
    with patch("backend.utils.websocket.get_redis") as mock_redis:
        mock_redis.return_value.publish = Mock()
        await broadcast_track_detection(track_data)
        
        # Verify Redis publish
        mock_redis.return_value.publish.assert_called_once_with(
            "track_detections",
            json.dumps(track_data)
        )

@pytest.mark.asyncio
async def test_broadcast_station_status(mock_websocket):
    """Test broadcasting station status."""
    station_data = {
        "station_id": 1,
        "status": "active",
        "last_checked": datetime.now().isoformat()
    }
    
    with patch("backend.utils.websocket.get_redis") as mock_redis:
        mock_redis.return_value.publish = Mock()
        await broadcast_station_status(station_data)
        
        # Verify Redis publish
        mock_redis.return_value.publish.assert_called_once_with(
            "station_status",
            json.dumps(station_data)
        )

@pytest.mark.asyncio
async def test_broadcast_system_status(connection_manager, mock_websocket):
    """Test broadcasting system status."""
    await connection_manager.connect(mock_websocket)
    status_data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }
    
    with patch("backend.utils.websocket.ConnectionManager.broadcast") as mock_broadcast:
        await broadcast_system_status(status_data)
        
        expected_message = {
            "type": "system_status",
            "data": status_data
        }
        mock_broadcast.assert_called_once_with(expected_message)

@pytest.mark.asyncio
async def test_send_heartbeat(mock_websocket):
    """Test sending heartbeat to client."""
    await send_heartbeat(mock_websocket)
    
    mock_websocket.send_json.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["type"] == "heartbeat"
    assert "timestamp" in call_args

@pytest.mark.asyncio
async def test_process_websocket_message_heartbeat(mock_websocket):
    """Test processing heartbeat message."""
    message = json.dumps({"type": "heartbeat"})
    
    await process_websocket_message(message, mock_websocket)
    
    mock_websocket.send_json.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["type"] == "heartbeat"

@pytest.mark.asyncio
async def test_process_websocket_message_invalid_json(mock_websocket):
    """Test processing invalid JSON message."""
    invalid_message = "invalid json"
    
    with patch("backend.utils.websocket.send_error") as mock_send_error:
        await process_websocket_message(invalid_message, mock_websocket)
        mock_send_error.assert_called_once_with(mock_websocket, "Message JSON invalide")

@pytest.mark.asyncio
async def test_process_websocket_message_unknown_type(mock_websocket):
    """Test processing message with unknown type."""
    message = json.dumps({"type": "unknown"})
    
    with patch("backend.utils.websocket.send_error") as mock_send_error:
        await process_websocket_message(message, mock_websocket)
        mock_send_error.assert_called_once_with(
            mock_websocket,
            "Type de message non reconnu: unknown"
        )

@pytest.mark.asyncio
async def test_connection_manager_reconnect(connection_manager, mock_websocket):
    """Test WebSocket reconnection handling."""
    # Initial connection
    await connection_manager.connect(mock_websocket)
    assert mock_websocket in connection_manager.active_connections
    
    # Simulate disconnect
    connection_manager.disconnect(mock_websocket)
    assert mock_websocket not in connection_manager.active_connections
    
    # Reconnect
    await connection_manager.connect(mock_websocket)
    assert mock_websocket in connection_manager.active_connections
    mock_websocket.accept.assert_called()

@pytest.mark.asyncio
async def test_connection_manager_broadcast_with_failed_connection(connection_manager, mock_websocket):
    """Test broadcasting with a failed connection."""
    await connection_manager.connect(mock_websocket)
    mock_websocket.send_json.side_effect = Exception("Connection failed")
    
    test_message = {"type": "test", "data": "test message"}
    await connection_manager.broadcast(test_message)
    
    # Verify the failed connection was removed
    assert mock_websocket not in connection_manager.active_connections

@pytest.mark.asyncio
async def test_process_websocket_message_validation(mock_websocket):
    """Test message validation during processing."""
    # Test missing type field
    message = json.dumps({"data": "test"})
    with patch("backend.utils.websocket.send_error") as mock_send_error:
        await process_websocket_message(message, mock_websocket)
        mock_send_error.assert_called_once_with(mock_websocket, "Type de message manquant")
    
    # Test empty message
    message = json.dumps({})
    with patch("backend.utils.websocket.send_error") as mock_send_error:
        await process_websocket_message(message, mock_websocket)
        mock_send_error.assert_called_once_with(mock_websocket, "Message vide")

@pytest.mark.asyncio
async def test_broadcast_track_detection_with_invalid_data(mock_websocket):
    """Test track detection broadcast with invalid data."""
    invalid_track_data = {
        "station_id": "invalid",  # Should be integer
        "track_id": None,
        "title": "",
        "artist": None
    }
    
    with patch("backend.utils.websocket.get_redis") as mock_redis, \
         patch("backend.utils.websocket.send_error") as mock_send_error:
        mock_redis.return_value.publish = Mock()
        await broadcast_track_detection(invalid_track_data)
        
        # Verify error was sent
        mock_send_error.assert_called_once()
        # Verify Redis publish was not called
        mock_redis.return_value.publish.assert_not_called()

@pytest.mark.asyncio
async def test_connection_manager_max_connections(connection_manager):
    """Test handling of maximum connections limit."""
    max_connections = 100
    websockets = [AsyncMock() for _ in range(max_connections + 1)]
    
    # Connect up to max limit
    for i in range(max_connections):
        await connection_manager.connect(websockets[i])
        assert websockets[i] in connection_manager.active_connections
    
    # Try to connect one more
    with pytest.raises(Exception) as exc_info:
        await connection_manager.connect(websockets[-1])
    assert "Maximum connections reached" in str(exc_info.value) 