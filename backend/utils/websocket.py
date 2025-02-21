from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from fastapi import WebSocket
import json
from ..redis_config import get_redis
import asyncio

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.redis = None
        self.pubsub = None
        self.last_heartbeat: Dict[str, datetime] = {}
        self.max_connections = 100  # Maximum number of concurrent connections
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new WebSocket client"""
        try:
            if len(self.active_connections) >= self.max_connections:
                await websocket.close(code=1008, reason="Too many connections")
                logger.warning(f"Rejected client {client_id} due to connection limit")
                return
                
            await websocket.accept()
            self.active_connections[client_id] = websocket
            self.last_heartbeat[client_id] = datetime.now()
            
            # Store client info in Redis
            self.redis = await get_redis()
            await self.redis.hset(
                "websocket_clients",
                client_id,
                json.dumps({
                    "connected_at": datetime.now().isoformat(),
                    "client_id": client_id,
                    "last_heartbeat": datetime.now().isoformat()
                })
            )
            
            logger.info(f"WebSocket client {client_id} connected ({len(self.active_connections)}/{self.max_connections})")
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket client {client_id}: {str(e)}")
            raise
    
    async def disconnect(self, client_id: str):
        """Disconnect a WebSocket client"""
        try:
            if client_id in self.active_connections:
                await self.active_connections[client_id].close()
                del self.active_connections[client_id]
                
            if client_id in self.last_heartbeat:
                del self.last_heartbeat[client_id]
            
            # Remove client info from Redis
            if self.redis:
                await self.redis.hdel("websocket_clients", client_id)
                
            logger.info(f"WebSocket client {client_id} disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket client {client_id}: {str(e)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        try:
            # Skip broadcasting heartbeat messages
            if message.get("type") == "ping":
                return
                
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
                    # Check if client is still active (had recent heartbeat)
                    if client_id in self.last_heartbeat:
                        last_beat = self.last_heartbeat[client_id]
                        if datetime.now() - last_beat > timedelta(minutes=2):
                            logger.warning(f"Client {client_id} heartbeat timeout")
                            disconnected_clients.append(client_id)
                            continue
                            
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to client {client_id}: {str(e)}")
                    disconnected_clients.append(client_id)
            
            # Clean up disconnected clients
            for client_id in disconnected_clients:
                await self.disconnect(client_id)
                
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")
    
    async def update_heartbeat(self, client_id: str):
        """Update client's last heartbeat time"""
        try:
            self.last_heartbeat[client_id] = datetime.now()
            if self.redis:
                client_info = json.loads(await self.redis.hget("websocket_clients", client_id))
                client_info["last_heartbeat"] = datetime.now().isoformat()
                await self.redis.hset(
                    "websocket_clients",
                    client_id,
                    json.dumps(client_info)
                )
        except Exception as e:
            logger.error(f"Error updating heartbeat for client {client_id}: {str(e)}")
            
    async def cleanup_stale_connections(self):
        """Clean up stale connections based on heartbeat"""
        while True:
            try:
                now = datetime.now()
                disconnected_clients = []
                
                for client_id, last_beat in self.last_heartbeat.items():
                    if now - last_beat > timedelta(minutes=2):
                        disconnected_clients.append(client_id)
                        
                for client_id in disconnected_clients:
                    logger.warning(f"Removing stale client {client_id}")
                    await self.disconnect(client_id)
                    
                await asyncio.sleep(60)  # Check every minute
                    
            except Exception as e:
                logger.error(f"Error in cleanup task: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
    
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

async def broadcast_station_update(station_data: Dict):
    """Broadcast station status update to all connected clients"""
    if manager.active_connections:
        message = {
            "type": "station_update",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "id": station_data.get("id"),
                "name": station_data.get("name"),
                "status": station_data.get("status"),
                "is_active": station_data.get("is_active"),
                "last_checked": station_data.get("last_checked"),
                "last_detection_time": station_data.get("last_detection_time"),
                "stream_url": station_data.get("stream_url"),
                "country": station_data.get("country"),
                "language": station_data.get("language"),
                "total_play_time": station_data.get("total_play_time")
            }
        }
        await manager.broadcast(message)

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
