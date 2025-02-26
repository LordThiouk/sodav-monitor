"""Module de gestion des WebSockets."""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from fastapi import WebSocket
import json
from .redis_config import get_redis
import asyncio

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Gestionnaire de connexions WebSocket."""
    
    def __init__(self, max_connections: int = 100):
        self.active_connections: List[WebSocket] = []
        self.redis = get_redis()
        self.max_connections = max_connections
    
    async def connect(self, websocket: WebSocket):
        """Établir une connexion WebSocket."""
        if len(self.active_connections) >= self.max_connections:
            raise Exception("Maximum connections reached")
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Fermer une connexion WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: Dict):
        """Diffuser un message à tous les clients connectés."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Nettoyer les connexions fermées
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

async def broadcast_track_detection(track_data: Dict):
    """Diffuser une détection de piste à tous les clients."""
    try:
        # Valider les données
        if not isinstance(track_data.get("station_id"), int) or \
           not track_data.get("track_id") or \
           not track_data.get("title") or \
           not track_data.get("artist"):
            await send_error(None, "Données de piste invalides")
            return

        # Publier sur Redis pour la synchronisation entre les workers
        redis = get_redis()
        redis.publish("track_detections", json.dumps(track_data))
        
        # Diffuser via WebSocket
        await manager.broadcast({
            "type": "track_detection",
            "data": track_data
        })
    except Exception as e:
        # Logger l'erreur mais ne pas la propager
        print(f"Erreur lors de la diffusion de la détection: {str(e)}")

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
