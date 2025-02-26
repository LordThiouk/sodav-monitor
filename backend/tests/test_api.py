"""Tests des endpoints API."""

import pytest
import asyncio
import websockets
import requests
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
import json
from ..core.config import get_settings
from ..models.models import ReportType, ReportFormat, ReportStatus, StationStatus

# Configuration
settings = get_settings()
BASE_URL = f"http://{settings.HOST}:{settings.PORT}/api"
WS_URL = f"ws://{settings.HOST}:{settings.PORT}/ws"

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def auth_headers():
    """Fixture pour les en-têtes d'authentification."""
    # Simuler la connexion
    login_data = {
        "username": "test_user",
        "password": "test_password"
    }
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}

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
        
        # Test de heartbeat
        heartbeat = {
            "type": "heartbeat",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send(json.dumps(heartbeat))
        response = await websocket.recv()
        response_data = json.loads(response)
        assert response_data["type"] == "heartbeat_ack"

@pytest.mark.parametrize("endpoint,expected_keys", [
    ("/api/health", ["status", "version"]),
    ("/api/stations", ["items", "total"]),
    ("/api/analytics/overview", ["detection_count", "active_stations"]),
    ("/api/reports", ["items", "total"]),
    ("/api/detections", ["items", "total"])
])
def test_api_endpoints(test_client, endpoint: str, expected_keys: list, auth_headers):
    """Test des endpoints API principaux."""
    response = test_client.get(endpoint, headers=auth_headers)
    assert response.status_code in [200, 401, 403]
    
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, (dict, list))
        if isinstance(data, dict):
            for key in expected_keys:
                assert key in data

def test_station_monitoring(test_client, auth_headers):
    """Test du monitoring des stations."""
    # Test de création de station
    station_data = {
        "name": "Test Radio",
        "stream_url": "http://test.com/stream",
        "country": "SN",
        "language": "fr",
        "region": "Dakar",
        "type": "radio"
    }
    response = test_client.post("/api/stations", json=station_data, headers=auth_headers)
    assert response.status_code == 200
    station = response.json()
    station_id = station["id"]
    
    # Test de mise à jour de station
    update_data = {
        "is_active": False,
        "region": "Saint-Louis"
    }
    response = test_client.put(f"/api/stations/{station_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    updated_station = response.json()
    assert updated_station["region"] == "Saint-Louis"
    
    # Test de récupération des statistiques de la station
    response = test_client.get(f"/api/stations/{station_id}/stats", headers=auth_headers)
    assert response.status_code == 200
    stats = response.json()
    assert "detection_count" in stats
    
    # Test de suppression de station
    response = test_client.delete(f"/api/stations/{station_id}", headers=auth_headers)
    assert response.status_code == 200

def test_detection_workflow(test_client, auth_headers, sample_station):
    """Test du workflow de détection."""
    # Test de création de détection
    detection_data = {
        "station_id": sample_station.id,
        "track_title": "Test Track",
        "artist": "Test Artist",
        "confidence": 0.95,
        "duration": 180
    }
    response = test_client.post("/api/detections", json=detection_data, headers=auth_headers)
    assert response.status_code == 200
    detection = response.json()
    detection_id = detection["id"]
    
    # Test de récupération de détection
    response = test_client.get(f"/api/detections/{detection_id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Test de filtrage des détections
    params = {
        "start_date": (datetime.now() - timedelta(days=1)).isoformat(),
        "end_date": datetime.now().isoformat(),
        "station_id": sample_station.id
    }
    response = test_client.get("/api/detections", params=params, headers=auth_headers)
    assert response.status_code == 200
    
    # Test de suppression de détection
    response = test_client.delete(f"/api/detections/{detection_id}", headers=auth_headers)
    assert response.status_code == 200

def test_report_management(test_client, auth_headers):
    """Test de la gestion des rapports."""
    # Test de création de rapport
    report_data = {
        "type": ReportType.DAILY,
        "format": ReportFormat.PDF,
        "start_date": datetime.now().isoformat(),
        "end_date": (datetime.now() + timedelta(days=1)).isoformat()
    }
    response = test_client.post("/api/reports", json=report_data, headers=auth_headers)
    assert response.status_code == 200
    report = response.json()
    report_id = report["id"]
    
    # Test de récupération de rapport
    response = test_client.get(f"/api/reports/{report_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] in [status.value for status in ReportStatus]
    
    # Test de téléchargement de rapport
    response = test_client.get(f"/api/reports/{report_id}/download", headers=auth_headers)
    assert response.status_code in [200, 404]  # 404 si le rapport n'est pas encore généré

def test_error_handling(test_client, auth_headers):
    """Test de la gestion des erreurs."""
    # Test avec un ID invalide
    response = test_client.get("/api/stations/999999", headers=auth_headers)
    assert response.status_code == 404
    error_data = response.json()
    assert "detail" in error_data
    
    # Test avec des données invalides
    invalid_data = {"invalid": "data"}
    response = test_client.post("/api/stations", json=invalid_data, headers=auth_headers)
    assert response.status_code == 422
    validation_error = response.json()
    assert "detail" in validation_error
    
    # Test avec une méthode non autorisée
    response = test_client.delete("/api/health", headers=auth_headers)
    assert response.status_code == 405
    
    # Test avec un token invalide
    invalid_headers = {"Authorization": "Bearer invalid_token"}
    response = test_client.get("/api/stations", headers=invalid_headers)
    assert response.status_code == 401
    
    # Test de validation des données de station
    invalid_station = {
        "name": "Test Radio",
        "stream_url": "invalid_url",  # URL invalide
        "country": "XX"  # Code pays invalide
    }
    response = test_client.post("/api/stations", json=invalid_station, headers=auth_headers)
    assert response.status_code == 422
    
    # Test de validation des données de détection
    invalid_detection = {
        "station_id": 1,
        "confidence": 2.0  # Confidence > 1.0
    }
    response = test_client.post("/api/detections", json=invalid_detection, headers=auth_headers)
    assert response.status_code == 422 