from typing import Dict, List
from datetime import datetime
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Store active WebSocket connections
active_connections: List[WebSocket] = []

async def broadcast_track_detection(track_data: Dict):
    """Broadcast track detection to all connected clients"""
    if active_connections:
        message = {
            "type": "track_detection",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "title": track_data.get("title"),
                "artist": track_data.get("artist"),
                "album": track_data.get("album"),
                "isrc": track_data.get("isrc"),
                "label": track_data.get("label"),
                "confidence": track_data.get("confidence"),
                "play_duration": track_data.get("play_duration"),
                "station": {
                    "id": track_data.get("station_id"),
                    "name": track_data.get("station_name")
                },
                "detected_at": track_data.get("detected_at")
            }
        }
        
        for connection in active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {str(e)}")
                active_connections.remove(connection)
