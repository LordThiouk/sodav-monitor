"""Test configuration for the SODAV Monitor project."""

import pytest
from unittest.mock import Mock, MagicMock, patch
import os
from typing import Generator, Dict, List
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt
import numpy as np
from unittest.mock import AsyncMock
from fastapi.middleware.cors import CORSMiddleware
import uuid
import asyncio
import pytest_asyncio
import logging

from backend.models.database import Base, get_db, TestingSessionLocal, test_engine
from backend.models.models import (
    User, RadioStation, Track, TrackDetection, ReportType, ReportFormat,
    Artist, StationStatus, ArtistStats, TrackStats, Report, ReportSubscription,
    DetectionHourly, AnalyticsData, DetectionDaily, DetectionMonthly, StationStats,
    TrackDaily, TrackMonthly, ArtistDaily, ArtistMonthly, StationTrackStats, StationHealth
)
from backend.routers import auth, channels, analytics, detections, reports, websocket
from backend.detection.audio_processor.core import AudioProcessor
from backend.core.config import get_settings, settings
from backend.core.security import get_current_user, oauth2_scheme, create_access_token
from backend.detection.audio_processor.stream_handler import StreamHandler
from backend.analytics.stats_manager import StatsManager
from backend.main import app
from backend.utils.auth.auth import get_password_hash

# Test configuration constants
TEST_SECRET_KEY = "test_secret_key"
TEST_ALGORITHM = "HS256"
TEST_TOKEN_EXPIRE_MINUTES = 15

# Mock settings before any imports
mock_settings = {
    "SECRET_KEY": TEST_SECRET_KEY,
    "JWT_SECRET_KEY": TEST_SECRET_KEY,
    "ALGORITHM": TEST_ALGORITHM,
    "ACCESS_TOKEN_EXPIRE_MINUTES": TEST_TOKEN_EXPIRE_MINUTES,
    "DATABASE_URL": "postgresql://sodav:sodav123@localhost:5432/sodav_test",  # Use PostgreSQL for tests
    "REDIS_HOST": "localhost",
    "REDIS_PORT": 6379,
    "REDIS_DB": 0,
    "REDIS_PASSWORD": None,
    "MUSICBRAINZ_API_KEY": "test_key",
    "ACOUSTID_API_KEY": "test_acoustid_key",
    "AUDD_API_KEY": "test_audd_key",
    "MUSICBRAINZ_APP_NAME": "SODAV Monitor Test",
    "MUSICBRAINZ_VERSION": "1.0",
    "MUSICBRAINZ_CONTACT": "test@sodav.sn",
    "LOG_LEVEL": "INFO",
    "LOG_FILE": "logs/test.log",
    "DETECTION_INTERVAL": 10,
    "CONFIDENCE_THRESHOLD": 50.0,
    "MAX_FAILURES": 3,
    "RESPONSE_TIMEOUT": 10,
    "MIN_CONFIDENCE_THRESHOLD": 0.8,
    "ACOUSTID_CONFIDENCE_THRESHOLD": 0.7,
    "AUDD_CONFIDENCE_THRESHOLD": 0.6,
    "LOCAL_CONFIDENCE_THRESHOLD": 0.8
}

# Override settings for testing
@pytest.fixture(autouse=True)
def override_settings():
    with patch("backend.core.config.get_settings") as mock_get_settings:
        mock_get_settings.return_value = mock_settings
        yield mock_settings

# Create test database engine with PostgreSQL settings
test_engine = create_engine(
    mock_settings["DATABASE_URL"],
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "connect_timeout": 30,
        "application_name": "sodav_monitor_test"
    }
)

# Create test session factory
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)

@pytest.fixture(scope="function")
def db_session() -> Generator:
    """Create a test database session."""
    try:
        # Drop all tables first to ensure clean state
        Base.metadata.drop_all(bind=test_engine)
        
        # Create all tables
        Base.metadata.create_all(bind=test_engine)
        
        # Create a new session
        session = TestingSessionLocal()
        
        # Override get_db dependency
        app.dependency_overrides[get_db] = lambda: session
        
        yield session
    except Exception as e:
        logger.error(f"Error setting up test database: {e}")
        raise
    finally:
        session.close()
        # Clean up by dropping all tables
        Base.metadata.drop_all(bind=test_engine)
        # Remove dependency override
        app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_user(db_session: Session) -> User:
    """Create a test user."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"  # Ensure unique email
    password_hash = get_password_hash("testpassword123")
    user = User(
        username=email,  # Use email as username
        email=email,
        password_hash=password_hash,
        is_active=True,
        role="admin",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> Dict[str, str]:
    """Create authentication headers for test user."""
    settings_override = {
        "SECRET_KEY": TEST_SECRET_KEY,
        "JWT_SECRET_KEY": TEST_SECRET_KEY,
        "ALGORITHM": TEST_ALGORITHM,
        "ACCESS_TOKEN_EXPIRE_MINUTES": TEST_TOKEN_EXPIRE_MINUTES
    }
    
    # Create a valid access token for the test user
    access_token = create_access_token(
        data={"sub": test_user.email},
        expires_delta=timedelta(minutes=TEST_TOKEN_EXPIRE_MINUTES),
        settings_override=settings_override
    )
    
    # Return the headers with the Bearer token
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture(scope="function")
def test_client(db_session: Session, test_user: User, auth_headers: Dict[str, str]) -> TestClient:
    """Create a test client."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_user():
        return test_user

    def override_oauth2_scheme():
        return auth_headers["Authorization"].split(" ")[1]

    def override_get_settings():
        return {
            "SECRET_KEY": TEST_SECRET_KEY,
            "JWT_SECRET_KEY": TEST_SECRET_KEY,
            "ALGORITHM": TEST_ALGORITHM,
            "ACCESS_TOKEN_EXPIRE_MINUTES": TEST_TOKEN_EXPIRE_MINUTES,
            "DATABASE_URL": "postgresql://sodav:sodav123@localhost:5432/sodav_test",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": 6379,
            "REDIS_DB": 0,
            "REDIS_PASSWORD": None,
            "MUSICBRAINZ_API_KEY": "test_key",
            "ACOUSTID_API_KEY": "test_acoustid_key",
            "AUDD_API_KEY": "test_audd_key",
            "MUSICBRAINZ_APP_NAME": "SODAV Monitor Test",
            "MUSICBRAINZ_VERSION": "1.0",
            "MUSICBRAINZ_CONTACT": "test@sodav.sn",
            "LOG_LEVEL": "INFO",
            "LOG_FILE": "logs/test.log",
            "DETECTION_INTERVAL": 10,
            "CONFIDENCE_THRESHOLD": 50.0,
            "MAX_FAILURES": 3,
            "RESPONSE_TIMEOUT": 10,
            "MIN_CONFIDENCE_THRESHOLD": 0.8,
            "ACOUSTID_CONFIDENCE_THRESHOLD": 0.7,
            "AUDD_CONFIDENCE_THRESHOLD": 0.6,
            "LOCAL_CONFIDENCE_THRESHOLD": 0.8
        }

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[oauth2_scheme] = override_oauth2_scheme
    app.dependency_overrides[get_settings] = override_get_settings

    with TestClient(app) as client:
        client.headers.update(auth_headers)
        yield client

    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def test_station(db_session: Session) -> RadioStation:
    """Create a test radio station."""
    station = RadioStation(
        name="Test Station",
        stream_url="http://test.stream/audio",
        country="SN",
        language="fr",
        region="Dakar",
        type="radio",
        status="active",
        is_active=True,
        last_check=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(station)
    db_session.commit()
    db_session.refresh(station)
    return station

@pytest.fixture(scope="function")
def test_artist(db_session: Session) -> Artist:
    """Create a test artist."""
    artist = Artist(
        name=f"Test Artist {uuid.uuid4().hex[:8]}",  # Ensure unique name
        country="SN",
        region="Dakar",
        type="musician",
        label="Test Label",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        total_play_time=timedelta(hours=1),
        total_plays=100,
        external_ids={"musicbrainz": "test_id"}
    )
    db_session.add(artist)
    db_session.commit()
    db_session.refresh(artist)
    return artist

@pytest.fixture(scope="function")
def test_track(db_session: Session, test_artist: Artist) -> Track:
    """Create a test track."""
    track = Track(
        title=f"Test Track {uuid.uuid4().hex[:8]}",  # Ensure unique title
        artist_id=test_artist.id,
        isrc="USABC1234567",
        label="Test Label",
        album="Test Album",
        duration=timedelta(minutes=3),
        fingerprint=f"test_fingerprint_{uuid.uuid4().hex}",  # Ensure unique fingerprint
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(track)
    db_session.commit()
    db_session.refresh(track)
    return track

@pytest.fixture(scope="function")
def test_report(db_session: Session, test_user: User) -> Report:
    """Create a test report."""
    report = Report(
        title="Test Report",
        type="daily",  # String type as defined in the model
        report_type="daily",  # String type as defined in the model
        format="xlsx",  # String type as defined in the model
        status="completed",  # String type as defined in the model
        progress=100.0,
        parameters={
            "start_date": datetime.utcnow().date().isoformat(),
            "end_date": datetime.utcnow().date().isoformat(),
            "include_graphs": True,
            "language": "fr"
        },
        user_id=test_user.id,
        created_by=test_user.id,
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    return report

@pytest.fixture(scope="function")
def test_subscription(db_session: Session, test_user: User) -> ReportSubscription:
    """Create a test report subscription."""
    subscription = ReportSubscription(
        name="Test Subscription",
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",  # Ensure unique email
        frequency="daily",  # String type as defined in the model
        report_type="daily",  # String type as defined in the model
        format="xlsx",  # String type as defined in the model
        parameters={
            "include_graphs": True,
            "language": "fr"
        },
        filters={
            "stations": ["all"],
            "artists": ["all"]
        },
        include_graphs=True,
        language="fr",
        active=True,
        user_id=test_user.id,
        created_by=test_user.id,
        created_at=datetime.utcnow()
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    return subscription

@pytest.fixture
def test_analytics_data(db_session: Session) -> AnalyticsData:
    """Create test analytics data."""
    now = datetime.utcnow()
    data = AnalyticsData(
        timestamp=now,
        detection_count=100,
        detection_rate=0.95,
        active_stations=10,
        average_confidence=0.92
    )
    db_session.add(data)
    db_session.commit()
    db_session.refresh(data)
    return data

@pytest.fixture
def test_hourly_detections(db_session: Session, test_track: Track, test_station: RadioStation) -> List[DetectionHourly]:
    """Create test hourly detections."""
    now = datetime.utcnow()
    detections = []
    for i in range(24):
        hour = now - timedelta(hours=23-i)
        detection = DetectionHourly(
            track_id=test_track.id,
            station_id=test_station.id,
            hour=hour.replace(minute=0, second=0, microsecond=0),
            count=i * 10
        )
        detections.append(detection)
    db_session.add_all(detections)
    db_session.commit()
    return detections

@pytest.fixture
def test_stats_manager(db_session: Session) -> StatsManager:
    """Create a test stats manager."""
    return StatsManager(db_session)

@pytest.fixture
def mock_audio_processor():
    """Create a mock audio processor."""
    mock = MagicMock()
    mock.detect_music = MagicMock(return_value={"status": "success", "detections": []})
    mock.is_initialized = MagicMock(return_value=True)
    return mock

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session

@pytest.fixture
def audio_processor(db_session):
    """Create an AudioProcessor instance for testing."""
    return AudioProcessor(db_session)

@pytest.fixture
def feature_extractor():
    """Create a FeatureExtractor instance for testing."""
    return FeatureExtractor()

@pytest.fixture
def track_manager(db_session):
    """Create a TrackManager instance for testing."""
    return TrackManager(db_session)

@pytest.fixture
def station_monitor(db_session):
    """Create a StationMonitor instance for testing."""
    return StationMonitor(db_session)

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
    # Create test artist first
    artist = Artist(
        name="Test Artist",
        country="SN",
        region="Dakar",
        type="solo",
        label="Test Label",
        created_at=datetime.utcnow()
    )
    db_session.add(artist)
    db_session.commit()
    db_session.refresh(artist)
    
    track = Track(
        title="Test Song",
        artist_id=artist.id,
        duration=timedelta(seconds=180),
        fingerprint="test_fingerprint",
        fingerprint_raw=b"test_fingerprint_raw",
        isrc="USABC1234567",
        label="Test Label",
        album="Test Album",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(track)
    db_session.commit()
    db_session.refresh(track)
    
    # Create track stats
    stats = TrackStats(
        track_id=track.id,
        total_plays=0,
        total_play_time=timedelta(0),
        average_confidence=0.0
    )
    db_session.add(stats)
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

@pytest.fixture
def multiple_detections(db_session: Session, test_track: Track, test_station: RadioStation) -> List[TrackDetection]:
    """Create multiple test detections."""
    now = datetime.utcnow()
    detections = []
    for i in range(10):
        detection = TrackDetection(
            track_id=test_track.id,
            station_id=test_station.id,
            detected_at=now - timedelta(hours=i),
            confidence=0.95,
            play_duration=timedelta(minutes=3),
            fingerprint="test_fingerprint",
            audio_hash=f"test_hash_{i}"
        )
        detections.append(detection)
    db_session.add_all(detections)
    db_session.commit()
    return detections

@pytest.fixture(scope="function")
def test_detection(db_session: Session, test_track: Track, test_station: RadioStation) -> TrackDetection:
    """Create a test detection."""
    detection = TrackDetection(
        track_id=test_track.id,
        station_id=test_station.id,
        confidence=0.95,
        detected_at=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(minutes=3),
        play_duration=timedelta(minutes=3),
        fingerprint=f"test_detection_fingerprint_{uuid.uuid4().hex}",  # Ensure unique fingerprint
        audio_hash=f"test_audio_hash_{uuid.uuid4().hex}",  # Ensure unique audio hash
        _is_valid=True
    )
    db_session.add(detection)
    db_session.commit()
    db_session.refresh(detection)
    return detection 