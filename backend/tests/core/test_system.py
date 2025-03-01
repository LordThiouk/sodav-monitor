"""Tests système pour l'application."""

import pytest
from sqlalchemy.orm import Session
from backend.models.models import RadioStation, Track, TrackDetection
from backend.models.database import SessionLocal
from backend.utils.radio.manager import RadioManager
from backend.detection.audio_processor import AudioProcessor

@pytest.fixture
def db_session():
    """Fixture pour la session de base de données."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def radio_manager(db_session):
    """Fixture pour le gestionnaire radio."""
    return RadioManager(db_session)

@pytest.fixture
def test_stations(db_session):
    """Fixture pour créer des stations de test."""
    stations = [
        RadioStation(
            name="Radio Test 1",
            stream_url="http://test1.stream/audio",
            country="SN",
            language="fr",
            is_active=True
        ),
        RadioStation(
            name="Radio Test 2",
            stream_url="http://test2.stream/audio",
            country="SN",
            language="fr",
            is_active=True
        )
    ]
    for station in stations:
        db_session.add(station)
    db_session.commit()
    return stations

async def test_station_monitoring(radio_manager, test_stations):
    """Test du monitoring des stations."""
    try:
        # Démarrer le monitoring pour chaque station
        for station in test_stations:
            await radio_manager.start_monitoring(station.id)
            
        # Vérifier que les stations sont bien monitorées
        active_stations = radio_manager.get_active_stations()
        assert len(active_stations) == len(test_stations)
        
        # Arrêter le monitoring
        for station in test_stations:
            await radio_manager.stop_monitoring(station.id)
            
    except Exception as e:
        pytest.fail(f"Test failed: {str(e)}")

async def test_stream_processing(radio_manager, test_stations):
    """Test du traitement des flux."""
    try:
        for station in test_stations:
            # Traiter le flux
            result = await radio_manager.process_station_stream(station.id)
            assert result is not None
            
            # Vérifier les métriques
            metrics = radio_manager.get_performance_metrics()
            assert "total_detections" in metrics
            assert "average_confidence" in metrics
            assert "active_monitors" in metrics
            
    except Exception as e:
        pytest.fail(f"Test failed: {str(e)}")

def test_performance_metrics(radio_manager, test_stations, db_session):
    """Test des métriques de performance."""
    try:
        # Créer quelques détections
        for station in test_stations:
            track = Track(
                title=f"Test Track {station.id}",
                artist="Test Artist",
                fingerprint=b"test_fingerprint"
            )
            db_session.add(track)
            db_session.commit()
            
            detection = TrackDetection(
                station_id=station.id,
                track_id=track.id,
                confidence=0.9
            )
            db_session.add(detection)
        db_session.commit()
        
        # Vérifier les métriques
        metrics = radio_manager.get_performance_metrics()
        assert metrics["total_detections"] >= len(test_stations)
        assert 0 <= metrics["average_confidence"] <= 1
        assert metrics["active_monitors"] >= 0
        
    except Exception as e:
        pytest.fail(f"Test failed: {str(e)}")
