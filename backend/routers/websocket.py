import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.heartbeat_interval = 30  # seconds

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    heartbeat_task = None
    try:
        # Start heartbeat in background
        heartbeat_task = asyncio.create_task(send_heartbeat(websocket))

        while True:
            try:
                data = await websocket.receive_text()
                # Process received data if needed
                await process_websocket_message(data, websocket)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
        manager.disconnect(websocket)


async def send_heartbeat(websocket: WebSocket):
    try:
        while True:
            await websocket.send_json(
                {"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()}
            )
            await asyncio.sleep(manager.heartbeat_interval)
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Heartbeat error: {e}")


async def process_websocket_message(data: str, websocket: WebSocket):
    """Traite les messages reçus via WebSocket."""
    try:
        message = json.loads(data)
        message_type = message.get("type")

        if message_type == "subscribe":
            # Gérer les abonnements aux événements
            pass
        elif message_type == "unsubscribe":
            # Gérer les désabonnements
            pass
        else:
            logger.warning(f"Unknown message type: {message_type}")

    except json.JSONDecodeError:
        logger.error("Invalid JSON message received")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


async def broadcast_track_detection(track_data: Dict):
    """Diffuse une détection de piste à tous les clients connectés."""
    message = {"type": "detection", "data": track_data, "timestamp": datetime.utcnow().isoformat()}
    await manager.broadcast(message)
