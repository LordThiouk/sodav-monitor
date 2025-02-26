import pytest
from unittest.mock import Mock, patch
import numpy as np
from backend.detection.audio_processor.core import AudioProcessor
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.feature_extractor import FeatureExtractor

@pytest.fixture
def mock_audio_data():
    """Generate mock audio data for testing"""
    return np.random.rand(44100 * 5)  # 5 seconds of random audio

@pytest.fixture
def mock_feature_extractor():
    with patch('backend.detection.audio_processor.feature_extractor.FeatureExtractor') as mock:
        extractor = Mock()
        extractor.extract_features = Mock(return_value={
            'mfcc': np.random.rand(20, 87),
            'spectral_contrast': np.random.rand(7, 87),
            'chroma': np.random.rand(12, 87)
        })
        mock.return_value = extractor
        yield extractor

@pytest.fixture
def mock_track_manager():
    with patch('backend.detection.audio_processor.track_manager.TrackManager') as mock:
        manager = Mock()
        manager.find_local_match = Mock(return_value=None)
        manager.save_track = Mock()
        mock.return_value = manager
        yield manager

@pytest.fixture
def audio_processor(mock_feature_extractor, mock_track_manager):
    return AudioProcessor()

def test_detect_music_vs_speech(audio_processor, mock_audio_data):
    """Test differentiation between music and speech content"""
    # Test music detection
    with patch('backend.detection.audio_processor.core.AudioProcessor._is_music', return_value=True):
        result = audio_processor.analyze_content_type(mock_audio_data)
        assert result == 'music'
    
    # Test speech detection
    with patch('backend.detection.audio_processor.core.AudioProcessor._is_music', return_value=False):
        result = audio_processor.analyze_content_type(mock_audio_data)
        assert result == 'speech'

def test_local_detection_success(audio_processor, mock_audio_data, mock_track_manager):
    """Test successful local track detection"""
    mock_track = {
        'id': '123',
        'title': 'Test Track',
        'artist': 'Test Artist',
        'confidence': 0.95
    }
    mock_track_manager.find_local_match.return_value = mock_track
    
    result = audio_processor.detect_track(mock_audio_data)
    assert result == mock_track
    assert result['confidence'] >= 0.8  # Local detection confidence threshold

def test_musicbrainz_fallback(audio_processor, mock_audio_data, mock_track_manager):
    """Test MusicBrainz fallback when local detection fails"""
    mock_track = {
        'id': '123',
        'title': 'Test Track',
        'artist': 'Test Artist',
        'confidence': 0.85
    }
    
    # Local detection returns None
    mock_track_manager.find_local_match.return_value = None
    
    # MusicBrainz detection succeeds
    with patch('backend.detection.audio_processor.core.AudioProcessor._detect_with_musicbrainz',
              return_value=mock_track):
        result = audio_processor.detect_track(mock_audio_data)
        assert result == mock_track
        assert result['confidence'] >= 0.7  # MusicBrainz confidence threshold

def test_audd_fallback(audio_processor, mock_audio_data, mock_track_manager):
    """Test Audd fallback when both local and MusicBrainz detection fail"""
    mock_track = {
        'id': '123',
        'title': 'Test Track',
        'artist': 'Test Artist',
        'confidence': 0.75
    }
    
    # Local detection returns None
    mock_track_manager.find_local_match.return_value = None
    
    # MusicBrainz detection fails
    with patch('backend.detection.audio_processor.core.AudioProcessor._detect_with_musicbrainz',
              return_value=None):
        # Audd detection succeeds
        with patch('backend.detection.audio_processor.core.AudioProcessor._detect_with_audd',
                  return_value=mock_track):
            result = audio_processor.detect_track(mock_audio_data)
            assert result == mock_track
            assert result['confidence'] >= 0.6  # Audd confidence threshold

def test_all_detection_methods_fail(audio_processor, mock_audio_data, mock_track_manager):
    """Test behavior when all detection methods fail"""
    # Local detection returns None
    mock_track_manager.find_local_match.return_value = None
    
    # MusicBrainz detection fails
    with patch('backend.detection.audio_processor.core.AudioProcessor._detect_with_musicbrainz',
              return_value=None):
        # Audd detection fails
        with patch('backend.detection.audio_processor.core.AudioProcessor._detect_with_audd',
                  return_value=None):
            result = audio_processor.detect_track(mock_audio_data)
            assert result is None

def test_low_confidence_results(audio_processor, mock_audio_data, mock_track_manager):
    """Test handling of low confidence detection results"""
    low_confidence_track = {
        'id': '123',
        'title': 'Test Track',
        'artist': 'Test Artist',
        'confidence': 0.3  # Below all thresholds
    }
    
    # Local detection returns low confidence result
    mock_track_manager.find_local_match.return_value = low_confidence_track
    
    # Should continue to MusicBrainz
    with patch('backend.detection.audio_processor.core.AudioProcessor._detect_with_musicbrainz',
              return_value=None):
        # Should continue to Audd
        with patch('backend.detection.audio_processor.core.AudioProcessor._detect_with_audd',
                  return_value=None):
            result = audio_processor.detect_track(mock_audio_data)
            assert result is None

def test_feature_extraction(audio_processor, mock_audio_data, mock_feature_extractor):
    """Test audio feature extraction"""
    features = audio_processor.extract_features(mock_audio_data)
    assert 'mfcc' in features
    assert 'spectral_contrast' in features
    assert 'chroma' in features
    mock_feature_extractor.extract_features.assert_called_once_with(mock_audio_data)

def test_error_handling(audio_processor, mock_audio_data):
    """Test error handling in the detection process"""
    # Test invalid audio data
    with pytest.raises(ValueError):
        audio_processor.detect_track(None)
    
    # Test processing error
    with patch('backend.detection.audio_processor.core.AudioProcessor.extract_features',
              side_effect=Exception("Processing error")):
        with pytest.raises(Exception, match="Processing error"):
            audio_processor.detect_track(mock_audio_data)

@pytest.mark.asyncio
async def test_async_detection(audio_processor, mock_audio_data):
    """Test asynchronous track detection"""
    mock_track = {
        'id': '123',
        'title': 'Test Track',
        'artist': 'Test Artist',
        'confidence': 0.95
    }
    
    with patch('backend.detection.audio_processor.core.AudioProcessor.detect_track',
              return_value=mock_track):
        result = await audio_processor.detect_track_async(mock_audio_data)
        assert result == mock_track

def test_detection_with_missing_api_keys(audio_processor, mock_audio_data):
    """Test detection behavior when API keys are missing"""
    # Local detection returns None
    mock_track_manager.find_local_match.return_value = None
    
    # Test missing ACOUSTID_API_KEY
    with patch('os.getenv', return_value=None):
        with pytest.raises(ValueError, match="Missing ACOUSTID_API_KEY"):
            audio_processor._detect_with_musicbrainz(mock_audio_data)
    
    # Test missing AUDD_API_KEY
    with patch('os.getenv', return_value=None):
        with pytest.raises(ValueError, match="Missing AUDD_API_KEY"):
            audio_processor._detect_with_audd(mock_audio_data) 