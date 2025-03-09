"""Module de gestion des WebSockets."""

from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
import logging
from fastapi import WebSocket
import json
from backend.core.config.redis import get_redis
import asyncio

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manage WebSocket connections and broadcasting."""
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self.active_connections: Set[WebSocket] = set()
        self.redis = None
        
    async def connect(self, websocket: WebSocket):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")
        
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
        
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
            
        # Convert message to JSON
        message_str = json.dumps(message)
        
        # Broadcast to all connections
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {str(e)}")
                disconnected.add(connection)
                
        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)
            
    async def initialize_redis(self):
        """Initialize Redis connection."""
        if not self.redis:
            self.redis = await get_redis()
            
    async def publish_to_redis(self, channel: str, message: Dict[str, Any]):
        """Publish a message to Redis channel."""
        try:
            await self.initialize_redis()
            message_str = json.dumps(message)
            await self.redis.publish(channel, message_str)
        except Exception as e:
            logger.error(f"Error publishing to Redis: {str(e)}")
            
    async def subscribe_to_redis(self, channel: str):
        """Subscribe to Redis channel and broadcast messages."""
        try:
            await self.initialize_redis()
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(channel)
            
            while True:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True)
                    if message:
                        data = json.loads(message['data'])
                        await self.broadcast(data)
                except Exception as e:
                    logger.error(f"Error processing Redis message: {str(e)}")
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error subscribing to Redis: {str(e)}")
            
    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific client."""
        try:
            message_str = json.dumps(message)
            await websocket.send_text(message_str)
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")
            await self.disconnect(websocket)
            
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
        
    async def cleanup(self):
        """Clean up resources."""
        # Close all connections
        for connection in self.active_connections:
            try:
                await connection.close()
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")
                
        self.active_connections.clear()
        
        # Close Redis connection
        if self.redis:
            await self.redis.close()
            self.redis = None

manager = WebSocketManager()

async def broadcast_track_detection(track_data: Dict[str, Any]):
    """Broadcast track detection to all connected clients."""
    await manager.broadcast({
        'type': 'track_detection',
        'data': track_data,
        'timestamp': datetime.now().isoformat()
    })

async def broadcast_station_update(station_data: Dict):
    """Diffuser une mise à jour de station à tous les clients."""
    try:
        # Valider les données
        if not isinstance(station_data.get("id"), int) or \
           not station_data.get("name") or \
           not station_data.get("stream_url"):
            await send_error(None, "Données de station invalides")
            return

        # Publier sur Redis pour la synchronisation
        redis = get_redis()
        redis.publish("station_updates", json.dumps(station_data))
        
        # Diffuser via WebSocket
        await manager.broadcast({
            "type": "station_update",
            "data": station_data
        })
    except Exception as e:
        print(f"Erreur lors de la diffusion de la mise à jour de la station: {str(e)}")

async def broadcast_station_status(station_data: Dict):
    """Diffuser le statut d'une station à tous les clients."""
    try:
        # Publier sur Redis pour la synchronisation
        redis = get_redis()
        redis.publish("station_status", json.dumps(station_data))
        
        # Diffuser via WebSocket
        await manager.broadcast({
            "type": "station_status",
            "data": station_data
        })
    except Exception as e:
        print(f"Erreur lors de la diffusion du statut: {str(e)}")

async def broadcast_system_status(status_data: Dict):
    """Diffuser le statut du système à tous les clients."""
    try:
        await manager.broadcast({
            "type": "system_status",
            "data": status_data
        })
    except Exception as e:
        print(f"Erreur lors de la diffusion du statut système: {str(e)}")

async def send_error(websocket: WebSocket, error: str):
    """Envoyer un message d'erreur à un client spécifique."""
    try:
        await websocket.send_json({
            "type": "error",
            "message": error
        })
    except Exception as e:
        print(f"Erreur lors de l'envoi du message d'erreur: {str(e)}")

async def send_heartbeat(websocket: WebSocket):
    """Envoyer un heartbeat à un client spécifique."""
    try:
        await websocket.send_json({
            "type": "heartbeat",
            "timestamp": str(datetime.utcnow())
        })
    except Exception as e:
        print(f"Erreur lors de l'envoi du heartbeat: {str(e)}")

async def process_websocket_message(data: str, websocket: WebSocket):
    """Traiter un message WebSocket reçu."""
    try:
        message = json.loads(data)
        
        # Valider le message
        if not message:
            await send_error(websocket, "Message vide")
            return
            
        if "type" not in message:
            await send_error(websocket, "Type de message manquant")
            return
            
        message_type = message.get("type")
        
        if message_type == "heartbeat":
            await send_heartbeat(websocket)
        elif message_type == "subscribe":
            # TODO: Implémenter la logique d'abonnement
            pass
        elif message_type == "unsubscribe":
            # TODO: Implémenter la logique de désabonnement
            pass
        else:
            await send_error(websocket, f"Type de message non reconnu: {message_type}")
            
    except json.JSONDecodeError:
        await send_error(websocket, "Message JSON invalide")
    except Exception as e:
        await send_error(websocket, f"Erreur lors du traitement du message: {str(e)}")
