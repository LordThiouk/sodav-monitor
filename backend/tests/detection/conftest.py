"""Fixtures for detection tests."""

import pytest
import numpy as np
from unittest.mock import Mock, patch
import os
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.detection.audio_processor import AudioProcessor
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.stream_handler import StreamHandler
from backend.models.models import RadioStation, Track, TrackDetection
from backend.models.database import SessionLocal
from backend.utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(__name__)

@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.query = Mock()
    session.rollback = Mock()
    return session

@pytest.fixture
def audio_processor(mock_db_session):
    """Create an AudioProcessor instance for testing."""
    return AudioProcessor(db_session=mock_db_session)

@pytest.fixture
def feature_extractor():
    """Create a FeatureExtractor instance for testing."""
    return FeatureExtractor()

@pytest.fixture
def track_manager(mock_db_session):
    """Create a TrackManager instance for testing."""
    return TrackManager(db_session=mock_db_session)

@pytest.fixture
def stream_handler():
    """Create a StreamHandler instance for testing."""
    return StreamHandler()

@pytest.fixture
def mock_audio_stream():
    """Create a mock audio stream for testing."""
    return np.random.random(44100 * 10)  # 10 seconds of audio

@pytest.fixture
def mock_music_features():
    """Create mock features typical for music."""
    return {
        'mfcc': np.random.random((100, 13)),
        'spectral_centroid': np.array([2000] * 100),
        'spectral_rolloff': np.array([0.85] * 100),
        'zero_crossing_rate': np.array([0.1] * 100)
    }

@pytest.fixture
def mock_speech_features():
    """Create mock features typical for speech."""
    return {
        'mfcc': np.random.random((100, 13)),
        'spectral_centroid': np.array([1000] * 100),
        'spectral_rolloff': np.array([0.3] * 100),
        'zero_crossing_rate': np.array([0.3] * 100)
    }

@pytest.fixture
def mock_track_data():
    """Create mock track data for testing."""
    return {
        'title': 'Test Track',
        'artist': 'Test Artist',
        'album': 'Test Album',
        'duration': 180,
        'fingerprint': 'test_fingerprint_hash',
        'confidence': 0.95,
        'detected_at': datetime.now().isoformat()
    }

@pytest.fixture
def mock_station_data():
    """Create mock radio station data for testing."""
    return {
        'id': 'test_station_1',
        'name': 'Test Radio',
        'url': 'http://test.radio/stream',
        'format': 'mp3',
        'bitrate': 128,
        'status': 'active'
    }

@pytest.fixture
def mock_external_api_response():
    """Create mock responses for external APIs."""
    return {
        'musicbrainz': {
            'success': True,
            'data': {
                'title': 'Test Track',
                'artist': 'Test Artist',
                'album': 'Test Album',
                'year': '2024'
            }
        },
        'audd': {
            'success': True,
            'data': {
                'title': 'Test Track',
                'artist': 'Test Artist',
                'album': 'Test Album',
                'release_date': '2024-01-01'
            }
        }
    }

@pytest.fixture
def sample_rates():
    """Provide common sample rates for testing."""
    return [22050, 44100, 48000]

@pytest.fixture
def test_audio_files(tmp_path):
    """Create temporary audio files for testing."""
    # Create a directory for test audio files
    audio_dir = tmp_path / "test_audio"
    audio_dir.mkdir()
    
    # Create some test audio data
    durations = [1, 5, 10]  # seconds
    files = []
    
    for duration in durations:
        audio_data = np.random.random(44100 * duration)
        file_path = audio_dir / f"test_audio_{duration}s.raw"
        audio_data.tofile(file_path)
        files.append(file_path)
    
    return files

@pytest.fixture
def mock_config():
    """Create mock configuration for testing."""
    return {
        'audio': {
            'sample_rate': 44100,
            'channels': 2,
            'chunk_size': 4096,
            'buffer_size': 16384
        },
        'detection': {
            'confidence_threshold': 0.8,
            'min_duration': 1.0,
            'max_silence': 0.5
        },
        'api': {
            'musicbrainz_api_key': 'test_mb_key',
            'audd_api_key': 'test_audd_key'
        }
    } 