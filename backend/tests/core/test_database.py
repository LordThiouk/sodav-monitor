"""Tests des opérations de base de données."""

import pytest
from sqlalchemy.orm import Session
from backend.models.database import SessionLocal, engine, get_database_url
from backend.models.models import Base, RadioStation, Track, TrackDetection
from datetime import datetime

@pytest.fixture(scope="function")
def db_session() -> Session:
    """Fixture pour la session de base de données de test."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_database_connection(db_session):
    """Test de la connexion à la base de données."""
    assert db_session is not None
    assert db_session.is_active

def test_create_station(db_session):
    """Test de la création d'une station radio."""
    station = RadioStation(
        name="Test Station",
        stream_url="http://test.stream",
        country="SN",
        language="fr",
        status="active"
    )
    db_session.add(station)
    db_session.commit()
    
    saved_station = db_session.query(RadioStation).first()
    assert saved_station.name == "Test Station"
    assert saved_station.stream_url == "http://test.stream"

def test_create_track(db_session):
    """Test de la création d'une piste."""
    track = Track(
        title="Test Track",
        artist="Test Artist",
        duration=180,
        fingerprint="test_fingerprint"
    )
    db_session.add(track)
    db_session.commit()
    
    saved_track = db_session.query(Track).first()
    assert saved_track.title == "Test Track"
    assert saved_track.artist == "Test Artist" 