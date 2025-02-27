from fastapi import WebSocket
from typing import Dict, List, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str, user_id: Optional[str] = None) -> None:
        """Connect a new WebSocket client."""
        await websocket.accept()
        
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)
            
        logger.info(f"New WebSocket connection: client_id={client_id}, user_id={user_id}")

    def disconnect(self, websocket: WebSocket, client_id: str, user_id: Optional[str] = None) -> None:
        """Disconnect a WebSocket client."""
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
                
        logger.info(f"WebSocket disconnected: client_id={client_id}, user_id={user_id}")

    async def send_personal_message(self, message: dict, client_id: str) -> None:
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to client {client_id}: {str(e)}")

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting message: {str(e)}")

    async def broadcast_to_users(self, message: dict, user_ids: List[str]) -> None:
        """Broadcast a message to specific users."""
        for user_id in user_ids:
            if user_id in self.user_connections:
                for connection in self.user_connections[user_id]:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        logger.error(f"Error sending message to user {user_id}: {str(e)}")

    async def send_detection_update(self, detection_data: dict) -> None:
        """Send a detection update to all connected clients."""
        message = {
            "type": "detection_update",
            "data": detection_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast(message)

    async def send_station_health_update(self, station_id: int, health_data: dict) -> None:
        """Send a station health update to all connected clients."""
        message = {
            "type": "station_health_update",
            "station_id": station_id,
            "data": health_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast(message)

    async def send_error_notification(self, user_id: str, error_message: str) -> None:
        """Send an error notification to a specific user."""
        message = {
            "type": "error_notification",
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_personal_message(message, user_id) 