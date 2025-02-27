"""Tests for the Feature Extractor module."""

import pytest
import numpy as np
from unittest.mock import Mock, patch
import librosa

from ...detection.audio_processor.feature_extractor import FeatureExtractor

@pytest.fixture
def feature_extractor():
    """Create a FeatureExtractor instance for testing."""
    return FeatureExtractor()

@pytest.fixture
def mock_audio_data():
    """Create mock audio data for testing."""
    # Generate 1 second of audio at 44.1kHz
    return np.random.random(44100)

def test_feature_extractor_initialization():
    """Test FeatureExtractor initialization."""
    extractor = FeatureExtractor()
    assert extractor is not None
    assert hasattr(extractor, 'extract_features')
    assert hasattr(extractor, 'is_music')

@pytest.mark.asyncio
async def test_extract_features(feature_extractor, mock_audio_data):
    """Test feature extraction from audio data."""
    features = await feature_extractor.extract_features(mock_audio_data)
    
    # Verify all expected features are present
    assert 'mfcc' in features
    assert 'spectral_centroid' in features
    assert 'spectral_rolloff' in features
    assert 'zero_crossing_rate' in features
    
    # Verify feature shapes
    assert features['mfcc'].shape[1] == 13  # Standard number of MFCC coefficients
    assert features['spectral_centroid'].shape[0] > 0
    assert features['spectral_rolloff'].shape[0] > 0
    assert features['zero_crossing_rate'].shape[0] > 0

@pytest.mark.asyncio
async def test_is_music_with_music(feature_extractor):
    """Test music detection with musical audio."""
    # Mock musical features
    mock_features = {
        'mfcc': np.random.random((100, 13)),
        'spectral_centroid': np.array([2000] * 100),  # Higher centroid typical for music
        'spectral_rolloff': np.array([0.85] * 100),   # Higher rolloff typical for music
        'zero_crossing_rate': np.array([0.1] * 100)   # Lower ZCR typical for music
    }
    
    with patch.object(feature_extractor, 'extract_features', return_value=mock_features):
        is_music = await feature_extractor.is_music(np.random.random(44100))
        assert is_music is True

@pytest.mark.asyncio
async def test_is_music_with_speech(feature_extractor):
    """Test music detection with speech audio."""
    # Mock speech features
    mock_features = {
        'mfcc': np.random.random((100, 13)),
        'spectral_centroid': np.array([1000] * 100),  # Lower centroid typical for speech
        'spectral_rolloff': np.array([0.3] * 100),    # Lower rolloff typical for speech
        'zero_crossing_rate': np.array([0.3] * 100)   # Higher ZCR typical for speech
    }
    
    with patch.object(feature_extractor, 'extract_features', return_value=mock_features):
        is_music = await feature_extractor.is_music(np.random.random(44100))
        assert is_music is False

@pytest.mark.asyncio
async def test_extract_features_with_invalid_data(feature_extractor):
    """Test feature extraction with invalid audio data."""
    with pytest.raises(ValueError):
        await feature_extractor.extract_features(np.array([]))
    
    with pytest.raises(ValueError):
        await feature_extractor.extract_features(None)

@pytest.mark.asyncio
async def test_feature_extraction_performance(feature_extractor):
    """Test performance of feature extraction."""
    # Generate 10 seconds of audio
    long_audio = np.random.random(441000)  # 10 seconds at 44.1kHz
    
    import time
    start_time = time.time()
    features = await feature_extractor.extract_features(long_audio)
    end_time = time.time()
    
    # Feature extraction should complete in a reasonable time (adjust threshold as needed)
    assert end_time - start_time < 5.0  # Should complete within 5 seconds

@pytest.mark.asyncio
async def test_feature_memory_usage(feature_extractor):
    """Test memory usage during feature extraction."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Generate and process 30 seconds of audio
    long_audio = np.random.random(1323000)  # 30 seconds at 44.1kHz
    features = await feature_extractor.extract_features(long_audio)
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Memory increase should be reasonable (adjust threshold as needed)
    assert memory_increase < 500 * 1024 * 1024  # Should use less than 500MB additional memory

@pytest.mark.asyncio
async def test_feature_extraction_with_different_sample_rates(feature_extractor):
    """Test feature extraction with different sample rates."""
    # Test with different sample rates
    sample_rates = [22050, 44100, 48000]
    
    for sr in sample_rates:
        audio_data = np.random.random(sr)  # 1 second of audio at each sample rate
        features = await feature_extractor.extract_features(audio_data, sr=sr)
        
        # Verify features are extracted correctly regardless of sample rate
        assert 'mfcc' in features
        assert 'spectral_centroid' in features
        assert features['mfcc'].shape[1] == 13

@pytest.mark.asyncio
async def test_feature_extraction_with_noise(feature_extractor):
    """Test feature extraction with noisy audio data."""
    # Generate noisy audio
    noise = np.random.normal(0, 1, 44100)
    features = await feature_extractor.extract_features(noise)
    
    assert isinstance(features, dict)
    assert all(not np.isnan(feat).any() for feat in features.values())

@pytest.mark.asyncio
async def test_feature_extraction_with_silence(feature_extractor):
    """Test feature extraction with silent audio."""
    silent_audio = np.zeros(44100)
    features = await feature_extractor.extract_features(silent_audio)
    
    assert isinstance(features, dict)
    assert all(not np.isnan(feat).any() for feat in features.values()) 