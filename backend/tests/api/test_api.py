"""Tests for the API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Generator
import json
import jwt

from backend.main import app
from backend.models.models import (
    User, RadioStation, Track, TrackDetection,
    Artist, StationStatus, ReportType, ReportFormat
)
from backend.core.security import create_access_token
from backend.tests.auth.test_auth import TEST_SETTINGS

# Test settings
TEST_SETTINGS = {
    'SECRET_KEY': "test_secret_key",
    'ALGORITHM': "HS256",
    'ACCESS_TOKEN_EXPIRE_MINUTES': 15
}

@pytest.fixture
def client() -> Generator:
    """Create a test client."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        role="user"
    )
    user.set_password("testpass")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Create authentication headers for a test user."""
    access_token = create_access_token(
        data={"sub": test_user.email},
        settings_override=TEST_SETTINGS
    )
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
def test_station(db_session: Session) -> RadioStation:
    """Create a test radio station."""
    station = RadioStation(
        name="Test Radio",
        stream_url="http://test.stream/audio",
        country="SN",
        language="fr",
        is_active=True,
        status=StationStatus.active.value,
        last_checked=datetime.utcnow()
    )
    db_session.add(station)
    db_session.commit()
    return station

@pytest.fixture
def test_artist(db_session: Session) -> Artist:
    """Create a test artist."""
    artist = Artist(
        name="Test Artist",
        country="SN",
        label="Test Label"
    )
    db_session.add(artist)
    db_session.commit()
    return artist

@pytest.fixture
def test_track(db_session: Session, test_artist: Artist) -> Track:
    """Create a test track."""
    track = Track(
        title="Test Track",
        artist_id=test_artist.id,
        duration=timedelta(minutes=3),
        fingerprint="test_fingerprint"
    )
    db_session.add(track)
    db_session.commit()
    return track

@pytest.fixture
def test_detection(db_session: Session, test_track: Track, test_station: RadioStation) -> TrackDetection:
    """Create a test detection."""
    detection = TrackDetection(
        track_id=test_track.id,
        station_id=test_station.id,
        confidence=0.95,
        detected_at=datetime.utcnow(),
        play_duration=timedelta(minutes=3),
        is_valid=True
    )
    db_session.add(detection)
    db_session.commit()
    return detection

class TestAuthAPI:
    """Test authentication endpoints."""
    
    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            data={"username": test_user.email, "password": "testpass"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
        
    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/auth/login",
            data={"username": "wrong@email.com", "password": "wrongpass"}
        )
        assert response.status_code == 401
        assert "detail" in response.json()
        
    def test_login_inactive_user(self, client: TestClient, test_user: User, db_session: Session):
        """Test login with inactive user."""
        # Deactivate user
        test_user.is_active = False
        db_session.commit()
        
        response = client.post(
            "/api/auth/login",
            data={"username": test_user.email, "password": "testpass"}
        )
        assert response.status_code == 401
        
        # Reactivate user for other tests
        test_user.is_active = True
        db_session.commit()
        
    def test_create_user_success(self, client: TestClient):
        """Test successful user creation."""
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123"
        }
        response = client.post("/api/auth/users", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert "password" not in data
        
    def test_create_user_duplicate_email(self, client: TestClient, test_user: User):
        """Test user creation with duplicate email."""
        user_data = {
            "username": "another",
            "email": test_user.email,  # Using existing email
            "password": "pass123"
        }
        response = client.post("/api/auth/users", json=user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
        
    def test_forgot_password(self, client: TestClient, test_user: User):
        """Test password reset request."""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": test_user.email}
        )
        assert response.status_code == 200
        assert "message" in response.json()
        
    def test_forgot_password_invalid_email(self, client: TestClient):
        """Test password reset with invalid email."""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )
        assert response.status_code == 404
        
    def test_reset_password(self, client: TestClient, test_user: User, db_session: Session):
        """Test password reset."""
        # First request password reset
        client.post(
            "/api/auth/forgot-password",
            json={"email": test_user.email}
        )
        
        # Get the reset token from the database
        db_session.refresh(test_user)
        reset_token = test_user.reset_token
        
        # Reset password
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "newpass123"
            }
        )
        assert response.status_code == 200
        
        # Try logging in with new password
        response = client.post(
            "/api/auth/login",
            data={"username": test_user.email, "password": "newpass123"}
        )
        assert response.status_code == 200
        
    def test_reset_password_invalid_token(self, client: TestClient):
        """Test password reset with invalid token."""
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "invalid_token",
                "new_password": "newpass123"
            }
        )
        assert response.status_code == 400
        
    def test_protected_route_without_token(self, client: TestClient):
        """Test accessing protected route without token."""
        response = client.get("/api/channels/")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
        
    def test_protected_route_with_expired_token(self, client: TestClient, test_user: User):
        """Test accessing protected route with expired token."""
        # Create expired token (30 minutes in the past)
        payload = {
            "sub": test_user.email,
            "exp": datetime.utcnow() - timedelta(minutes=30)
        }
        expired_token = jwt.encode(
            payload,
            TEST_SETTINGS["SECRET_KEY"],
            algorithm=TEST_SETTINGS["ALGORITHM"]
        )
        
        response = client.get(
            "/api/channels/",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

class TestChannelsAPI:
    """Test channels endpoints."""
    
    def test_get_stations(self, client: TestClient, auth_headers: Dict[str, str], test_station: RadioStation):
        """Test getting list of stations."""
        response = client.get("/api/channels/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert data[0]["name"] == test_station.name
        assert data[0]["stream_url"] == test_station.stream_url
        assert data[0]["country"] == test_station.country
        assert data[0]["language"] == test_station.language
        assert isinstance(data[0]["is_active"], bool)
        
    def test_get_stations_with_filters(self, client: TestClient, auth_headers: Dict[str, str], test_station: RadioStation):
        """Test getting stations with filters."""
        # Test country filter
        response = client.get(f"/api/channels/?country={test_station.country}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(s["country"] == test_station.country for s in data)
        
        # Test language filter
        response = client.get(f"/api/channels/?language={test_station.language}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(s["language"] == test_station.language for s in data)
        
        # Test status filter
        response = client.get("/api/channels/?status=active", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(s["status"] == "active" for s in data)
        
    def test_get_stations_pagination(self, client: TestClient, auth_headers: Dict[str, str], db_session: Session):
        """Test station list pagination."""
        # Create multiple stations
        for i in range(5):
            station = RadioStation(
                name=f"Test Radio {i}",
                stream_url=f"http://test{i}.stream/audio",
                country="SN",
                language="fr",
                is_active=True
            )
            db_session.add(station)
        db_session.commit()
        
        # Test limit
        response = client.get("/api/channels/?limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Test skip
        response = client.get("/api/channels/?skip=2&limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] != "Test Radio 0"
        
    def test_get_station_by_id(self, client: TestClient, auth_headers: Dict[str, str], test_station: RadioStation):
        """Test getting station by ID."""
        response = client.get(f"/api/channels/{test_station.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_station.id
        assert data["name"] == test_station.name
        assert data["stream_url"] == test_station.stream_url
        assert data["country"] == test_station.country
        assert data["language"] == test_station.language
        
    def test_get_nonexistent_station(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test getting non-existent station."""
        response = client.get("/api/channels/999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        
    def test_create_station(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test creating a new station."""
        station_data = {
            "name": "New Radio",
            "stream_url": "http://new.stream/audio",
            "country": "SN",
            "language": "fr"
        }
        response = client.post("/api/channels/", headers=auth_headers, json=station_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == station_data["name"]
        assert data["stream_url"] == station_data["stream_url"]
        assert data["country"] == station_data["country"]
        assert data["language"] == station_data["language"]
        
    def test_create_station_validation(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test station creation validation."""
        # Test missing required field
        response = client.post("/api/channels/", headers=auth_headers, json={
            "name": "Invalid Radio"
        })
        assert response.status_code == 422
        
        # Test invalid URL
        response = client.post("/api/channels/", headers=auth_headers, json={
            "name": "Invalid Radio",
            "stream_url": "invalid-url",
            "country": "SN",
            "language": "fr"
        })
        assert response.status_code == 422
        
    def test_update_station(self, client: TestClient, auth_headers: Dict[str, str], test_station: RadioStation):
        """Test updating a station."""
        update_data = {
            "name": "Updated Radio",
            "stream_url": "http://updated.stream/audio"
        }
        response = client.patch(
            f"/api/channels/{test_station.id}",
            headers=auth_headers,
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["stream_url"] == update_data["stream_url"]
        
    def test_update_nonexistent_station(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test updating non-existent station."""
        update_data = {"name": "Updated Radio"}
        response = client.patch(
            "/api/channels/999",
            headers=auth_headers,
            json=update_data
        )
        assert response.status_code == 404
        
    def test_delete_station(self, client: TestClient, auth_headers: Dict[str, str], test_station: RadioStation):
        """Test deleting a station."""
        response = client.delete(
            f"/api/channels/{test_station.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Verify station is deleted
        response = client.get(f"/api/channels/{test_station.id}", headers=auth_headers)
        assert response.status_code == 404
        
    def test_delete_nonexistent_station(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test deleting non-existent station."""
        response = client.delete("/api/channels/999", headers=auth_headers)
        assert response.status_code == 404

class TestDetectionsAPI:
    """Test detections endpoints."""
    
    def test_get_detections(self, client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
        """Test getting list of detections."""
        response = client.get("/api/detections/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert data[0]["id"] == test_detection.id
        assert data[0]["track_id"] == test_detection.track_id
        assert data[0]["station_id"] == test_detection.station_id
        assert data[0]["confidence"] == test_detection.confidence
        assert isinstance(data[0]["detected_at"], str)
        assert isinstance(data[0]["play_duration"], int)
        
    def test_get_detections_with_filters(self, client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
        """Test getting detections with filters."""
        # Test station filter
        params = {
            "station_id": test_detection.station_id,
            "start_date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "confidence_threshold": 0.9
        }
        response = client.get("/api/detections/", headers=auth_headers, params=params)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(d["station_id"] == test_detection.station_id for d in data)
        assert all(d["confidence"] >= 0.9 for d in data)
        
    def test_get_detections_pagination(self, client: TestClient, auth_headers: Dict[str, str], db_session: Session, test_track: Track, test_station: RadioStation):
        """Test detections pagination."""
        # Create multiple detections
        for i in range(5):
            detection = TrackDetection(
                track_id=test_track.id,
                station_id=test_station.id,
                confidence=0.95,
                detected_at=datetime.utcnow() - timedelta(minutes=i),
                play_duration=timedelta(minutes=3),
                is_valid=True
            )
            db_session.add(detection)
        db_session.commit()
        
        # Test limit
        response = client.get("/api/detections/?limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Test offset
        response = client.get("/api/detections/?offset=2&limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] != test_track.id
        
    def test_get_detection_by_id(self, client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
        """Test getting detection by ID."""
        response = client.get(f"/api/detections/{test_detection.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_detection.id
        assert data["track_id"] == test_detection.track_id
        assert data["station_id"] == test_detection.station_id
        assert data["confidence"] == test_detection.confidence
        assert isinstance(data["detected_at"], str)
        assert isinstance(data["play_duration"], int)
        
    def test_get_nonexistent_detection(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test getting non-existent detection."""
        response = client.get("/api/detections/999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        
    def test_create_detection(self, client: TestClient, auth_headers: Dict[str, str], test_track: Track, test_station: RadioStation):
        """Test creating a new detection."""
        detection_data = {
            "track_id": test_track.id,
            "station_id": test_station.id,
            "confidence": 0.95,
            "play_duration": 180,
            "detected_at": datetime.utcnow().isoformat()
        }
        response = client.post("/api/detections/", headers=auth_headers, json=detection_data)
        assert response.status_code == 200
        data = response.json()
        assert data["track_id"] == detection_data["track_id"]
        assert data["station_id"] == detection_data["station_id"]
        assert data["confidence"] == detection_data["confidence"]
        assert data["play_duration"] == detection_data["play_duration"]
        
    def test_create_detection_validation(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test detection creation validation."""
        # Test missing required fields
        response = client.post("/api/detections/", headers=auth_headers, json={})
        assert response.status_code == 422
        
        # Test invalid confidence value
        response = client.post("/api/detections/", headers=auth_headers, json={
            "track_id": 1,
            "station_id": 1,
            "confidence": 2.0,  # Invalid confidence > 1.0
            "play_duration": 180
        })
        assert response.status_code == 422
        
    def test_delete_detection(self, client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
        """Test deleting a detection."""
        response = client.delete(f"/api/detections/{test_detection.id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify detection is deleted
        response = client.get(f"/api/detections/{test_detection.id}", headers=auth_headers)
        assert response.status_code == 404
        
    def test_delete_nonexistent_detection(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test deleting non-existent detection."""
        response = client.delete("/api/detections/999", headers=auth_headers)
        assert response.status_code == 404
        
    def test_get_station_detections(self, client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
        """Test getting detections for a specific station."""
        response = client.get(f"/api/detections/station/{test_detection.station_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(d["station_id"] == test_detection.station_id for d in data)
        
    def test_get_track_detections(self, client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
        """Test getting detections for a specific track."""
        response = client.get(f"/api/detections/track/{test_detection.track_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(d["track_id"] == test_detection.track_id for d in data)
        
    def test_invalid_date_filter(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test detection filtering with invalid dates."""
        params = {
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() - timedelta(days=1)).isoformat()  # End before start
        }
        response = client.get("/api/detections/", headers=auth_headers, params=params)
        assert response.status_code == 422  # Validation error
        assert "end_date" in response.json()["detail"][0]["loc"]

class TestAnalyticsAPI:
    """Test analytics endpoints."""
    
    def test_get_overview(self, client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
        """Test getting analytics overview."""
        response = client.get("/api/analytics/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "totalDetections" in data
        assert "activeStations" in data
        assert "systemHealth" in data
        
    def test_get_artist_stats(self, client: TestClient, auth_headers: Dict[str, str], test_artist: Artist):
        """Test getting artist statistics."""
        response = client.get("/api/analytics/artists", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(stat["artist"] == test_artist.name for stat in data)

class TestReportsAPI:
    """Test reports endpoints."""
    
    def test_generate_report(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test report generation."""
        report_data = {
            "report_type": ReportType.COMPREHENSIVE.value,
            "format": ReportFormat.PDF.value,
            "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "include_graphs": True
        }
        response = client.post("/api/reports/generate", headers=auth_headers, json=report_data)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "success"
        
    def test_get_report_list(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test getting list of reports."""
        response = client.get("/api/reports/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

def test_api_error_handling(client: TestClient, auth_headers: Dict[str, str]):
    """Test API error handling."""
    # Test 404
    response = client.get("/api/nonexistent", headers=auth_headers)
    assert response.status_code == 404
    
    # Test 422 (validation error)
    response = client.post("/api/channels/", headers=auth_headers, json={})
    assert response.status_code == 422
    
    # Test 500 (server error)
    with pytest.raises(Exception):
        client.get("/api/channels/error", headers=auth_headers) 