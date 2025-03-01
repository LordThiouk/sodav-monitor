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
import logging
from backend.core.security import get_current_user, create_access_token
from backend.core.config import get_settings
from backend.models.models import StationStatus, User, RadioStation, Track, TrackDetection, ReportType, ReportFormat, Artist, StationHealth, ArtistStats, TrackStats

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Apply the mock settings and import models
with patch('backend.core.config.settings.get_settings', return_value=mock_settings):
    from backend.models.database import Base, get_db
    from backend.models.models import (
        User, RadioStation, Track, TrackDetection, ReportType, ReportFormat,
        Artist, StationHealth, ArtistStats, TrackStats,
        Report, ReportSubscription, DetectionHourly, DetectionDaily,
        DetectionMonthly, StationStats, TrackDaily, TrackMonthly,
        ArtistDaily, ArtistMonthly, StationTrackStats, AnalyticsData
    )
    from backend.routers import auth, channels, analytics, detections, reports

# Create test database engine with minimal pooling for tests
test_engine = create_engine(
    "postgresql://postgres:postgres@localhost:5432/sodav_test",
    poolclass=StaticPool,
    connect_args={"connect_timeout": 5}
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
def test_db():
    """Set up test database."""
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=test_engine)
        logger.info("Dropped all tables")
        
        # Create all tables
        Base.metadata.create_all(bind=test_engine)
        logger.info("Created all tables")
        
        # Create a new session
        connection = test_engine.connect()
        transaction = connection.begin()
        session = TestingSessionLocal(bind=connection)
        
        # Verify tables are created
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        logger.info(f"Created tables: {tables}")
        
        if 'users' not in tables:
            raise Exception("Users table not created. Available tables: " + ", ".join(tables))
            
        yield session
        
        # Rollback the transaction
        transaction.rollback()
        connection.close()
        
    except Exception as e:
        logger.error(f"Error setting up test database: {str(e)}")
        raise

@pytest.fixture(scope="function")
def client(test_app, test_db) -> Generator:
    """Create a test client."""
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()
            
    def override_get_settings():
        return mock_settings
    
    async def override_get_current_user():
        # Create a test user if it doesn't exist
        user = test_db.query(User).filter(User.email == "test@example.com").first()
        if not user:
            user = User(
                username="testuser",
                email="test@example.com",
                role="user",
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
    user = test_db.query(User).filter(User.email == "test@example.com").first()
    if user:
        return user
        
    user = User(
        username="testuser",
        email="test@example.com",
        role="user",
        is_active=True,
        created_at=datetime.utcnow()
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
        settings_override=mock_settings
    )
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
def test_station(test_db: Session) -> RadioStation:
    """Create a test radio station."""
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
    test_db.flush()  # Use flush instead of commit to keep changes in the current transaction
    return station

@pytest.fixture
def test_artist(test_db: Session) -> Artist:
    """Create a test artist."""
    artist = Artist(
        name="Test Artist",
        country="SN",
        region="Dakar",
        type="solo",
        label="Test Label",
        created_at=datetime.utcnow()
    )
    test_db.add(artist)
    test_db.commit()
    test_db.refresh(artist)
    
    # Create artist stats
    stats = ArtistStats(
        artist_id=artist.id,
        total_plays=0,
        total_play_time=timedelta(0),
        average_confidence=0.0
    )
    test_db.add(stats)
    test_db.commit()
    return artist

@pytest.fixture
def test_track(test_db: Session, test_artist: Artist) -> Track:
    """Create a test track."""
    track = Track(
        title="Test Track",
        artist_id=test_artist.id,
        duration=timedelta(minutes=3),
        fingerprint="test_fingerprint",
        created_at=datetime.utcnow()
    )
    test_db.add(track)
    test_db.commit()
    test_db.refresh(track)
    
    # Create track stats
    stats = TrackStats(
        track_id=track.id,
        total_plays=0,
        total_play_time=timedelta(0),
        average_confidence=0.0
    )
    test_db.add(stats)
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
        is_valid=True,
        fingerprint="test_detection_fingerprint",
        audio_hash="test_audio_hash"
    )
    test_db.add(detection)
    test_db.commit()
    test_db.refresh(detection)
    return detection

@pytest.fixture
def test_station_health(test_db: Session, test_station: RadioStation) -> StationHealth:
    """Create a test station health record."""
    health = StationHealth(
        station_id=test_station.id,
        timestamp=datetime.utcnow(),
        status="healthy",
        response_time=0.1,
        content_type="audio/mpeg"
    )
    test_db.add(health)
    test_db.commit()
    test_db.refresh(health)
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
def audio_processor(test_db):
    """Create an AudioProcessor instance for testing."""
    return AudioProcessor(test_db)

@pytest.fixture
def feature_extractor():
    """Create a FeatureExtractor instance for testing."""
    return FeatureExtractor()

@pytest.fixture
def track_manager(test_db):
    """Create a TrackManager instance for testing."""
    return TrackManager(test_db)

@pytest.fixture
def station_monitor(test_db):
    """Create a StationMonitor instance for testing."""
    return StationMonitor(test_db)

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
def sample_station(test_db):
    """Create a test radio station."""
    station = RadioStation(
        name="Radio Test",
        stream_url="http://test.stream/live",
        status="active"
    )
    test_db.add(station)
    test_db.commit()
    return station

@pytest.fixture
def sample_track(test_db):
    """Create a test track."""
    track = Track(
        title="Test Song",
        artist="Test Artist",
        duration=180.0,
        fingerprint="test_fingerprint"
    )
    test_db.add(track)
    test_db.commit()
    return track

@pytest.fixture
def sample_detection(test_db, sample_station, sample_track):
    """Create a test detection."""
    detection = TrackDetection(
        station_id=sample_station.id,
        track_id=sample_track.id,
        confidence=0.95,
        detected_at=datetime.utcnow()
    )
    test_db.add(detection)
    test_db.commit()
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
def report_generator(test_db):
    """Crée un générateur de rapports de test."""
    stats_manager = StatsManager(test_db)
    return ReportGenerator(test_db, stats_manager) 