"""Tests for the FeatureExtractor class."""

import pytest
import numpy as np
from unittest.mock import patch
from backend.detection.audio_processor.feature_extractor import FeatureExtractor

class TestFeatureExtractorInitialization:
    """Test FeatureExtractor initialization."""
    
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
    
    def test_extract_features_shape(self, sample_audio_data, mock_librosa):
        """Test the shape of extracted features."""
        with patch('backend.detection.audio_processor.feature_extractor.librosa', mock_librosa):
            extractor = FeatureExtractor()
            features = extractor.extract_features(sample_audio_data)
            
            assert "mel_spectrogram" in features
            assert "mfcc" in features
            assert "spectral_contrast" in features
            assert "chroma" in features
            
            # Check feature dimensions
            n_frames = 100  # Expected number of frames from mock librosa
            assert isinstance(features["mel_spectrogram"], np.ndarray)
            assert features["mel_spectrogram"].shape == (128, n_frames)
            assert features["mfcc"].shape == (20, n_frames)
            assert features["spectral_contrast"].shape == (7, n_frames)
            assert features["chroma"].shape == (12, n_frames)
    
    def test_extract_features_stereo(self, sample_stereo_audio, mock_librosa):
        """Test feature extraction with stereo audio."""
        with patch('backend.detection.audio_processor.feature_extractor.librosa', mock_librosa):
            extractor = FeatureExtractor()
            features = extractor.extract_features(sample_stereo_audio)
            
            # Should convert to mono internally
            mock_librosa.feature.melspectrogram.assert_called_once()
            assert isinstance(features["mel_spectrogram"], np.ndarray)
            assert features["mel_spectrogram"].shape == (128, 100)
            assert features["mfcc"].shape == (20, 100)
            assert features["spectral_contrast"].shape == (7, 100)
            assert features["chroma"].shape == (12, 100)
    
    def test_extract_features_invalid_input(self):
        """Test feature extraction with invalid input."""
        extractor = FeatureExtractor()
        
        with pytest.raises(TypeError):
            extractor.extract_features([1, 2, 3])  # not numpy array
            
        with pytest.raises(ValueError):
            extractor.extract_features(np.array([]))  # empty array

class TestMusicDetection:
    """Test music detection functionality."""
    
    def test_is_music_detection_music(self, sample_music_data, mock_librosa):
        """Test music detection with music-like audio."""
        with patch('backend.detection.audio_processor.feature_extractor.librosa', mock_librosa):
            extractor = FeatureExtractor()
            features = extractor.extract_features(sample_music_data)
            is_music, confidence = extractor.is_music(features)
            
            assert isinstance(is_music, bool)
            assert isinstance(confidence, float)
            assert 0 <= confidence <= 1
            assert is_music is True  # Should detect as music
            assert confidence > 0.6  # Adjusted threshold for music
    
    def test_is_music_detection_speech(self, sample_speech_data, mock_librosa):
        """Test music detection with speech-like audio."""
        with patch('backend.detection.audio_processor.feature_extractor.librosa', mock_librosa):
            extractor = FeatureExtractor()
            features = extractor.extract_features(sample_speech_data)
            is_music, confidence = extractor.is_music(features)
            
            assert isinstance(is_music, bool)
            assert isinstance(confidence, float)
            assert 0 <= confidence <= 1
            assert confidence < 0.7  # Lower confidence for speech
            assert is_music == (confidence > 0.6)  # Music if confidence > 0.6
    
    def test_is_music_detection_noise(self, mock_librosa):
        """Test music detection with noise."""
        with patch('backend.detection.audio_processor.feature_extractor.librosa', mock_librosa):
            extractor = FeatureExtractor()
            noise = np.random.normal(0, 0.1, 22050)  # Reduced amplitude noise
            features = extractor.extract_features(noise)
            is_music, confidence = extractor.is_music(features)
            
            assert isinstance(is_music, bool)
            assert isinstance(confidence, float)
            assert 0 <= confidence <= 1
            assert confidence < 0.7  # Lower confidence for noise
            assert is_music == (confidence > 0.6)  # Music if confidence > 0.6
    
    def test_is_music_detection_edge_cases(self, mock_librosa):
        """Test music detection with edge cases."""
        with patch('backend.detection.audio_processor.feature_extractor.librosa', mock_librosa):
            extractor = FeatureExtractor()
            
            # Test with silence
            silence = np.zeros(22050)
            features = extractor.extract_features(silence)
            is_music, confidence = extractor.is_music(features)
            assert confidence < 0.7  # Low confidence for silence
            assert is_music == (confidence > 0.6)  # Music if confidence > 0.6
            
            # Test with very short audio
            short_audio = np.random.rand(1000)
            features = extractor.extract_features(short_audio)
            is_music, confidence = extractor.is_music(features)
            assert isinstance(is_music, bool)
            assert 0 <= confidence <= 1
    
    def test_is_music_missing_features(self):
        """Test music detection with missing features."""
        extractor = FeatureExtractor()
        incomplete_features = {
            "mel_spectrogram": np.random.rand(128, 100),
            "mfcc": np.random.rand(20, 100)
            # missing spectral_contrast and chroma
        }
        
        with pytest.raises(ValueError):
            extractor.is_music(incomplete_features)
    
    def test_is_music_invalid_features(self):
        """Test music detection with invalid feature types."""
        extractor = FeatureExtractor()
        invalid_features = {
            "mel_spectrogram": [1, 2, 3],  # not numpy array
            "mfcc": np.random.rand(20, 100),
            "spectral_contrast": np.random.rand(7, 100),
            "chroma": np.random.rand(12, 100)
        }
        
        with pytest.raises(TypeError):
            extractor.is_music(invalid_features)

class TestAudioDuration:
    """Test audio duration calculation."""
    
    def test_get_audio_duration(self):
        """Test duration calculation for various audio lengths."""
        extractor = FeatureExtractor()
        
        # Test 1-second audio
        audio_1s = np.random.rand(22050)
        duration = extractor.get_audio_duration(audio_1s)
        assert np.isclose(duration, 1.0)
        
        # Test 2-second stereo audio
        audio_2s = np.random.rand(44100, 2)
        duration = extractor.get_audio_duration(audio_2s)
        assert np.isclose(duration, 2.0)
    
    def test_get_audio_duration_invalid(self):
        """Test duration calculation with invalid input."""
        extractor = FeatureExtractor()
        
        with pytest.raises(TypeError):
            extractor.get_audio_duration([1, 2, 3])  # not numpy array
            
        with pytest.raises(ValueError):
            extractor.get_audio_duration(np.array([]))  # empty array

@pytest.mark.benchmark
class TestFeatureExtractorPerformance:
    """Performance tests for FeatureExtractor."""
    
    def test_feature_extraction_performance(self, benchmark, sample_audio_data, mock_librosa):
        """Benchmark feature extraction performance."""
        with patch('backend.detection.audio_processor.feature_extractor.librosa', mock_librosa):
            extractor = FeatureExtractor()
            
            def extract_features():
                return extractor.extract_features(sample_audio_data)
            
            result = benchmark(extract_features)
            assert isinstance(result, dict)
            assert len(result) == 4  # All features present
    
    def test_music_detection_performance(self, benchmark, mock_librosa):
        """Benchmark music detection performance."""
        with patch('backend.detection.audio_processor.feature_extractor.librosa', mock_librosa):
            extractor = FeatureExtractor()
            features = {
                "mel_spectrogram": np.random.rand(128, 100),
                "mfcc": np.random.rand(20, 100),
                "spectral_contrast": np.random.rand(7, 100),
                "chroma": np.random.rand(12, 100)
            }
            
            def detect_music():
                return extractor.is_music(features)
            
            result = benchmark(detect_music)
            assert isinstance(result[0], bool)
            assert isinstance(result[1], float)
            assert 0 <= result[1] <= 1
    
    def test_memory_usage(self, benchmark, sample_audio_data, mock_librosa):
        """Test memory usage during feature extraction."""
        import psutil
        import os
        
        with patch('backend.detection.audio_processor.feature_extractor.librosa', mock_librosa):
            extractor = FeatureExtractor()
            process = psutil.Process(os.getpid())
            
            def measure_memory():
                initial = process.memory_info().rss
                features = extractor.extract_features(sample_audio_data)
                final = process.memory_info().rss
                return (final - initial) / 1024 / 1024  # MB
            
            memory_increase = benchmark(measure_memory)
            assert memory_increase < 100  # Should use less than 100MB additional memory 