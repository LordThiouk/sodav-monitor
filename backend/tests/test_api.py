"""Tests des endpoints API et WebSocket."""

import pytest
import asyncio
import websockets
import requests
import logging
from typing import Dict, Any
from datetime import datetime
import json
from ..core.config import get_settings

# Configuration
settings = get_settings()
BASE_URL = f"http://{settings.HOST}:{settings.PORT}/api"
WS_URL = f"ws://{settings.HOST}:{settings.PORT}/ws"

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_websocket_connection():
    """Test de la connexion WebSocket et des messages."""
    async with websockets.connect(WS_URL) as websocket:
        # Test d'envoi de message
        test_message = {
            "type": "test",
            "message": "Test message",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send(json.dumps(test_message))
        
        # Test de réception
        response = await websocket.recv()
        response_data = json.loads(response)
        assert "type" in response_data
        assert "timestamp" in response_data

@pytest.mark.parametrize("endpoint", [
    "/health",
    "/stations",
    "/analytics/overview",
    "/reports",
    "/detections"
])
def test_api_endpoints(endpoint: str):
    """Test des endpoints API principaux."""
    response = requests.get(f"{BASE_URL}{endpoint}")
    assert response.status_code in [200, 401, 403]  # 401/403 pour les endpoints protégés
    
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, (dict, list))

@pytest.mark.asyncio
async def test_station_monitoring():
    """Test du monitoring des stations."""
    # Test de création de station
    station_data = {
        "name": "Test Radio",
        "stream_url": "http://test.com/stream",
        "country": "SN",
        "language": "fr"
    }
    response = requests.post(f"{BASE_URL}/stations", json=station_data)
    assert response.status_code == 200 or response.status_code == 401
    
    if response.status_code == 200:
        station = response.json()
        station_id = station["id"]
        
        # Test de mise à jour de station
        update_data = {"is_active": False}
        response = requests.put(f"{BASE_URL}/stations/{station_id}", json=update_data)
        assert response.status_code == 200
        
        # Test de suppression de station
        response = requests.delete(f"{BASE_URL}/stations/{station_id}")
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_detection_workflow():
    """Test du workflow de détection."""
    # Test de création de détection
    detection_data = {
        "station_id": 1,
        "track_title": "Test Track",
        "artist": "Test Artist",
        "confidence": 0.95
    }
    response = requests.post(f"{BASE_URL}/detections", json=detection_data)
    assert response.status_code in [200, 401]
    
    if response.status_code == 200:
        detection = response.json()
        detection_id = detection["id"]
        
        # Test de récupération de détection
        response = requests.get(f"{BASE_URL}/detections/{detection_id}")
        assert response.status_code == 200
        
        # Test de suppression de détection
        response = requests.delete(f"{BASE_URL}/detections/{detection_id}")
        assert response.status_code == 200

def test_error_handling():
    """Test de la gestion des erreurs."""
    # Test avec un ID invalide
    response = requests.get(f"{BASE_URL}/stations/999999")
    assert response.status_code == 404
    
    # Test avec des données invalides
    invalid_data = {"invalid": "data"}
    response = requests.post(f"{BASE_URL}/stations", json=invalid_data)
    assert response.status_code == 422
    
    # Test avec une méthode non autorisée
    response = requests.delete(f"{BASE_URL}/health")
    assert response.status_code == 405 