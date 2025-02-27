"""Unit tests for the AudioProcessor core functionality."""

import pytest
import numpy as np
from backend.detection.audio_processor import AudioProcessor

@pytest.fixture
def audio_processor():
    """Fixture providing a configured AudioProcessor instance."""
    return AudioProcessor(sample_rate=44100)

@pytest.fixture
def sample_audio_data():
    """Fixture providing sample audio data for testing."""
    # Create a synthetic audio signal (1 second of 440Hz sine wave)
    duration = 1.0
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration))
    return np.sin(2 * np.pi * 440 * t)

class TestAudioProcessorInitialization:
    """Test cases for AudioProcessor initialization."""
    
    def test_default_initialization(self):
        """Test initialization with default parameters."""
        processor = AudioProcessor()
        assert processor.sample_rate == 44100
        
    def test_custom_sample_rate(self):
        """Test initialization with custom sample rate."""
        custom_rate = 48000
        processor = AudioProcessor(sample_rate=custom_rate)
        assert processor.sample_rate == custom_rate
        
    def test_invalid_sample_rate(self):
        """Test initialization with invalid sample rate."""
        with pytest.raises(ValueError):
            AudioProcessor(sample_rate=0)

class TestAudioProcessorStreamProcessing:
    """Test cases for audio stream processing."""
    
    def test_process_stream_returns_tuple(self, audio_processor, sample_audio_data):
        """Test that process_stream returns a tuple of (bool, float)."""
        result = audio_processor.process_stream(sample_audio_data)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)
        
    def test_confidence_score_range(self, audio_processor, sample_audio_data):
        """Test that confidence score is between 0 and 1."""
        _, confidence = audio_processor.process_stream(sample_audio_data)
        assert 0 <= confidence <= 1
        
    def test_empty_audio_data(self, audio_processor):
        """Test processing empty audio data."""
        with pytest.raises(ValueError):
            audio_processor.process_stream(np.array([]))
            
    def test_invalid_audio_data_type(self, audio_processor):
        """Test processing invalid audio data type."""
        with pytest.raises(TypeError):
            audio_processor.process_stream([1, 2, 3])  # List instead of np.ndarray

class TestAudioProcessorFeatureExtraction:
    """Test cases for audio feature extraction."""
    
    def test_feature_extraction_shape(self, audio_processor, sample_audio_data):
        """Test that extracted features have the expected shape."""
        features = audio_processor.extract_features(sample_audio_data)
        assert isinstance(features, np.ndarray)
        assert features.shape == (128,)
        
    def test_feature_extraction_range(self, audio_processor, sample_audio_data):
        """Test that extracted features are within expected range."""
        features = audio_processor.extract_features(sample_audio_data)
        assert np.all((features >= 0) & (features <= 1))
        
    def test_empty_audio_data(self, audio_processor):
        """Test feature extraction with empty audio data."""
        with pytest.raises(ValueError):
            audio_processor.extract_features(np.array([]))

class TestAudioProcessorFingerprinting:
    """Test cases for audio fingerprint matching."""
    
    @pytest.fixture
    def sample_database(self):
        """Fixture providing a sample fingerprint database."""
        return [np.random.random((128,)) for _ in range(5)]
    
    def test_successful_match(self, audio_processor, sample_database):
        """Test successful fingerprint matching."""
        features = np.random.random((128,))
        match_idx = audio_processor.match_fingerprint(features, sample_database)
        assert match_idx is None or (0 <= match_idx < len(sample_database))
        
    def test_empty_database(self, audio_processor):
        """Test matching against empty database."""
        features = np.random.random((128,))
        match_idx = audio_processor.match_fingerprint(features, [])
        assert match_idx is None
        
    def test_invalid_feature_shape(self, audio_processor, sample_database):
        """Test matching with invalid feature shape."""
        features = np.random.random((64,))  # Wrong shape
        with pytest.raises(ValueError):
            audio_processor.match_fingerprint(features, sample_database) 