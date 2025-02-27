"""Test configuration for the SODAV Monitor project."""

import pytest
from unittest.mock import Mock, MagicMock
import os
from typing import Generator
from sqlalchemy.orm import Session
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt

# Mock settings before any imports
mock_settings = MagicMock()
mock_settings.SECRET_KEY = "test_secret_key"
mock_settings.ALGORITHM = "HS256"
mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15
mock_settings.DATABASE_URL = "sqlite:///./test.db"
mock_settings.REDIS_HOST = "localhost"
mock_settings.REDIS_PORT = 6379
mock_settings.REDIS_DB = 0
mock_settings.REDIS_PASSWORD = None
mock_settings.MUSICBRAINZ_API_KEY = "test_key"
mock_settings.ACOUSTID_API_KEY = "test_acoustid_key"
mock_settings.AUDD_API_KEY = "test_audd_key"
mock_settings.MUSICBRAINZ_APP_NAME = "SODAV Monitor Test"
mock_settings.MUSICBRAINZ_VERSION = "1.0"
mock_settings.MUSICBRAINZ_CONTACT = "test@sodav.sn"
mock_settings.LOG_LEVEL = "INFO"
mock_settings.LOG_FILE = "logs/test.log"
mock_settings.DETECTION_INTERVAL = 10
mock_settings.CONFIDENCE_THRESHOLD = 50.0
mock_settings.MAX_FAILURES = 3
mock_settings.RESPONSE_TIMEOUT = 10
mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.8
mock_settings.ACOUSTID_CONFIDENCE_THRESHOLD = 0.7
mock_settings.AUDD_CONFIDENCE_THRESHOLD = 0.6
mock_settings.LOCAL_CONFIDENCE_THRESHOLD = 0.8

import pytest
from unittest.mock import patch

# Apply the mock settings
with patch('backend.core.config.settings.get_settings', return_value=mock_settings):
    from backend.models.database import get_db, Base, engine
    from backend.detection.audio_processor import AudioProcessor, FeatureExtractor, TrackManager, StationMonitor
    from backend.models.models import User, RadioStation, Track, TrackDetection, ReportType, ReportFormat

@pytest.fixture(scope="session")
def db() -> Generator[Session, None, None]:
    """Create a test database session."""
    # Create test database
    Base.metadata.create_all(bind=engine)
    
    # Get database session
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()
        # Clean up test database
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session

@pytest.fixture
def audio_processor(db):
    """Create an AudioProcessor instance for testing."""
    return AudioProcessor(db)

@pytest.fixture
def feature_extractor():
    """Create a FeatureExtractor instance for testing."""
    return FeatureExtractor()

@pytest.fixture
def track_manager(db):
    """Create a TrackManager instance for testing."""
    return TrackManager(db)

@pytest.fixture
def station_monitor(db):
    """Create a StationMonitor instance for testing."""
    return StationMonitor(db)

@pytest.fixture(scope="session")
def app():
    """Crée une instance FastAPI pour les tests."""
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(channels.router, prefix="/api/stations", tags=["stations"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
    app.include_router(detections.router, prefix="/api/detections", tags=["detections"])
    app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
    return app

@pytest.fixture(scope="session")
def test_client(app):
    """Crée un client de test FastAPI."""
    return TestClient(app)

@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        username="test_user",
        email="test@example.com",
        role="admin"
    )
    user.set_password("test_password")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def auth_token(test_user):
    """Create a test JWT token."""
    token_data = {
        "sub": test_user.username,
        "role": test_user.role,
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    return jwt.encode(token_data, mock_settings.SECRET_KEY, algorithm=mock_settings.ALGORITHM)

@pytest.fixture
def auth_headers(auth_token):
    """Create authentication headers for tests."""
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture
def sample_station(db_session):
    """Create a test radio station."""
    station = RadioStation(
        name="Radio Test",
        stream_url="http://test.stream/live",
        status="active"
    )
    db_session.add(station)
    db_session.commit()
    return station

@pytest.fixture
def sample_track(db_session):
    """Create a test track."""
    track = Track(
        title="Test Song",
        artist="Test Artist",
        duration=180.0,
        fingerprint="test_fingerprint"
    )
    db_session.add(track)
    db_session.commit()
    return track

@pytest.fixture
def sample_detection(db_session, sample_station, sample_track):
    """Create a test detection."""
    detection = TrackDetection(
        station_id=sample_station.id,
        track_id=sample_track.id,
        confidence=0.95,
        detected_at=datetime.utcnow()
    )
    db_session.add(detection)
    db_session.commit()
    return detection

@pytest.fixture
def sample_report_data():
    """Create test report data."""
    return {
        "start_date": datetime.utcnow() - timedelta(days=7),
        "end_date": datetime.utcnow(),
        "type": ReportType.COMPREHENSIVE,
        "format": ReportFormat.PDF,
        "include_graphs": True,
        "language": "fr"
    }

@pytest.fixture
def report_generator(db_session):
    """Crée un générateur de rapports de test."""
    stats_manager = StatsManager(db_session)
    return ReportGenerator(db_session, stats_manager) 