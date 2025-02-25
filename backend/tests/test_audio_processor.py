"""Tests pour le module de détection audio."""

import pytest
from unittest.mock import Mock, patch
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import io
import soundfile as sf

from ..detection.audio_processor.core import AudioProcessor
from ..detection.audio_processor.stream_handler import StreamHandler
from ..detection.audio_processor.feature_extractor import FeatureExtractor
from ..detection.audio_processor.track_manager import TrackManager
from ..detection.audio_processor.station_monitor import StationMonitor
from ..models.models import RadioStation, Track, TrackDetection

@pytest.fixture
def db_session():
    """Crée une session de base de données mock pour les tests."""
    return Mock(spec=Session)

@pytest.fixture
def audio_processor(db_session):
    """Crée une instance de AudioProcessor pour les tests."""
    music_recognizer = Mock()
    return AudioProcessor(db_session, music_recognizer)

@pytest.fixture
def stream_handler():
    """Crée une instance de StreamHandler pour les tests."""
    return StreamHandler()

@pytest.fixture
def feature_extractor():
    """Crée une instance de FeatureExtractor pour les tests."""
    return FeatureExtractor()

@pytest.fixture
def track_manager(db_session):
    """Crée une instance de TrackManager pour les tests."""
    return TrackManager(db_session)

@pytest.fixture
def station_monitor(db_session):
    """Crée une instance de StationMonitor pour les tests."""
    return StationMonitor(db_session)

@pytest.fixture
def sample_station():
    """Crée une station radio de test."""
    return RadioStation(
        id=1,
        name="Test Radio",
        stream_url="http://test.radio/stream",
        is_active=True,
        country="SN",
        language="fr"
    )

@pytest.mark.asyncio
async def test_process_stream_success(stream_handler, feature_extractor, track_manager):
    """Teste le traitement réussi d'un flux audio."""
    # Mock des données audio
    audio_data = b"mock_audio_data"
    
    # Mock du téléchargement audio
    with patch.object(stream_handler, '_download_audio_chunk', return_value=audio_data):
        # Mock de l'analyse audio
        with patch.object(feature_extractor, 'analyze_audio', return_value={
            "confidence": 0.9,
            "fingerprint": "test_fingerprint",
            "features": {"tempo": 120, "key": "C"}
        }):
            result = await stream_handler.process_stream(
                "http://test.radio/stream",
                feature_extractor,
                track_manager,
                station_id=1
            )
            
            assert result is not None
            assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_process_stream_no_music(stream_handler, feature_extractor, track_manager):
    """Teste le traitement d'un flux sans musique."""
    audio_data = b"mock_speech_data"
    
    with patch.object(stream_handler, '_download_audio_chunk', return_value=audio_data):
        with patch.object(feature_extractor, 'analyze_audio', return_value={
            "confidence": 0.2,
            "features": {"speech_probability": 0.9}
        }):
            result = await stream_handler.process_stream(
                "http://test.radio/stream",
                feature_extractor,
                track_manager,
                station_id=1
            )
            
            assert result == {"status": "Aucune musique détectée"}

@pytest.mark.asyncio
async def test_station_monitoring(station_monitor, sample_station, stream_handler, feature_extractor, track_manager):
    """Teste le monitoring d'une station."""
    with patch.object(station_monitor, 'monitor_station') as mock_monitor:
        await station_monitor.add_station(sample_station)
        assert sample_station.id in station_monitor.monitoring_tasks
        
        # Simule le monitoring pendant quelques secondes
        await station_monitor.start_monitoring(stream_handler, feature_extractor, track_manager)
        mock_monitor.assert_called_once()

@pytest.mark.asyncio
async def test_feature_extraction(feature_extractor):
    """Teste l'extraction des caractéristiques audio."""
    # Crée des données audio synthétiques pour le test
    sample_rate = 22050
    duration = 3  # secondes
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
    
    # Convertit en format WAV en mémoire
    audio_buffer = io.BytesIO()
    sf.write(audio_buffer, test_audio, sample_rate, format='WAV')
    audio_bytes = audio_buffer.getvalue()
    
    features = await feature_extractor.analyze_audio(audio_bytes)
    assert features is not None
    assert "confidence" in features
    assert features["confidence"] > 0

@pytest.mark.asyncio
async def test_track_management(track_manager, db_session):
    """Teste la gestion des pistes."""
    test_features = {
        "fingerprint": "test_fingerprint",
        "confidence": 0.95,
        "title": "Test Track",
        "artist": "Test Artist",
        "duration": 180
    }
    
    # Mock de la base de données
    mock_track = Mock(spec=Track)
    mock_track.id = 1
    mock_track.title = "Test Track"
    mock_track.to_dict = Mock(return_value={"id": 1, "title": "Test Track"})
    db_session.query.return_value.filter_by.return_value.first.return_value = mock_track
    
    result = await track_manager.process_track(test_features, station_id=1)
    assert result is not None
    assert "status" in result
    assert result["status"] == "success"
    assert "detection" in result
    assert "track_id" in result["detection"]
    assert result["detection"]["track_id"] == 1

def test_memory_management(audio_processor):
    """Teste la gestion de la mémoire."""
    assert audio_processor._check_memory_usage() is True
    assert audio_processor.max_memory_usage > 0
    assert audio_processor.processing_semaphore._value == audio_processor.max_concurrent_stations 