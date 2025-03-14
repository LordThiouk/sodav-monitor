"""WebSocket management utilities.

This module provides functionality for managing WebSocket connections
and broadcasting updates to connected clients.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from backend.models.models import RadioStation
from backend.utils.logging_config import setup_logging

logger = setup_logging(__name__)


class ConnectionManager:
    """WebSocket connection manager.

    This class handles WebSocket connections, disconnections, and
    broadcasting messages to connected clients.
    """

    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Connect a new WebSocket client.

        Args:
            websocket: The WebSocket connection to add
        """
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client.

        Args:
            websocket: The WebSocket connection to remove
        """
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict):
        """Broadcast a message to all connected clients.

        Args:
            message: The message to broadcast
        """
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection)
            except Exception as e:
                logger.error(f"Error broadcasting message: {str(e)}")
                self.disconnect(connection)


# Alias for backward compatibility
WebSocketManager = ConnectionManager

manager = ConnectionManager()


async def broadcast_station_update(station: RadioStation):
    """Broadcast a station status update.

    Args:
        station: The station that was updated
    """
    await manager.broadcast(
        {
            "type": "station_update",
            "data": {
                "id": station.id,
                "name": station.name,
                "status": station.status.value,
                "last_checked": station.last_checked.isoformat() if station.last_checked else None,
            },
        }
    )


async def broadcast_system_status(status: Dict):
    """Broadcast system status information.

    Args:
        status: System status information to broadcast
    """
    await manager.broadcast(
        {
            "type": "system_status",
            "data": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


async def broadcast_station_status(station_id: int, status: str, message: Optional[str] = None):
    """Broadcast a station status update.

    Args:
        station_id: ID of the station
        status: Status of the station
        message: Optional status message
    """
    await manager.broadcast(
        {
            "type": "station_status",
            "data": {
                "id": station_id,
                "status": status,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
    )


async def broadcast_track_detection(detection_data: Dict[str, Any]):
    """Broadcast a track detection event.

    Args:
        detection_data: Detection data to broadcast
    """
    await manager.broadcast(
        {
            "type": "track_detection",
            "data": detection_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


async def send_heartbeat(websocket: WebSocket):
    """Send a heartbeat message to a WebSocket client.

    Args:
        websocket: The WebSocket connection to send the heartbeat to
    """
    try:
        await websocket.send_json(
            {
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Error sending heartbeat: {str(e)}")
        manager.disconnect(websocket)


async def process_websocket_message(websocket: WebSocket, message: str):
    """Process a message received from a WebSocket client.

    Args:
        websocket: The WebSocket connection that sent the message
        message: The message received

    Returns:
        Dict: Response message
    """
    try:
        data = json.loads(message)
        message_type = data.get("type")

        if message_type == "heartbeat":
            await send_heartbeat(websocket)
            return {"status": "ok", "type": "heartbeat_response"}
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return {"status": "error", "message": f"Unknown message type: {message_type}"}
    except json.JSONDecodeError:
        logger.error("Invalid JSON message received")
        return {"status": "error", "message": "Invalid JSON message"}
    except Exception as e:
        logger.error(f"Error processing WebSocket message: {str(e)}")
        return {"status": "error", "message": str(e)}
