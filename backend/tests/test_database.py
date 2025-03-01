"""Tests for database models and operations."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from backend.models.models import (
    Base, User, Track, Artist, RadioStation, TrackDetection,
    ArtistStats, TrackStats, StationStats, StationTrackStats,
    DetectionHourly, DetectionDaily, DetectionMonthly,
    Report, ReportSubscription, ReportType, ReportFormat, ReportStatus,
    StationStatus, StationHealth, ArtistDaily
)
from werkzeug.security import generate_password_hash

@pytest.fixture(scope="function")
def engine():
    """Create a test database engine."""
    return create_engine('sqlite:///:memory:')

@pytest.fixture(scope="function")
def session(engine):
    """Create a new database session for testing."""
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

@pytest.fixture
def test_user(session):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=generate_password_hash("testpass"),
        role="user"
    )
    session.add(user)
    session.commit()
    return user

@pytest.fixture
def test_artist(session):
    """Create a test artist."""
    artist = Artist(
        name="Test Artist",
        country="SN",
        region="Dakar",
        type="solo",
        label="Test Label"
    )
    session.add(artist)
    session.commit()
    return artist

@pytest.fixture
def test_track(session, test_artist):
    """Create a test track."""
    track = Track(
        title="Test Track",
        artist_id=test_artist.id,
        duration=timedelta(seconds=180),
        fingerprint="test_fingerprint",
        external_ids={"spotify": "test_id"}
    )
    session.add(track)
    session.commit()
    return track

@pytest.fixture
def test_station(session):
    """Create a test radio station."""
    station = RadioStation(
        name="Test Radio",
        stream_url="http://test.stream/audio",
        country="SN",
        language="fr",
        region="Dakar",
        type="radio",
        status=StationStatus.ACTIVE.value,
        is_active=True
    )
    session.add(station)
    session.commit()
    return station

class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation(self, session):
        """Test user creation."""
        user = User(
            username="testuser2",
            email="test2@example.com",
            password_hash=generate_password_hash("testpass"),
            role="user"
        )
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.username == "testuser2"
        assert user.role == "user"

    def test_unique_username(self, session):
        """Test username uniqueness."""
        user1 = User(
            username="unique",
            email="unique1@example.com",
            password_hash=generate_password_hash("testpass"),
            role="user"
        )
        session.add(user1)
        session.commit()

        user2 = User(
            username="unique",
            email="unique2@example.com",
            password_hash=generate_password_hash("testpass"),
            role="user"
        )
        session.add(user2)
        with pytest.raises(Exception):
            session.commit()

    def test_user_roles(self, session):
        """Test user role assignment."""
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("adminpass"),
            role="admin"
        )
        session.add(admin)
        session.commit()

        assert admin.role == "admin"

class TestArtistModel:
    """Test Artist model functionality."""
    
    def test_artist_creation(self, session):
        """Test artist creation."""
        artist = Artist(
            name="New Artist",
            country="SN",
            type="band"
        )
        session.add(artist)
        session.commit()

        assert artist.id is not None
        assert artist.name == "New Artist"

    def test_artist_stats_relationship(self, session, test_artist):
        """Test artist statistics relationship."""
        stats = ArtistStats(
            artist_id=test_artist.id,
            total_plays=10,
            total_play_time=timedelta(hours=1)
        )
        session.add(stats)
        session.commit()

        assert test_artist.stats.total_plays == 10

    def test_artist_tracks_relationship(self, session, test_artist):
        """Test artist tracks relationship."""
        track = Track(
            title="Artist Track",
            artist_id=test_artist.id,
            duration=timedelta(minutes=4)
        )
        session.add(track)
        session.commit()

        assert len(test_artist.tracks) == 1
        assert test_artist.tracks[0].title == "Artist Track"

class TestTrackModel:
    """Test Track model functionality."""
    
    def test_track_creation(self, session, test_track):
        """Test track creation."""
        track = Track(
            title="New Track",
            artist_id=test_track.artist_id,
            duration=timedelta(minutes=5)
        )
        session.add(track)
        session.commit()

        assert track.id is not None
        assert track.title == "New Track"

    def test_track_artist_relationship(self, session, test_track, test_artist):
        """Test track artist relationship."""
        assert test_track.artist_id == test_artist.id
        assert test_track.artist.name == "Test Artist"

    def test_track_stats_relationship(self, session, test_track):
        """Test track statistics relationship."""
        stats = TrackStats(
            track_id=test_track.id,
            total_plays=5,
            total_play_time=timedelta(minutes=15)
        )
        session.add(stats)
        session.commit()

        assert test_track.stats.total_plays == 5

class TestRadioStationModel:
    """Test RadioStation model functionality."""
    
    def test_station_creation(self, session):
        """Test radio station creation."""
        station = RadioStation(
            name="New Station",
            stream_url="http://new.stream",
            country="SN"
        )
        session.add(station)
        session.commit()

        assert station.id is not None
        assert station.name == "New Station"

    def test_station_health_monitoring(self, session, test_station):
        """Test station health monitoring."""
        test_station.last_check = datetime.utcnow()
        test_station.status = "offline"
        session.commit()

        assert test_station.status == "offline"

    def test_station_track_stats(self, session, test_station, test_track):
        """Test station track statistics."""
        stats = StationTrackStats(
            station_id=test_station.id,
            track_id=test_track.id,
            play_count=3
        )
        session.add(stats)
        session.commit()

        assert stats.play_count == 3

class TestTrackDetectionModel:
    """Test TrackDetection model functionality."""
    
    def test_detection_creation(self, session, test_track, test_station):
        """Test track detection creation."""
        detection = TrackDetection(
            track_id=test_track.id,
            station_id=test_station.id,
            confidence=0.95,
            detected_at=datetime.utcnow(),
            play_duration=timedelta(minutes=3),
            fingerprint="test_detection_fingerprint",
            is_valid=True  # Set is_valid explicitly
        )
        session.add(detection)
        session.commit()
        
        assert detection.id is not None
        assert detection.confidence == 0.95
        assert detection.is_valid is True
        
    def test_detection_validation(self, session, test_track, test_station):
        """Test detection validation rules."""
        detection = TrackDetection(
            track_id=test_track.id,
            station_id=test_station.id,
            confidence=0.95,
            detected_at=datetime.utcnow(),
            play_duration=timedelta(minutes=3),
            fingerprint="test_fingerprint",
            is_valid=True
        )
        session.add(detection)
        session.commit()

        assert detection.confidence >= 0.0
        assert detection.confidence <= 1.0

class TestReportingModels:
    """Test reporting-related models."""
    
    def test_report_creation(self, session, test_user):
        """Test report creation."""
        report = Report(
            user_id=test_user.id,
            type="monthly",
            status="pending",
            parameters={"month": 3, "year": 2024}
        )
        session.add(report)
        session.commit()
        
        assert report.id is not None
        assert report.status == "pending"
        
    def test_report_subscription(self, session, test_user):
        """Test report subscription."""
        sub = ReportSubscription(
            user_id=test_user.id,
            report_type="monthly",
            frequency="monthly",
            parameters={"format": "pdf"}
        )
        session.add(sub)
        session.commit()
        
        assert sub.id is not None
        assert sub.frequency == "monthly"

class TestAnalyticsModels:
    """Test analytics-related models."""
    
    def test_detection_aggregation(self, session, test_track, test_station):
        """Test detection aggregation."""
        hourly = DetectionHourly(
            track_id=test_track.id,
            station_id=test_station.id,
            hour=datetime.utcnow().replace(minute=0, second=0, microsecond=0),
            count=3
        )
        session.add(hourly)
        session.commit()
        
        assert hourly.count == 3
        
    def test_artist_stats_aggregation(self, session, test_artist):
        """Test artist statistics aggregation."""
        daily = ArtistDaily(
            artist_id=test_artist.id,
            date=datetime.utcnow().date(),
            count=5,
            total_play_time=timedelta(minutes=15)
        )
        session.add(daily)
        session.commit()
        
        assert daily.count == 5
        assert daily.total_play_time == timedelta(minutes=15)

def test_cascade_delete(session, test_track, test_station):
    """Test cascade deletion behavior."""
    detection = TrackDetection(
        track_id=test_track.id,
        station_id=test_station.id,
        confidence=0.9,
        detected_at=datetime.utcnow(),
        play_duration=timedelta(minutes=2),
        fingerprint="cascade_test",
        is_valid=True
    )
    session.add(detection)
    session.commit()

    session.delete(test_track)
    session.commit()

    assert session.query(TrackDetection).filter_by(id=detection.id).first() is None 