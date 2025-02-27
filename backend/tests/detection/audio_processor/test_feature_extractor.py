"""Tests for the FeatureExtractor class."""

import pytest
import numpy as np
from detection.audio_processor.feature_extractor import FeatureExtractor

@pytest.fixture
def feature_extractor():
    """Create a FeatureExtractor instance with default parameters."""
    return FeatureExtractor()

@pytest.fixture
def sample_audio():
    """Generate a sample audio signal for testing."""
    # Generate a 1-second sine wave at 440Hz
    duration = 1.0
    sample_rate = 22050
    t = np.linspace(0, duration, int(sample_rate * duration))
    signal = np.sin(2 * np.pi * 440 * t)
    return signal

class TestFeatureExtractorInitialization:
    """Test FeatureExtractor initialization and parameter validation."""
    
    def test_default_initialization(self):
        """Test initialization with default parameters."""
        extractor = FeatureExtractor()
        assert extractor.sample_rate == 22050
        assert extractor.n_mels == 128
        assert extractor.n_fft == 2048
        assert extractor.hop_length == 512
        
    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        extractor = FeatureExtractor(
            sample_rate=44100,
            n_mels=64,
            n_fft=1024,
            hop_length=256
        )
        assert extractor.sample_rate == 44100
        assert extractor.n_mels == 64
        assert extractor.n_fft == 1024
        assert extractor.hop_length == 256
        
    @pytest.mark.parametrize("param,value", [
        ("sample_rate", 0),
        ("n_mels", -1),
        ("n_fft", 0),
        ("hop_length", -10)
    ])
    def test_invalid_parameters(self, param, value):
        """Test initialization with invalid parameters."""
        params = {
            "sample_rate": 22050,
            "n_mels": 128,
            "n_fft": 2048,
            "hop_length": 512
        }
        params[param] = value
        
        with pytest.raises(ValueError):
            FeatureExtractor(**params)

class TestFeatureExtraction:
    """Test feature extraction functionality."""
    
    def test_extract_features_shape(self, feature_extractor, sample_audio):
        """Test the shape of extracted features."""
        features = feature_extractor.extract_features(sample_audio)
        
        assert "mel_spectrogram" in features
        assert "mfcc" in features
        assert "spectral_contrast" in features
        assert "chroma" in features
        
        # Check feature dimensions
        n_frames = 1 + (len(sample_audio) - feature_extractor.n_fft) // feature_extractor.hop_length
        assert features["mel_spectrogram"].shape[0] == feature_extractor.n_mels
        assert features["mel_spectrogram"].shape[1] == n_frames
        assert features["mfcc"].shape[0] == 20  # n_mfcc
        assert features["chroma"].shape[0] == 12  # number of chroma bands
        
    def test_extract_features_stereo(self, feature_extractor):
        """Test feature extraction with stereo audio."""
        # Create stereo signal
        stereo_audio = np.random.rand(22050, 2)  # 1 second of random stereo audio
        features = feature_extractor.extract_features(stereo_audio)
        
        assert all(isinstance(feat, np.ndarray) for feat in features.values())
        
    def test_extract_features_invalid_input(self, feature_extractor):
        """Test feature extraction with invalid input."""
        with pytest.raises(TypeError):
            feature_extractor.extract_features([1, 2, 3])  # not numpy array
            
        with pytest.raises(ValueError):
            feature_extractor.extract_features(np.array([]))  # empty array

class TestMusicDetection:
    """Test music detection functionality."""
    
    def test_is_music_detection(self, feature_extractor, sample_audio):
        """Test music detection with sample audio."""
        features = feature_extractor.extract_features(sample_audio)
        is_music, confidence = feature_extractor.is_music(features)
        
        assert isinstance(is_music, bool)
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1
        
    def test_is_music_missing_features(self, feature_extractor):
        """Test music detection with missing features."""
        incomplete_features = {
            "mel_spectrogram": np.random.rand(128, 100),
            "mfcc": np.random.rand(20, 100)
            # missing spectral_contrast and chroma
        }
        
        with pytest.raises(ValueError):
            feature_extractor.is_music(incomplete_features)
            
    def test_is_music_invalid_features(self, feature_extractor):
        """Test music detection with invalid feature types."""
        invalid_features = {
            "mel_spectrogram": [1, 2, 3],  # not numpy array
            "mfcc": np.random.rand(20, 100),
            "spectral_contrast": np.random.rand(7, 100),
            "chroma": np.random.rand(12, 100)
        }
        
        with pytest.raises(TypeError):
            feature_extractor.is_music(invalid_features)

class TestAudioDuration:
    """Test audio duration calculation."""
    
    def test_get_audio_duration(self, feature_extractor):
        """Test duration calculation for various audio lengths."""
        # Test 1-second audio
        audio_1s = np.random.rand(22050)
        duration = feature_extractor.get_audio_duration(audio_1s)
        assert np.isclose(duration, 1.0)
        
        # Test 2-second stereo audio
        audio_2s = np.random.rand(44100, 2)
        duration = feature_extractor.get_audio_duration(audio_2s)
        assert np.isclose(duration, 2.0)
        
    def test_get_audio_duration_invalid(self, feature_extractor):
        """Test duration calculation with invalid input."""
        with pytest.raises(TypeError):
            feature_extractor.get_audio_duration([1, 2, 3])  # not numpy array
            
        with pytest.raises(ValueError):
            feature_extractor.get_audio_duration(np.array([]))  # empty array

@pytest.mark.benchmark
class TestFeatureExtractorPerformance:
    """Performance tests for FeatureExtractor."""
    
    def test_feature_extraction_performance(self, feature_extractor, benchmark):
        """Benchmark feature extraction performance."""
        # Generate 10 seconds of audio
        duration = 10.0
        sample_rate = 22050
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * 440 * t)
        
        def extract_features():
            return feature_extractor.extract_features(audio)
            
        result = benchmark(extract_features)
        assert isinstance(result, dict)
        
    def test_music_detection_performance(self, feature_extractor, benchmark):
        """Benchmark music detection performance."""
        # Generate features for benchmarking
        audio = np.random.rand(22050)  # 1 second of random audio
        features = feature_extractor.extract_features(audio)
        
        def detect_music():
            return feature_extractor.is_music(features)
            
        result = benchmark(detect_music)
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float) 