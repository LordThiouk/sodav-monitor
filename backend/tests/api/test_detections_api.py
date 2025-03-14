"""Test cases for the detections API endpoints."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.models import Artist, RadioStation, StationStatus, Track, TrackDetection, User
from backend.schemas.base import DetectionCreate, DetectionResponse


@pytest.fixture
def test_artist(db_session: Session) -> Artist:
    """Create a test artist."""
    unique_id = uuid.uuid4().hex[:8]
    artist = Artist(name=f"Test Artist {unique_id}")
    db_session.add(artist)
    db_session.commit()
    db_session.refresh(artist)
    return artist


@pytest.fixture
def test_track(db_session: Session, test_artist: Artist) -> Track:
    """Create a test track."""
    unique_id = uuid.uuid4().hex[:8]
    track = Track(
        title=f"Test Track {unique_id}",
        artist_id=test_artist.id,
        isrc=f"USABC{unique_id}",
        label="Test Label",
        fingerprint=f"test_fingerprint_{unique_id}",
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
        country="SN",
        language="fr",
        type="radio",
        status="active",
        is_active=True,  # Ensure the station is active
    )
    db_session.add(station)
    db_session.commit()
    db_session.refresh(station)
    return station


@pytest.fixture
def mock_radio_manager():
    """Create a mock RadioManager."""
    mock_manager = Mock()
    mock_manager.detect_music = AsyncMock(
        return_value={
            "status": "success",
            "message": "Successfully processed station",
            "detections": [{"detection": {"type": "music", "source": "local", "confidence": 0.95}}],
        }
    )
    return mock_manager


@pytest.fixture
def test_app(mock_radio_manager):
    """Create a test FastAPI application with mocked RadioManager."""
    app = FastAPI()

    # Set up app state
    app.state.radio_manager = mock_radio_manager

    # Include routers
    from backend.routers import auth, websocket
    from backend.routers.analytics import router as analytics_router
    from backend.routers.channels import router as channels_router
    from backend.routers.detections import router as detections_router
    from backend.routers.reports import router as reports_router

    app.include_router(auth.router, prefix="/api")
    app.include_router(
        detections_router, prefix="/api/detections"
    )  # Correct prefix for detections router
    app.include_router(
        channels_router, prefix="/api/channels"
    )  # Correct prefix for channels router
    app.include_router(analytics_router, prefix="/api/analytics")
    app.include_router(reports_router, prefix="/api/reports")
    app.include_router(websocket.router, prefix="/api/ws")

    return app


@pytest.fixture
def test_client(
    db_session: Session, test_user: User, auth_headers: Dict[str, str], test_app, mock_radio_manager
):
    """Create a test client."""
    from backend.models.database import get_db
    from backend.utils.auth import get_current_user, oauth2_scheme

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_user():
        return test_user

    def override_oauth2_scheme():
        return auth_headers["Authorization"].split(" ")[1]

    # Override dependencies
    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = override_get_current_user
    test_app.dependency_overrides[oauth2_scheme] = override_oauth2_scheme

    # Ensure RadioManager is set in app state
    test_app.state.radio_manager = mock_radio_manager

    with TestClient(test_app) as client:
        yield client

    test_app.dependency_overrides.clear()


@pytest.fixture
def test_detections(
    db_session: Session, test_track: Track, test_station: RadioStation
) -> List[TrackDetection]:
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
            audio_hash="test_hash",
        )
        detections.append(detection)

    db_session.add_all(detections)
    db_session.commit()
    for detection in detections:
        db_session.refresh(detection)
    return detections


def test_get_detections(
    test_client: TestClient, test_detections: List[TrackDetection], auth_headers: Dict[str, str]
):
    """Test getting all detections."""
    # Get the IDs of the test detections
    test_detection_ids = [d.id for d in test_detections]

    response = test_client.get("/api/detections/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 5  # At least 5 detections

    # Filter the response to only include the test detections
    test_data = [d for d in data if d["id"] in test_detection_ids]

    # Print confidence values for debugging
    print("\nConfidence values in test detections:")
    for i, d in enumerate(test_data):
        print(
            f"Detection {i}: id = {d['id']}, confidence = {d['confidence']}, type = {type(d['confidence'])}"
        )

    # Check that all test detections have confidence 0.95
    assert all(d["confidence"] == 0.95 for d in test_data)


def test_get_detections_with_filters(
    test_client: TestClient,
    test_detections: List[TrackDetection],
    test_station: RadioStation,
    auth_headers: Dict[str, str],
):
    """Test getting detections with filters."""
    response = test_client.get(
        f"/api/detections/?station_id={test_station.id}&confidence_threshold=0.9",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert all(d["station"]["id"] == test_station.id for d in data)


def test_search_detections(
    test_client: TestClient, test_detections: List[TrackDetection], auth_headers: Dict[str, str]
):
    """Test searching detections."""
    response = test_client.get("/api/detections/search/?query=Test Track", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all("Test Track" in d["track"]["title"] for d in data)


def test_get_detection_by_id(
    test_client: TestClient, test_detections: List[TrackDetection], auth_headers: Dict[str, str]
):
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


def test_create_detection(
    test_client: TestClient,
    test_track: Track,
    test_station: RadioStation,
    auth_headers: Dict[str, str],
):
    """Test creating a new detection."""
    now = datetime.utcnow()
    detection_data = {
        "detection_data": {
            "track_id": test_track.id,
            "station_id": test_station.id,
            "detected_at": now.isoformat(),
            "confidence": 0.95,
            "play_duration": 180,
            "fingerprint": "test_fingerprint",
            "audio_hash": "test_hash",
        }
    }

    response = test_client.post("/api/detections/", json=detection_data, headers=auth_headers)
    print(f"\nResponse status: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
    assert response.status_code == 200
    data = response.json()

    # Verify the response
    assert "id" in data
    assert data["track"]["id"] == test_track.id
    assert data["station"]["id"] == test_station.id
    assert data["confidence"] == 0.95
    assert data["play_duration"] == "PT3M"  # ISO 8601 duration format for 3 minutes


def test_delete_detection(
    test_client: TestClient, test_detections: List[TrackDetection], auth_headers: Dict[str, str]
):
    """Test deleting a detection."""
    detection_id = test_detections[0].id
    response = test_client.delete(f"/api/detections/{detection_id}", headers=auth_headers)
    assert response.status_code == 200

    # Verify deletion
    response = test_client.get(f"/api/detections/{detection_id}", headers=auth_headers)
    assert response.status_code == 404


def test_get_station_detections(
    test_client: TestClient,
    test_detections: List[TrackDetection],
    test_station: RadioStation,
    auth_headers: Dict[str, str],
):
    """Test getting detections for a specific station."""
    response = test_client.get(f"/api/detections/station/{test_station.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(d["station"]["id"] == test_station.id for d in data)


def test_get_track_detections(
    test_client: TestClient,
    test_detections: List[TrackDetection],
    test_track: Track,
    auth_headers: Dict[str, str],
):
    """Test getting detections for a specific track."""
    response = test_client.get(f"/api/detections/track/{test_track.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(d["track"]["id"] == test_track.id for d in data)


def test_get_latest_detections(
    test_client: TestClient, test_detections: List[TrackDetection], auth_headers: Dict[str, str]
):
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


def test_process_audio(
    test_client: TestClient, test_station: RadioStation, auth_headers: Dict[str, str]
):
    """Test processing audio for a station."""
    # Create a mock file
    file_content = b"test audio content"
    files = {"file": ("test.mp3", file_content, "audio/mpeg")}

    response = test_client.post(
        f"/api/detections/process?station_id={test_station.id}", headers=auth_headers, files=files
    )

    print(f"\nResponse status: {response.status_code}")
    print(f"Response content: {response.content.decode()}")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["status"] == "success"


def test_detect_music_on_station(
    test_client: TestClient,
    test_station: RadioStation,
    auth_headers: Dict[str, str],
    mock_radio_manager,
):
    """Test detecting music on a specific station."""
    # Set the mock in the app state
    test_client.app.state.radio_manager = mock_radio_manager

    # Make the request
    response = test_client.post(
        f"/api/channels/{test_station.id}/detect-music", headers=auth_headers
    )

    # Verify the response
    assert response.status_code == 200
    data = response.json()

    # Check if the response has the expected format
    assert "message" in data
    assert f"Music detection initiated for {test_station.name}" in data["message"]

    # Since we can't directly verify the mock was called (due to background task),
    # we'll just check that the response is correct
    # The actual call to detect_music happens in a background task which is not executed during the test
