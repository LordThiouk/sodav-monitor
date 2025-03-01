"""Tests for the API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Generator
import jwt
from unittest.mock import patch
from httpx import ASGITransport
from fastapi import Depends

from backend.models.models import (
    User, RadioStation, Track, TrackDetection,
    Artist, StationStatus, ReportType, ReportFormat
)
from backend.core.security import create_access_token
from backend.core.config import get_settings
from backend.models.database import get_db
from backend.main import app
from backend.tests.conftest import mock_settings
from backend.core.security import get_current_user
from backend.core.security import oauth2_scheme

# Test settings
TEST_SETTINGS = {
    'SECRET_KEY': "test_secret_key",
    'ALGORITHM': "HS256",
    'ACCESS_TOKEN_EXPIRE_MINUTES': 15
}

@pytest.fixture(scope="function")
def client(test_app, test_db) -> Generator:
    """Test client fixture."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    def override_get_settings():
        return TEST_SETTINGS
    
    def override_get_current_user():
        # Create a test user if it doesn't exist
        user = test_db.query(User).filter(User.email == "test@example.com").first()
        if not user:
            user = User(
                username="testuser",
                email="test@example.com",
                is_active=True,
                created_at=datetime.utcnow()
            )
            user.set_password("testpass")
            test_db.add(user)
            test_db.commit()
            test_db.refresh(user)
        return user
    
    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_settings] = override_get_settings
    test_app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(test_app) as client:
        yield client
    
    test_app.dependency_overrides.clear()

@pytest.fixture
def test_user(test_db: Session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        is_active=True
    )
    user.set_password("testpass")
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Create authentication headers."""
    access_token = create_access_token(
        data={"sub": test_user.email},
        settings_override=TEST_SETTINGS
    )
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
def test_station(test_db: Session) -> RadioStation:
    """Create a test radio station."""
    station = RadioStation(
        name="Test Radio",
        stream_url="http://test.stream/audio",
        region="SN",
        language="fr",
        type="radio",
        is_active=True,
        status=StationStatus.ACTIVE.value,
        last_check=datetime.utcnow()
    )
    test_db.add(station)
    test_db.commit()
    test_db.refresh(station)
    return station

@pytest.fixture
def test_artist(test_db: Session) -> Artist:
    """Create a test artist."""
    artist = Artist(
        name="Test Artist",
        country="SN",
        label="Test Label"
    )
    test_db.add(artist)
    test_db.commit()
    return artist

@pytest.fixture
def test_track(test_db: Session, test_artist: Artist) -> Track:
    """Create a test track."""
    track = Track(
        title="Test Track",
        artist_id=test_artist.id,
        duration=timedelta(minutes=3),
        fingerprint="test_fingerprint"
    )
    test_db.add(track)
    test_db.commit()
    return track

@pytest.fixture
def test_detection(test_db: Session, test_track: Track, test_station: RadioStation) -> TrackDetection:
    """Create a test detection."""
    detection = TrackDetection(
        track_id=test_track.id,
        station_id=test_station.id,
        confidence=0.95,
        detected_at=datetime.utcnow(),
        play_duration=timedelta(minutes=3),
        is_valid=True
    )
    test_db.add(detection)
    test_db.commit()
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
        assert "access_token" in response.json()
        
    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/auth/login",
            data={"username": "wrong@email.com", "password": "wrongpass"}
        )
        assert response.status_code == 401
        
    def test_login_inactive_user(self, client: TestClient, test_user: User, test_db: Session):
        """Test login with inactive user."""
        test_user.is_active = False
        test_db.commit()
        
        response = client.post(
            "/api/auth/login",
            data={"username": test_user.email, "password": "testpass"}
        )
        assert response.status_code == 401
        
    def test_create_user_success(self, client: TestClient):
        """Test successful user creation."""
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123"
        }
        response = client.post("/api/auth/users", json=user_data)
        assert response.status_code == 200
        
    def test_create_user_duplicate_email(self, client: TestClient, test_user: User):
        """Test user creation with duplicate email."""
        user_data = {
            "username": "another",
            "email": test_user.email,
            "password": "pass123"
        }
        response = client.post("/api/auth/users", json=user_data)
        assert response.status_code == 400
        
    def test_forgot_password(self, client: TestClient, test_user: User):
        """Test password reset request."""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": test_user.email}
        )
        assert response.status_code == 200
        
    def test_forgot_password_invalid_email(self, client: TestClient):
        """Test password reset with invalid email."""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )
        assert response.status_code == 404
        
    def test_reset_password(self, client: TestClient, test_user: User, test_db: Session):
        """Test password reset."""
        # First request password reset
        client.post(
            "/api/auth/forgot-password",
            json={"email": test_user.email}
        )
        
        # Get the reset token from the database
        test_db.refresh(test_user)
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
        
    def test_protected_route_with_expired_token(self, client: TestClient, test_user: User, test_db: Session):
        """Test accessing protected route with expired token."""
        # Create expired token (30 minutes in the past)
        settings_override = dict(TEST_SETTINGS, ACCESS_TOKEN_EXPIRE_MINUTES=-30)
        expired_token = create_access_token(
            data={"sub": test_user.email},
            settings_override=settings_override
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        # Override get_current_user dependency for this test
        async def override_get_current_user(token: str = Depends(oauth2_scheme)):
            return await get_current_user(db=test_db, token=token, settings_override=settings_override)
            
        client.app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            response = client.get("/api/channels/", headers=headers)
            assert response.status_code == 401
            assert response.json()["detail"] == "Token has expired"
        finally:
            # Clean up the override
            del client.app.dependency_overrides[get_current_user]

class TestChannelsAPI:
    """Test channels endpoints."""
    
    def test_get_stations(self, client: TestClient, auth_headers: Dict[str, str], test_station: RadioStation):
        """Test getting list of stations."""
        response = client.get("/api/channels/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert response.json()[0]["name"] == test_station.name
        
    def test_get_stations_with_filters(self, client: TestClient, auth_headers: Dict[str, str], test_db: Session):
        """Test getting stations with filters."""
        # Create a test station directly in the test
        station = RadioStation(
            name="Test Radio",
            stream_url="http://test.stream/audio",
            country="SN",
            region="Dakar",
            language="fr",
            type="radio",
            status=StationStatus.ACTIVE.value,
            is_active=True,
            last_check=datetime.utcnow()
        )
        test_db.add(station)
        test_db.flush()  # Ensure the station is available in the current transaction
        
        response = client.get(
            "/api/channels/",
            headers=auth_headers,
            params={"country": "SN", "status": StationStatus.ACTIVE.value}
        )
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert response.json()[0]["country"] == "SN"
        assert response.json()[0]["status"] == StationStatus.ACTIVE.value
        
    def test_get_stations_pagination(self, client: TestClient, auth_headers: Dict[str, str], test_db: Session):
        """Test station list pagination."""
        # Create multiple stations
        for i in range(5):
            station = RadioStation(
                name=f"Test Radio {i}",
                stream_url=f"http://test{i}.stream/audio",
                country="SN",
                language="fr",
                is_active=True,
                status=StationStatus.ACTIVE.value,
                last_check=datetime.utcnow()
            )
            test_db.add(station)
        test_db.commit()
        
        response = client.get(
            "/api/channels/",
            headers=auth_headers,
            params={"limit": 2, "offset": 0}
        )
        assert response.status_code == 200
        assert len(response.json()) == 2
        
    def test_get_station_by_id(self, client: TestClient, auth_headers: Dict[str, str], test_station: RadioStation):
        """Test getting a specific station."""
        response = client.get(f"/api/channels/{test_station.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == test_station.name
        assert data["stream_url"] == test_station.stream_url
        
    def test_get_nonexistent_station(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test getting a nonexistent station."""
        response = client.get("/api/channels/999", headers=auth_headers)
        assert response.status_code == 404
        
    def test_create_station(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test station creation."""
        station_data = {
            "station": {
                "name": "New Radio",
                "stream_url": "http://new.stream/audio",
                "country": "SN",
                "region": "Dakar",
                "language": "fr",
                "type": "radio",
                "status": "inactive",
                "is_active": False
            }
        }
        response = client.post("/api/channels/", headers=auth_headers, json=station_data)
        print("Response body:", response.json())
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == station_data["station"]["name"]
        assert data["stream_url"] == station_data["station"]["stream_url"]
        assert data["country"] == station_data["station"]["country"]
        assert data["region"] == station_data["station"]["region"]
        assert data["language"] == station_data["station"]["language"]
        assert data["type"] == station_data["station"]["type"]
        assert data["status"] == station_data["station"]["status"]
        assert data["is_active"] == station_data["station"]["is_active"]
        
    def test_create_station_validation(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test station creation validation."""
        invalid_data = {
            "name": "",  # Empty name
            "stream_url": "not_a_url",  # Invalid URL
            "country": "XXX",  # Invalid country code
            "region": "XXX"  # Invalid region code
        }
        response = client.post("/api/channels/", headers=auth_headers, json=invalid_data)
        assert response.status_code == 422
        
    def test_update_station(self, client: TestClient, auth_headers: Dict[str, str], test_station: RadioStation):
        """Test station update."""
        update_data = {
            "station_update": {
                "name": "Updated Radio",
                "stream_url": "http://updated.stream/audio",
                "country": "SN",
                "region": "Dakar",
                "language": "fr",
                "type": "radio",
                "status": StationStatus.ACTIVE.value,
                "is_active": True
            }
        }
        response = client.put(f"/api/channels/{test_station.id}", headers=auth_headers, json=update_data)
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["station_update"]["name"]
        assert data["stream_url"] == update_data["station_update"]["stream_url"]
        assert data["status"] == update_data["station_update"]["status"]
        assert data["is_active"] == update_data["station_update"]["is_active"]
        
    def test_update_nonexistent_station(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test updating a nonexistent station."""
        update_data = {
            "station_update": {
                "name": "Updated Radio",
                "stream_url": "http://updated.stream/audio",
                "status": StationStatus.ACTIVE.value
            }
        }
        response = client.put("/api/channels/999", headers=auth_headers, json=update_data)
        assert response.status_code == 404
        
    def test_delete_station(self, client: TestClient, auth_headers: Dict[str, str], test_station: RadioStation):
        """Test deleting a station."""
        response = client.delete(f"/api/channels/{test_station.id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify deletion
        response = client.get(f"/api/channels/{test_station.id}", headers=auth_headers)
        assert response.status_code == 404
        
    def test_delete_nonexistent_station(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test deleting a nonexistent station."""
        response = client.delete("/api/channels/999", headers=auth_headers)
        assert response.status_code == 404

class TestDetectionsAPI:
    """Test detection endpoints."""
    
    def test_get_detections(self, client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
        """Test getting list of detections."""
        response = client.get("/api/detections/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["track_id"] == test_detection.track_id
        
    def test_get_detections_with_filters(self, client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
        """Test detections list with filters."""
        response = client.get(
            "/api/detections/",
            headers=auth_headers,
            params={"confidence_min": 0.9}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(d["confidence"] >= 0.9 for d in data)

    def test_get_detections_date_range(self, client: TestClient, auth_headers: Dict[str, str], test_db: Session, test_track: Track, test_station: RadioStation):
        """Test getting detections within a date range."""
        # Create detections with different dates
        dates = [
            datetime.utcnow() - timedelta(days=5),
            datetime.utcnow() - timedelta(days=3),
            datetime.utcnow() - timedelta(days=1)
        ]
        
        for date in dates:
            detection = TrackDetection(
                track_id=test_track.id,
                station_id=test_station.id,
                confidence=0.95,
                detected_at=date,
                play_duration=timedelta(minutes=3),
                is_valid=True
            )
            test_db.add(detection)
        test_db.commit()
        
        # Test date range filter
        start_date = (datetime.utcnow() - timedelta(days=4)).date().isoformat()
        end_date = datetime.utcnow().date().isoformat()
        
        response = client.get(
            "/api/detections/",
            headers=auth_headers,
            params={
                "start_date": start_date,
                "end_date": end_date
            }
        )
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Should only get detections from last 4 days
        
    def test_get_detections_combined_filters(self, client: TestClient, auth_headers: Dict[str, str], test_db: Session, test_track: Track, test_station: RadioStation):
        """Test getting detections with combined filters (confidence, date range, and station)."""
        # Create detections with different confidences and dates
        detections_data = [
            {"confidence": 0.95, "days_ago": 2},
            {"confidence": 0.85, "days_ago": 2},
            {"confidence": 0.75, "days_ago": 1}
        ]
        
        for data in detections_data:
            detection = TrackDetection(
                track_id=test_track.id,
                station_id=test_station.id,
                confidence=data["confidence"],
                detected_at=datetime.utcnow() - timedelta(days=data["days_ago"]),
                play_duration=timedelta(minutes=3),
                is_valid=True
            )
            test_db.add(detection)
        test_db.commit()
        
        # Test combined filters
        start_date = (datetime.utcnow() - timedelta(days=3)).date().isoformat()
        end_date = datetime.utcnow().date().isoformat()
        
        response = client.get(
            "/api/detections/",
            headers=auth_headers,
            params={
                "start_date": start_date,
                "end_date": end_date,
                "confidence_min": 0.9,
                "station_id": test_station.id
            }
        )
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Should only get the detection with 0.95 confidence
        assert data[0]["confidence"] >= 0.9
        assert data[0]["station_id"] == test_station.id
        
    def test_get_detections_pagination(self, client: TestClient, auth_headers: Dict[str, str], test_db: Session, test_track: Track, test_station: RadioStation):
        """Test detections pagination."""
        # Create multiple detections
        for i in range(5):
            detection = TrackDetection(
                track_id=test_track.id,
                station_id=test_station.id,
                confidence=0.95,
                detected_at=datetime.utcnow() - timedelta(hours=i),
                play_duration=timedelta(minutes=3),
                is_valid=True
            )
            test_db.add(detection)
        test_db.commit()
        
        # Test limit
        response = client.get(
            "/api/detections/",
            headers=auth_headers,
            params={"limit": 3}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        
    def test_get_detection_by_id(self, client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
        """Test getting a specific detection."""
        response = client.get(f"/api/detections/{test_detection.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["track_id"] == test_detection.track_id
        assert data["station_id"] == test_detection.station_id
        
    def test_get_nonexistent_detection(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test getting a nonexistent detection."""
        response = client.get("/api/detections/999", headers=auth_headers)
        assert response.status_code == 404
        
    def test_create_detection(self, client: TestClient, auth_headers: Dict[str, str], test_track: Track, test_station: RadioStation):
        """Test detection creation."""
        detection_data = {
            "track_id": test_track.id,
            "station_id": test_station.id,
            "confidence": 0.95,
            "detected_at": datetime.utcnow().isoformat(),
            "play_duration": "PT3M",
            "is_valid": True
        }
        response = client.post("/api/detections/", headers=auth_headers, json=detection_data)
        assert response.status_code == 200
        data = response.json()
        assert data["track_id"] == detection_data["track_id"]
        assert data["station_id"] == detection_data["station_id"]
        
    def test_create_detection_validation(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test detection creation validation."""
        invalid_data = {
            "track_id": 999,  # Nonexistent track
            "station_id": 999,  # Nonexistent station
            "confidence": 2.0  # Invalid confidence value
        }
        response = client.post("/api/detections/", headers=auth_headers, json=invalid_data)
        assert response.status_code == 422
        
    def test_delete_detection(self, client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
        """Test deleting a detection."""
        response = client.delete(f"/api/detections/{test_detection.id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify deletion
        response = client.get(f"/api/detections/{test_detection.id}", headers=auth_headers)
        assert response.status_code == 404
        
    def test_delete_nonexistent_detection(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test deleting a nonexistent detection."""
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
        """Test invalid date filter."""
        response = client.get(
            "/api/detections/",
            headers=auth_headers,
            params={"start_date": "invalid-date"}
        )
        assert response.status_code == 422

class TestAnalyticsAPI:
    """Test analytics endpoints."""
    
    def test_get_overview(self, client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
        """Test getting analytics overview."""
        response = client.get("/api/analytics/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_detections" in data
        assert "total_stations" in data
        assert "total_tracks" in data
        
    def test_get_artist_stats(self, client: TestClient, auth_headers: Dict[str, str], test_artist: Artist):
        """Test getting artist statistics."""
        response = client.get(f"/api/analytics/artists/{test_artist.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["artist_id"] == test_artist.id
        assert "total_plays" in data
        assert "total_play_time" in data

class TestReportsAPI:
    """Test report endpoints."""
    
    def test_generate_report(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test report generation."""
        report_data = {
            "report_type": ReportType.DAILY.value,
            "format": ReportFormat.CSV.value,
            "start_date": datetime.utcnow().date().isoformat(),
            "end_date": datetime.utcnow().date().isoformat()
        }
        response = client.post("/api/reports/generate", headers=auth_headers, json=report_data)
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert "status" in data
        
    def test_get_report_list(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test getting list of reports."""
        response = client.get("/api/reports/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

def test_api_error_handling(client: TestClient, auth_headers: Dict[str, str]):
    """Test API error handling."""
    # Test invalid JSON
    response = client.post(
        "/api/channels/",
        headers=auth_headers,
        data="invalid json"
    )
    assert response.status_code == 422
    
    # Test method not allowed
    response = client.put("/api/auth/login")
    assert response.status_code == 405 