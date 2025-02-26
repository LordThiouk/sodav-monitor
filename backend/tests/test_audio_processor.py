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
    return AudioProcessor(db_session)

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
        stream_url="http://test.stream/audio",
        country="SN",
        language="fr",
        is_active=True
    )

@pytest.mark.asyncio
async def test_process_stream_speech(audio_processor, feature_extractor):
    """Test de détection de parole."""
    # Simuler des données audio de parole
    audio_data = np.random.random(44100)
    
    # Mocker la détection de type de contenu
    with patch.object(feature_extractor, 'is_music', return_value=False):
        result = await audio_processor.process_stream(audio_data, station_id=1)
        
        assert result["type"] == "speech"
        assert result["confidence"] == 0.0
        assert result["station_id"] == 1

@pytest.mark.asyncio
async def test_process_stream_local_match(audio_processor, track_manager):
    """Test de détection locale de musique."""
    # Simuler des données audio de musique
    audio_data = np.random.random(44100)
    
    # Mocker la détection locale
    mock_match = {
        "confidence": 0.95,
        "track": {"id": 1, "title": "Test Track", "artist": "Test Artist"}
    }
    
    with patch.object(track_manager, 'find_local_match', return_value=mock_match):
        result = await audio_processor.process_stream(audio_data, station_id=1)
        
        assert result["type"] == "music"
        assert result["source"] == "local"
        assert result["confidence"] == 0.95
        assert result["track"]["title"] == "Test Track"

@pytest.mark.asyncio
async def test_process_stream_musicbrainz_match(audio_processor, track_manager):
    """Test de détection avec MusicBrainz."""
    audio_data = np.random.random(44100)
    
    # Mocker les détections
    with patch.object(track_manager, 'find_local_match', return_value=None):
        mock_mb_match = {
            "confidence": 0.85,
            "track": {"id": 2, "title": "MB Track", "artist": "MB Artist"}
        }
        with patch.object(track_manager, 'find_musicbrainz_match', return_value=mock_mb_match):
            result = await audio_processor.process_stream(audio_data, station_id=1)
            
            assert result["type"] == "music"
            assert result["source"] == "musicbrainz"
            assert result["confidence"] == 0.85
            assert result["track"]["title"] == "MB Track"

@pytest.mark.asyncio
async def test_process_stream_audd_match(audio_processor, track_manager):
    """Test de détection avec Audd."""
    audio_data = np.random.random(44100)
    
    # Mocker les détections
    with patch.object(track_manager, 'find_local_match', return_value=None):
        with patch.object(track_manager, 'find_musicbrainz_match', return_value=None):
            mock_audd_match = {
                "confidence": 0.75,
                "track": {"id": 3, "title": "Audd Track", "artist": "Audd Artist"}
            }
            with patch.object(track_manager, 'find_audd_match', return_value=mock_audd_match):
                result = await audio_processor.process_stream(audio_data, station_id=1)
                
                assert result["type"] == "music"
                assert result["source"] == "audd"
                assert result["confidence"] == 0.75
                assert result["track"]["title"] == "Audd Track"

@pytest.mark.asyncio
async def test_process_stream_no_match(audio_processor, track_manager):
    """Test de détection sans correspondance."""
    audio_data = np.random.random(44100)
    
    # Mocker toutes les détections pour qu'elles échouent
    with patch.object(track_manager, 'find_local_match', return_value=None):
        with patch.object(track_manager, 'find_musicbrainz_match', return_value=None):
            with patch.object(track_manager, 'find_audd_match', return_value=None):
                result = await audio_processor.process_stream(audio_data, station_id=1)
                
                assert result["type"] == "music"
                assert result["source"] == "unknown"
                assert result["confidence"] == 0.0

@pytest.mark.asyncio
async def test_station_monitoring(audio_processor, station_monitor):
    """Test du monitoring des stations."""
    # Test du démarrage du monitoring
    with patch.object(station_monitor, 'start_monitoring', return_value=True):
        result = await audio_processor.start_monitoring(1)
        assert result is True
    
    # Test de l'arrêt du monitoring
    with patch.object(station_monitor, 'stop_monitoring', return_value=True):
        result = await audio_processor.stop_monitoring(1)
        assert result is True

def test_memory_management(audio_processor):
    """Test de la gestion de la mémoire."""
    # Pour le moment, la fonction retourne toujours True
    assert audio_processor._check_memory_usage() is True 