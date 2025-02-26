"""Tests for the Feature Extractor component."""

import pytest
import numpy as np
from unittest.mock import Mock, patch
import librosa

from detection.audio_processor.feature_extractor import FeatureExtractor

@pytest.fixture
def feature_extractor():
    """Create a FeatureExtractor instance for testing."""
    return FeatureExtractor()

@pytest.fixture
def sample_audio_data():
    """Generate sample audio data for testing."""
    # Generate 1 second of audio at 44.1kHz
    return np.random.random(44100)

def test_init_feature_extractor():
    """Test FeatureExtractor initialization."""
    extractor = FeatureExtractor()
    assert extractor is not None
    assert hasattr(extractor, 'extract_features')
    assert hasattr(extractor, 'is_music')

@pytest.mark.asyncio
async def test_extract_features_valid_audio(feature_extractor, sample_audio_data):
    """Test feature extraction with valid audio data."""
    features = await feature_extractor.extract_features(sample_audio_data)
    
    assert isinstance(features, dict)
    assert 'mfcc' in features
    assert 'spectral_centroid' in features
    assert 'zero_crossing_rate' in features
    assert isinstance(features['mfcc'], np.ndarray)

@pytest.mark.asyncio
async def test_extract_features_empty_audio(feature_extractor):
    """Test feature extraction with empty audio data."""
    with pytest.raises(ValueError, match="Audio data is empty"):
        await feature_extractor.extract_features(np.array([]))

@pytest.mark.asyncio
async def test_extract_features_invalid_audio(feature_extractor):
    """Test feature extraction with invalid audio data."""
    with pytest.raises(ValueError, match="Invalid audio data"):
        await feature_extractor.extract_features(None)

@pytest.mark.asyncio
async def test_is_music_with_music(feature_extractor):
    """Test music detection with musical audio."""
    # Mock musical features
    mock_features = {
        'mfcc': np.random.random((20, 10)),
        'spectral_centroid': np.array([2000] * 100),  # Higher centroid typical for music
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
        'mfcc': np.random.random((20, 10)),
        'spectral_centroid': np.array([500] * 100),   # Lower centroid typical for speech
        'zero_crossing_rate': np.array([0.5] * 100)   # Higher ZCR typical for speech
    }
    
    with patch.object(feature_extractor, 'extract_features', return_value=mock_features):
        is_music = await feature_extractor.is_music(np.random.random(44100))
        assert is_music is False

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

@pytest.mark.asyncio
async def test_feature_extraction_performance(feature_extractor):
    """Test performance of feature extraction."""
    # Generate 10 seconds of audio
    long_audio = np.random.random(441000)
    
    with patch('time.time') as mock_time:
        mock_time.side_effect = [0, 2]  # Simulate 2 seconds processing time
        features = await feature_extractor.extract_features(long_audio)
        
        assert isinstance(features, dict)
        assert all(isinstance(feat, np.ndarray) for feat in features.values())

@pytest.mark.asyncio
async def test_feature_extraction_memory(feature_extractor):
    """Test memory usage during feature extraction."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Process 5 seconds of audio
    audio = np.random.random(220500)
    features = await feature_extractor.extract_features(audio)
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Ensure memory usage increase is reasonable (less than 100MB)
    assert memory_increase < 100 * 1024 * 1024  # 100MB in bytes 