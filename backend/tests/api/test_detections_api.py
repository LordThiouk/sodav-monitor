"""Test cases for the detections API endpoints."""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.models.models import TrackDetection, Track, RadioStation, Artist, StationStatus
from backend.schemas.base import DetectionCreate, DetectionResponse

@pytest.fixture
def test_artist(db_session: Session) -> Artist:
    """Create a test artist."""
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.commit()
    db_session.refresh(artist)
    return artist

@pytest.fixture
def test_track(db_session: Session, test_artist: Artist) -> Track:
    """Create a test track."""
    track = Track(
        title="Test Track",
        artist_id=test_artist.id,
        isrc="USABC1234567",
        label="Test Label",
        fingerprint="test_fingerprint"
    )
    db_session.add(track)
    db_session.commit()
    db_session.refresh(track)
    return track

@pytest.fixture
def test_station(db_session: Session) -> RadioStation:
    """Create a test radio station."""
    station = RadioStation(
        name="Test Station",
        stream_url="http://test.stream/audio",
        region="Test Region",
        language="fr",
        type="radio",
        status=StationStatus.ACTIVE
    )
    db_session.add(station)
    db_session.commit()
    db_session.refresh(station)
    return station

@pytest.fixture
def test_detections(db_session: Session, test_track: Track, test_station: RadioStation) -> List[TrackDetection]:
    """Create multiple test detections."""
    detections = []
    base_time = datetime.utcnow() - timedelta(hours=12)
    
    for i in range(5):
        detection = TrackDetection(
            track_id=test_track.id,
            station_id=test_station.id,
            detected_at=base_time + timedelta(hours=i),
            confidence=0.95,
            play_duration=timedelta(seconds=180),
            fingerprint="test_fingerprint",
            audio_hash="test_hash"
        )
        detections.append(detection)
    
    db_session.add_all(detections)
    db_session.commit()
    for detection in detections:
        db_session.refresh(detection)
    return detections

def test_get_detections(test_client: TestClient, test_detections: List[TrackDetection], auth_headers: Dict[str, str]):
    """Test getting all detections."""
    response = test_client.get("/api/detections/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert all(d["confidence"] == 0.95 for d in data)

def test_get_detections_with_filters(test_client: TestClient, test_detections: List[TrackDetection], test_station: RadioStation, auth_headers: Dict[str, str]):
    """Test getting detections with filters."""
    response = test_client.get(
        f"/api/detections/?station_id={test_station.id}&confidence_threshold=0.9",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert all(d["station"]["id"] == test_station.id for d in data)

def test_search_detections(test_client: TestClient, test_detections: List[TrackDetection], auth_headers: Dict[str, str]):
    """Test searching detections."""
    response = test_client.get("/api/detections/search/?query=Test Track", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all("Test Track" in d["track"]["title"] for d in data)

def test_get_detection_by_id(test_client: TestClient, test_detections: List[TrackDetection], auth_headers: Dict[str, str]):
    """Test getting a specific detection by ID."""
    detection_id = test_detections[0].id
    response = test_client.get(f"/api/detections/{detection_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == detection_id

def test_get_nonexistent_detection(test_client: TestClient, auth_headers: Dict[str, str]):
    """Test getting a nonexistent detection."""
    response = test_client.get("/api/detections/99999", headers=auth_headers)
    assert response.status_code == 404

def test_create_detection(test_client: TestClient, test_track: Track, test_station: RadioStation, auth_headers: Dict[str, str]):
    """Test creating a new detection."""
    now = datetime.utcnow()
    detection_data = {
        "detection": {
            "track_id": test_track.id,
            "station_id": test_station.id,
            "detected_at": now.isoformat(),
            "confidence": 0.95,
            "play_duration": 180,
            "fingerprint": "test_fingerprint",
            "audio_hash": "test_hash"
        }
    }
    
    response = test_client.post("/api/detections/", json=detection_data, headers=auth_headers)
    print(f"\nResponse status: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
    assert response.status_code == 200
    data = response.json()
    assert data["track"]["id"] == test_track.id
    assert data["track"]["title"] == test_track.title
    assert data["track"]["artist"] == test_track.artist.name
    assert data["station"]["id"] == test_station.id
    assert data["station"]["name"] == test_station.name
    assert data["confidence"] == 0.95

def test_delete_detection(test_client: TestClient, test_detections: List[TrackDetection], auth_headers: Dict[str, str]):
    """Test deleting a detection."""
    detection_id = test_detections[0].id
    response = test_client.delete(f"/api/detections/{detection_id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Verify deletion
    response = test_client.get(f"/api/detections/{detection_id}", headers=auth_headers)
    assert response.status_code == 404

def test_get_station_detections(test_client: TestClient, test_detections: List[TrackDetection], test_station: RadioStation, auth_headers: Dict[str, str]):
    """Test getting detections for a specific station."""
    response = test_client.get(f"/api/detections/station/{test_station.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(d["station"]["id"] == test_station.id for d in data)

def test_get_track_detections(test_client: TestClient, test_detections: List[TrackDetection], test_track: Track, auth_headers: Dict[str, str]):
    """Test getting detections for a specific track."""
    response = test_client.get(f"/api/detections/track/{test_track.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(d["track"]["id"] == test_track.id for d in data)

def test_get_latest_detections(test_client: TestClient, test_detections: List[TrackDetection], auth_headers: Dict[str, str]):
    """Test getting latest detections."""
    response = test_client.get("/api/detections/latest/", headers=auth_headers)
    print(f"\nResponse status: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(isinstance(d, dict) for d in data)
    assert all(
        all(key in d for key in ["id", "track", "station", "detected_at", "confidence"])
        for d in data
    )
    # Verify first detection
    first_detection = data[0]
    assert isinstance(first_detection["track"], dict)
    assert isinstance(first_detection["station"], dict)
    assert "id" in first_detection["track"]
    assert "title" in first_detection["track"]
    assert "artist" in first_detection["track"]
    assert "id" in first_detection["station"]
    assert "name" in first_detection["station"]

def test_process_audio(test_client: TestClient, test_station: RadioStation, auth_headers: Dict[str, str]):
    """Test processing audio for a station."""
    response = test_client.post(f"/api/detections/process?station_id={test_station.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["status"] == "success" 