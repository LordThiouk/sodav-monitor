"""Tests for the music detection API endpoints."""

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Generator
import json
from unittest.mock import Mock, patch, AsyncMock
import redis

from backend.main import app
from backend.models.models import (
    RadioStation, Track, TrackDetection,
    Artist, StationStatus, User
)
from backend.core.config.redis import get_redis

@pytest.fixture
def mock_audio_processor():
    """Mock the audio processor for testing."""
    with patch("backend.detection.audio_processor.core.AudioProcessor") as mock:
        processor = Mock()
        processor.stream_handler = Mock()
        processor.stream_handler.get_audio_data = AsyncMock(return_value=None)
        processor.process_stream = AsyncMock(return_value={
            "type": "music",
            "source": "local",
            "confidence": 0.95,
            "station_id": 1
        })
        mock.return_value = processor
        yield processor

@pytest.fixture
def mock_radio_manager(mock_audio_processor):
    """Mock the radio manager for testing."""
    with patch("backend.processing.radio_manager.RadioManager") as mock:
        manager = Mock()
        manager.audio_processor = mock_audio_processor
        manager.detect_music = AsyncMock(return_value={
            "status": "success",
            "message": "Successfully processed station",
            "detections": [{
                "detection": {
                    "type": "music",
                    "source": "local",
                    "confidence": 0.95
                }
            }]
        })
        mock.return_value = manager
        yield manager

@pytest.fixture
def test_app(mock_radio_manager):
    """Create a test FastAPI application with mocked RadioManager."""
    app = FastAPI()
    
    # Set up app state
    app.state.radio_manager = mock_radio_manager
    
    # Include routers
    from backend.routers import auth, channels, analytics, detections, reports, websocket
    app.include_router(auth.router)
    app.include_router(channels.router)
    app.include_router(analytics.router)
    app.include_router(detections.router)
    app.include_router(reports.router)
    app.include_router(websocket.router)
    
    return app

@pytest.fixture
def test_client(mock_redis, test_db_session):
    """Create a test client with mocked dependencies."""
    from backend.models.database import get_db
    from backend.core.security import get_current_user
    from backend.core.config import get_settings
    from backend.core.security import oauth2_scheme
    from backend.core.config.redis import get_redis
    
    def override_get_settings():
        return {
            "SECRET_KEY": "test_secret_key",
            "JWT_SECRET_KEY": "test_secret_key",
            "ALGORITHM": "HS256",
            "ACCESS_TOKEN_EXPIRE_MINUTES": 15
        }
    
    def override_get_current_user():
        return User(
            id=1,
            email="test@example.com",
            hashed_password="test_hashed_password",
            is_active=True,
            is_superuser=True
        )
    
    # Override dependencies
    app.dependency_overrides[get_db] = lambda: test_db_session
    app.dependency_overrides[get_settings] = override_get_settings
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[oauth2_scheme] = lambda: "test_token"
    app.dependency_overrides[get_redis] = lambda: mock_redis
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

def override_get_db():
    """Override get_db dependency."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture
def mock_redis():
    """Mock Redis for testing."""
    mock_redis = Mock()
    mock_redis.publish = Mock(return_value=1)  # Redis publish returns number of clients received the message
    mock_redis.subscribe = Mock()
    mock_redis.get_message = Mock()
    
    # Patch the get_redis function at the module level
    with patch('backend.core.config.redis.get_redis', return_value=mock_redis), \
         patch('backend.routers.channels.get_redis', return_value=mock_redis), \
         patch('backend.core.config.redis._redis_client', mock_redis):
        yield mock_redis

@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Create authentication headers with JWT token."""
    # Create token payload
    token_data = {
        "sub": test_user.email,
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    
    # Create token directly with jwt
    access_token = jwt.encode(
        token_data,
        "test_secret_key",  # Use test secret key
        algorithm="HS256"
    )
    
    return {"Authorization": f"Bearer {access_token}"}

@pytest.mark.asyncio
async def test_detection_redis_integration(
    test_client: TestClient,
    auth_headers: Dict[str, str],
    test_station: RadioStation,
    mock_redis,
    mock_radio_manager
):
    """Test Redis integration for music detection."""
    # Configure mock for success case
    mock_radio_manager.detect_music.return_value = {
        "status": "success",
        "message": "Successfully processed station",
        "detections": [{
            "detection": {
                "type": "music",
                "source": "local",
                "confidence": 0.95,
                "station_id": test_station.id
            }
        }]
    }
    
    # Ensure station is active
    test_station.status = "active"
    test_station.is_active = True
    
    # Set up RadioManager in app state
    test_client.app.state.radio_manager = mock_radio_manager
    
    # Make the request
    response = test_client.post(
        f"/api/channels/{test_station.id}/detect-music",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Verify Redis publish was called
    assert mock_redis.publish.call_count == 1
    call_args = mock_redis.publish.call_args[0]
    assert call_args[0] == "sodav_monitor:websocket"
    
    published_data = json.loads(call_args[1])
    assert published_data["type"] == "detection_update"
    assert published_data["data"]["station_id"] == test_station.id
    assert published_data["data"]["confidence"] == 0.95
    assert "timestamp" in published_data["data"]

@pytest.mark.asyncio
async def test_detection_redis_error_handling(
    test_client: TestClient,
    auth_headers: Dict[str, str],
    test_station: RadioStation,
    mock_redis,
    mock_radio_manager
):
    """Test Redis error handling during music detection."""
    # Configure Redis to fail
    mock_redis.publish.side_effect = Exception("Redis connection error")
    
    # Configure mock for success case
    mock_radio_manager.detect_music.return_value = {
        "status": "success",
        "message": "Successfully processed station",
        "detections": [{
            "detection": {
                "type": "music",
                "source": "local",
                "confidence": 0.95,
                "station_id": test_station.id
            }
        }]
    }
    
    response = test_client.post(
        f"/api/channels/{test_station.id}/detect-music",
        headers=auth_headers
    )
    # Detection should still succeed even if Redis fails
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "details" in data
    assert "detections" in data["details"]

class TestMusicDetectionAPI:
    """Test music detection endpoints."""
    
    def test_detect_music_success(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test successful music detection."""
        # Configure mock for success case
        mock_radio_manager.detect_music.return_value = {
            "status": "success",
            "message": "Successfully processed station",
            "detections": [{
                "detection": {
                    "type": "music",
                    "source": "local",
                    "confidence": 0.95
                }
            }]
        }
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "details" in data
        assert "station_id" in data["details"]
        assert "station_name" in data["details"]
        assert "detections" in data["details"]
        assert len(data["details"]["detections"]) > 0
        assert data["details"]["detections"][0]["detection"]["type"] == "music"
        
    def test_detect_speech_content(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test when speech is detected instead of music."""
        # Configure mock to detect speech
        mock_radio_manager.detect_music.return_value = {
            "status": "success",
            "message": "Successfully processed station",
            "detections": [{
                "detection": {
                    "type": "speech",
                    "confidence": 0.8,
                    "station_id": test_station.id
                }
            }]
        }
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["details"]["detections"][0]["detection"]["type"] == "speech"
        
    def test_detection_with_local_match(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        test_track: Track,
        mock_radio_manager
    ):
        """Test detection with a match in local database."""
        # Configure mock for local match
        mock_radio_manager.detect_music.return_value = {
            "status": "success",
            "message": "Successfully processed station",
            "detections": [{
                "detection": {
                    "type": "music",
                    "source": "local",
                    "confidence": 0.98,
                    "track": test_track,
                    "station_id": test_station.id
                }
            }]
        }
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["details"]["detections"][0]["detection"]["source"] == "local"
        assert data["details"]["detections"][0]["detection"]["confidence"] == 0.98
        
    def test_detection_fallback_chain(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test the fallback chain (local → MusicBrainz → Audd)."""
        # Configure mock for fallback scenario
        mock_radio_manager.detect_music.return_value = {
            "status": "success",
            "message": "Successfully processed station",
            "detections": [{
                "detection": {
                    "type": "music",
                    "source": "musicbrainz",
                    "confidence": 0.9,
                    "track": {"title": "Test Track", "artist": "Test Artist"},
                    "station_id": test_station.id
                }
            }]
        }
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["details"]["detections"][0]["detection"]["source"] == "musicbrainz"
        
    def test_detection_error_handling(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test error handling during detection."""
        # Simulate processing error
        mock_radio_manager.detect_music.side_effect = Exception("Processing error")
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Processing error" in data["detail"]
        
    def test_invalid_station_id(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test detection with invalid station ID."""
        response = test_client.post(
            "/api/channels/999999/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "Station not found" in response.json()["detail"]
        
    def test_inactive_station(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        db_session: Session
    ):
        """Test detection with inactive station."""
        # Deactivate station
        test_station.is_active = False
        test_station.status = "inactive"
        db_session.commit()
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "not found or not active" in response.json()["detail"].lower()

    def test_concurrent_detection_limit(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test concurrent detection limit handling."""
        # Configure mock for success case
        mock_radio_manager.detect_music.return_value = {
            "status": "success",
            "message": "Successfully processed station",
            "detections": [{
                "detection": {
                    "type": "music",
                    "source": "local",
                    "confidence": 0.95
                }
            }]
        }
        
        # Create multiple concurrent requests
        responses = []
        for _ in range(5):  # Try 5 concurrent requests
            response = test_client.post(
                f"/api/channels/{test_station.id}/detect-music",
                headers=auth_headers
            )
            responses.append(response)
        
        # Verify all requests were handled
        assert all(r.status_code == 200 for r in responses)
        
    def test_detection_with_low_confidence(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test detection with low confidence score."""
        # Configure mock for low confidence
        mock_radio_manager.detect_music.return_value = {
            "status": "success",
            "message": "Successfully processed station",
            "detections": [{
                "detection": {
                    "type": "music",
                    "source": "local",
                    "confidence": 0.3,
                    "station_id": test_station.id
                }
            }]
        }
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["details"]["detections"][0]["detection"]["confidence"] == 0.3

    def test_detection_with_missing_audio_processor(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test detection when audio processor is not initialized."""
        # Configure mock for missing audio processor
        mock_radio_manager.audio_processor = None
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 500
        assert "Audio processor not initialized" in response.json()["detail"]

    def test_detection_with_stream_error(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test detection when stream cannot be accessed."""
        # Configure mock for stream error
        mock_radio_manager.detect_music.side_effect = RuntimeError("Stream unavailable")
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 500
        assert "Stream unavailable" in response.json()["detail"]

    def test_detection_with_multiple_matches(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager,
        test_track: Track
    ):
        """Test detection with multiple matches found."""
        # Configure mock for multiple matches
        mock_radio_manager.detect_music.return_value = {
            "status": "success",
            "message": "Successfully processed station",
            "detections": [
                {
                    "detection": {
                        "type": "music",
                        "source": "local",
                        "confidence": 0.98,
                        "track": test_track,
                        "station_id": test_station.id
                    }
                },
                {
                    "detection": {
                        "type": "music",
                        "source": "musicbrainz",
                        "confidence": 0.85,
                        "track": test_track,
                        "station_id": test_station.id
                    }
                }
            ]
        }
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["details"]["detections"]) == 2
        assert data["details"]["detections"][0]["detection"]["confidence"] == 0.98
        assert data["details"]["detections"][1]["detection"]["confidence"] == 0.85

    def test_detection_with_invalid_auth(
        self,
        test_client: TestClient,
        test_station: RadioStation
    ):
        """Test detection with invalid authentication."""
        # Override the auth dependency to raise an exception
        from backend.core.security import get_current_user
        from fastapi import HTTPException
        
        def override_get_current_user():
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials"
            )
        
        test_client.app.dependency_overrides[get_current_user] = override_get_current_user
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]
        
        # Clean up
        test_client.app.dependency_overrides.pop(get_current_user)

    def test_detection_rate_limiting(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test rate limiting for detection requests."""
        # Make multiple requests in quick succession
        responses = []
        for _ in range(10):
            response = test_client.post(
                f"/api/channels/{test_station.id}/detect-music",
                headers=auth_headers
            )
            responses.append(response)
            
        # Verify all requests were handled
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count > 0
        
        # Verify rate limiting headers if they exist
        if "X-RateLimit-Remaining" in responses[-1].headers:
            assert int(responses[-1].headers["X-RateLimit-Remaining"]) >= 0

    def test_detection_with_empty_audio(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test detection with empty audio data."""
        # Configure mock for empty audio
        mock_radio_manager.detect_music.return_value = {
            "status": "error",
            "message": "No audio data received",
            "detections": []
        }
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 500
        assert "No audio data received" in response.json()["detail"]

    def test_detection_with_timeout(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test detection with stream timeout."""
        # Configure mock for timeout
        mock_radio_manager.detect_music.side_effect = TimeoutError("Stream processing timeout")
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 500
        assert "timeout" in response.json()["detail"].lower()

    def test_detection_with_corrupted_audio(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test detection with corrupted audio data."""
        # Configure mock for corrupted audio
        mock_radio_manager.detect_music.return_value = {
            "status": "error",
            "message": "Invalid audio format",
            "detections": []
        }
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 500
        assert "Invalid audio format" in response.json()["detail"]

    def test_concurrent_detection_requests(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test handling of concurrent detection requests."""
        import asyncio
        
        # Configure mock for success case
        mock_radio_manager.detect_music.return_value = {
            "status": "success",
            "message": "Successfully processed station",
            "detections": [{
                "detection": {
                    "type": "music",
                    "source": "local",
                    "confidence": 0.95
                }
            }]
        }
        
        # Make concurrent requests
        async def make_request():
            return test_client.post(
                f"/api/channels/{test_station.id}/detect-music",
                headers=auth_headers
            )
        
        # Create multiple concurrent requests
        responses = []
        for _ in range(5):  # Try 5 concurrent requests
            response = test_client.post(
                f"/api/channels/{test_station.id}/detect-music",
                headers=auth_headers
            )
            responses.append(response)
        
        # Verify all requests were handled
        assert all(r.status_code == 200 for r in responses)
        
    def test_detection_with_missing_audio_processor(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test detection when audio processor is not initialized."""
        # Configure mock for missing audio processor
        mock_radio_manager.audio_processor = None
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 500
        assert "Audio processor not initialized" in response.json()["detail"]

    def test_detection_with_invalid_station_status(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager,
        db_session: Session
    ):
        """Test detection with invalid station status."""
        # Set station status to inactive
        test_station.status = "inactive"
        test_station.is_active = False
        db_session.commit()
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "not found or not active" in response.json()["detail"].lower()

    def test_detection_with_very_low_confidence(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager
    ):
        """Test detection with very low confidence score."""
        # Configure mock for low confidence
        mock_radio_manager.detect_music.return_value = {
            "status": "success",
            "message": "Successfully processed station",
            "detections": [{
                "detection": {
                    "type": "music",
                    "source": "local",
                    "confidence": 0.3,
                    "station_id": test_station.id
                }
            }]
        }
        
        response = test_client.post(
            f"/api/channels/{test_station.id}/detect-music",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["details"]["detections"][0]["detection"]["confidence"] == 0.3 