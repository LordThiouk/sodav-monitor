"""Unit tests for the AudioProcessor core functionality."""

import pytest
import numpy as np
from backend.detection.audio_processor import AudioProcessor
from unittest.mock import Mock
from sqlalchemy.orm import Session

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = Mock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.query = Mock()
    session.rollback = Mock()
    return session

@pytest.fixture
def audio_processor(mock_db_session):
    """Fixture providing a configured AudioProcessor instance."""
    return AudioProcessor(db_session=mock_db_session, sample_rate=44100)

@pytest.fixture
def sample_audio_data():
    """Fixture providing sample audio data for testing."""
    # Create a synthetic audio signal (1 second of 440Hz sine wave)
    duration = 1.0
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration))
    return np.sin(2 * np.pi * 440 * t)

class TestAudioProcessorInitialization:
    """Test AudioProcessor initialization and parameter validation."""
    
    def test_default_initialization(self, mock_db_session):
        """Test initialization with default parameters."""
        processor = AudioProcessor(db_session=mock_db_session)
        assert processor.sample_rate == 44100
        assert processor.db_session == mock_db_session
        
    def test_custom_sample_rate(self, mock_db_session):
        """Test initialization with custom sample rate."""
        custom_rate = 48000
        processor = AudioProcessor(db_session=mock_db_session, sample_rate=custom_rate)
        assert processor.sample_rate == custom_rate
        
    def test_invalid_sample_rate(self, mock_db_session):
        """Test initialization with invalid sample rate."""
        with pytest.raises(ValueError):
            AudioProcessor(db_session=mock_db_session, sample_rate=0)
            
    def test_missing_db_session(self):
        """Test initialization without database session."""
        with pytest.raises(TypeError):
            AudioProcessor()

class TestAudioProcessorStreamProcessing:
    """Test audio stream processing functionality."""
    
    def test_process_stream_returns_tuple(self, audio_processor):
        """Test process_stream returns expected tuple."""
        audio_data = np.random.random(44100)  # 1 second of random audio
        result = audio_processor.detect_music_in_stream(audio_data)
        assert isinstance(result, tuple)
        assert len(result) == 2
        
    def test_confidence_score_range(self, audio_processor):
        """Test confidence score is within valid range."""
        audio_data = np.random.random(44100)
        _, confidence = audio_processor.detect_music_in_stream(audio_data)
        assert 0 <= confidence <= 1
        
    def test_empty_audio_data(self, audio_processor):
        """Test handling of empty audio data."""
        with pytest.raises(ValueError):
            audio_processor.detect_music_in_stream(np.array([]))
            
    def test_invalid_audio_data_type(self, audio_processor):
        """Test handling of invalid audio data type."""
        with pytest.raises(TypeError):
            audio_processor.detect_music_in_stream([1, 2, 3])  # List instead of numpy array

class TestAudioProcessorFeatureExtraction:
    """Test feature extraction functionality."""
    
    def test_feature_extraction_shape(self, audio_processor):
        """Test shape of extracted features."""
        audio_data = np.random.random(44100)
        features = audio_processor.extract_features(audio_data)
        assert isinstance(features, dict)
        assert all(isinstance(feat, np.ndarray) for feat in features.values())
        
    def test_feature_extraction_range(self, audio_processor):
        """Test range of extracted features."""
        audio_data = np.random.random(44100)
        features = audio_processor.extract_features(audio_data)
        for feat in features.values():
            assert not np.any(np.isnan(feat))
            assert not np.any(np.isinf(feat))
            
    def test_empty_audio_data(self, audio_processor):
        """Test feature extraction with empty audio data."""
        with pytest.raises(ValueError):
            audio_processor.extract_features(np.array([]))

class TestAudioProcessorFingerprinting:
    """Test audio fingerprinting functionality."""
    
    def test_successful_match(self, audio_processor):
        """Test successful fingerprint matching."""
        audio_data = np.random.random(44100)
        fingerprint = audio_processor.generate_fingerprint(audio_data)
        assert isinstance(fingerprint, bytes)
        assert len(fingerprint) > 0
        
    def test_empty_database(self, audio_processor):
        """Test matching against empty database."""
        audio_data = np.random.random(44100)
        audio_processor.db_session.query.return_value.filter.return_value.first.return_value = None
        match = audio_processor.find_match(audio_data)
        assert match is None
        
    def test_invalid_feature_shape(self, audio_processor):
        """Test handling of invalid feature shape."""
        with pytest.raises(ValueError):
            audio_processor.generate_fingerprint(np.array([])) 