from typing import Dict, List, Optional
from datetime import datetime
import logging
from fastapi import WebSocket
import json
from redis_config import get_redis
import asyncio

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.redis = None
        self.pubsub = None
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new WebSocket client"""
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            
            # Store client info in Redis
            self.redis = await get_redis()
            await self.redis.hset(
                "websocket_clients",
                client_id,
                json.dumps({
                    "connected_at": asyncio.datetime.now().isoformat(),
                    "client_id": client_id
                })
            )
            
            logger.info(f"WebSocket client {client_id} connected")
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket client {client_id}: {str(e)}")
            raise
    
    async def disconnect(self, client_id: str):
        """Disconnect a WebSocket client"""
        try:
            if client_id in self.active_connections:
                await self.active_connections[client_id].close()
                del self.active_connections[client_id]
            
            # Remove client info from Redis
            if self.redis:
                await self.redis.hdel("websocket_clients", client_id)
                
            logger.info(f"WebSocket client {client_id} disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket client {client_id}: {str(e)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        try:
            # Publish message to Redis channel
            self.redis = await get_redis()
            await self.redis.publish(
                "websocket_broadcast",
                json.dumps(message)
            )
            
            # Send to local connections
            disconnected_clients = []
            for client_id, connection in self.active_connections.items():
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to client {client_id}: {str(e)}")
                    disconnected_clients.append(client_id)
            
            # Clean up disconnected clients
            for client_id in disconnected_clients:
                await self.disconnect(client_id)
                
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")
    
    async def start_listener(self):
        """Start Redis subscription listener"""
        try:
            self.redis = await get_redis()
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe("websocket_broadcast")
            
            # Listen for messages
            while True:
                try:
                    message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                    if message and message["type"] == "message":
                        data = json.loads(message["data"])
                        await self.broadcast(data)
                except Exception as e:
                    logger.error(f"Error in Redis listener: {str(e)}")
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error starting Redis listener: {str(e)}")
            
    async def stop_listener(self):
        """Stop Redis subscription listener"""
        if self.pubsub:
            await self.pubsub.unsubscribe("websocket_broadcast")
            await self.pubsub.close()

# Create global WebSocket manager instance
manager = WebSocketManager()

async def broadcast_track_detection(track_data: Dict):
    """Broadcast track detection to all connected clients"""
    if manager.active_connections:
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
        
        for connection in manager.active_connections.values():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {str(e)}")
                manager.active_connections.remove(connection)
