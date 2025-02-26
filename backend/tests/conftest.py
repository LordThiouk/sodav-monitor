"""Configuration des tests."""

import os
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from fastapi import FastAPI
from jose import jwt

from backend.models.models import Base, RadioStation, Track, TrackDetection, Report, ReportSubscription, User
from backend.models.models import ReportType, ReportStatus, ReportFormat
from backend.reports.report_generator import ReportGenerator
from backend.analytics.stats_manager import StatsManager
from backend.detection.audio_processor import AudioProcessor, FeatureExtractor, TrackManager, StationMonitor
from backend.routers import auth, channels, analytics, detections, reports
from backend.core.config import get_settings

settings = get_settings()

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
    """Crée un utilisateur de test."""
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
    """Crée un token JWT de test."""
    token_data = {
        "sub": test_user.username,
        "role": test_user.role,
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    return jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

@pytest.fixture
def auth_headers(auth_token):
    """Crée les en-têtes d'authentification pour les tests."""
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture(scope="session")
def engine():
    """Crée une base de données SQLite en mémoire pour les tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def db_session(engine):
    """Crée une nouvelle session de base de données pour chaque test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def sample_station(db_session):
    """Crée une station de radio de test."""
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
    """Crée une piste de test."""
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
    """Crée une détection de test."""
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
    """Crée des données de rapport de test."""
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
def audio_processor():
    """Crée un processeur audio de test."""
    feature_extractor = FeatureExtractor()
    track_manager = TrackManager()
    station_monitor = StationMonitor()
    return AudioProcessor(feature_extractor, track_manager, station_monitor)

@pytest.fixture
def feature_extractor():
    """Crée un extracteur de caractéristiques de test."""
    return FeatureExtractor()

@pytest.fixture
def track_manager():
    """Crée un gestionnaire de pistes de test."""
    return TrackManager()

@pytest.fixture
def station_monitor():
    """Crée un moniteur de station de test."""
    return StationMonitor() 