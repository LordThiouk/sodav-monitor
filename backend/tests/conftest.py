"""Test configuration for the SODAV Monitor project."""

import pytest
from unittest.mock import Mock, MagicMock, patch
import os
from typing import Generator, Dict
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt

from backend.models.database import Base, get_db
from backend.models.models import (
    User, RadioStation, Track, TrackDetection, ReportType, ReportFormat,
    Artist, StationStatus, StationHealth, ArtistStats, TrackStats
)
from backend.routers import auth, channels, analytics, detections, reports
from backend.core.security import create_access_token

# Mock settings before any imports
mock_settings = MagicMock()
mock_settings.SECRET_KEY = "test_secret_key"
mock_settings.ALGORITHM = "HS256"
mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15
mock_settings.DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/sodav_test"
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

# Apply the mock settings
with patch('backend.core.config.settings.get_settings', return_value=mock_settings):
    from backend.models.database import Base
    from backend.models.models import User, RadioStation, Track, TrackDetection, ReportType, ReportFormat
    from backend.routers import auth, channels, analytics, detections, reports

# Create test database engine
test_engine = create_engine(
    "postgresql://postgres:postgres@localhost:5432/sodav_test",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30
)

# Create test session factory
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)

@pytest.fixture(scope="session")
def test_app():
    """Create a test FastAPI application."""
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(channels.router, prefix="/api/channels", tags=["channels"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
    app.include_router(detections.router, prefix="/api/detections", tags=["detections"])
    app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
    return app

@pytest.fixture(scope="function")
def test_db_setup():
    """Set up test database."""
    # Drop all tables
    Base.metadata.drop_all(bind=test_engine)
    
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create a new session
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Verify tables are created
    inspector = inspect(test_engine)
    if 'users' not in inspector.get_table_names():
        raise Exception("Users table not created")
    
    # Verify columns exist
    user_columns = [col['name'] for col in inspector.get_columns('users')]
    required_columns = ['id', 'username', 'email', 'password_hash', 'is_active', 'created_at', 'last_login', 'role', 'reset_token', 'reset_token_expires']
    missing_columns = [col for col in required_columns if col not in user_columns]
    if missing_columns:
        raise Exception(f"Missing columns in users table: {missing_columns}")
    
    try:
        yield session
    finally:
        # Roll back transaction and close session
        session.close()
        transaction.rollback()
        connection.close()
        # Drop all tables
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def db_session(test_db_setup) -> Generator[Session, None, None]:
    """Create a test database session."""
    yield test_db_setup  # Use the session from test_db_setup

@pytest.fixture
def client(test_app, db_session) -> Generator:
    """Create a test client."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    test_app.dependency_overrides[get_db] = override_get_db
    with TestClient(test_app) as c:
        yield c
    test_app.dependency_overrides.clear()

@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        role="user",
        is_active=True,
        created_at=datetime.utcnow()
    )
    user.set_password("testpass")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Create authentication headers."""
    access_token = create_access_token(
        data={"sub": test_user.email},
        settings_override=mock_settings
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
        last_checked=datetime.utcnow(),
        region="Dakar",
        type="radio"
    )
    db_session.add(station)
    db_session.commit()
    db_session.refresh(station)
    return station

@pytest.fixture
def test_artist(db_session: Session) -> Artist:
    """Create a test artist."""
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
    
    # Create artist stats
    stats = ArtistStats(
        artist_id=artist.id,
        total_plays=0,
        total_play_time=timedelta(0),
        average_confidence=0.0
    )
    db_session.add(stats)
    db_session.commit()
    return artist

@pytest.fixture
def test_track(db_session: Session, test_artist: Artist) -> Track:
    """Create a test track."""
    track = Track(
        title="Test Track",
        artist_id=test_artist.id,
        duration=timedelta(minutes=3),
        fingerprint="test_fingerprint",
        created_at=datetime.utcnow()
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
def test_detection(db_session: Session, test_track: Track, test_station: RadioStation) -> TrackDetection:
    """Create a test detection."""
    detection = TrackDetection(
        track_id=test_track.id,
        station_id=test_station.id,
        confidence=0.95,
        detected_at=datetime.utcnow(),
        play_duration=timedelta(minutes=3),
        is_valid=True,
        fingerprint="test_detection_fingerprint",
        audio_hash="test_audio_hash"
    )
    db_session.add(detection)
    db_session.commit()
    db_session.refresh(detection)
    return detection

@pytest.fixture
def test_station_health(db_session: Session, test_station: RadioStation) -> StationHealth:
    """Create a test station health record."""
    health = StationHealth(
        station_id=test_station.id,
        timestamp=datetime.utcnow(),
        status="healthy",
        response_time=0.1,
        content_type="audio/mpeg"
    )
    db_session.add(health)
    db_session.commit()
    db_session.refresh(health)
    return health

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

@pytest.fixture(scope="session")
def app():
    """Create a FastAPI instance for testing."""
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(channels.router, prefix="/api/channels", tags=["channels"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
    app.include_router(detections.router, prefix="/api/detections", tags=["detections"])
    app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
    return app

@pytest.fixture(scope="session")
def test_client(app):
    """Crée un client de test FastAPI."""
    return TestClient(app)

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