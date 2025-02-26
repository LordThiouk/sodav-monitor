"""Tests for the recognition core module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import os
import musicbrainzngs
from sqlalchemy.orm import Session

from backend.detection.audio_processor.recognition_core import MusicRecognizer
from backend.detection.audio_processor.local_detection import LocalDetector
from backend.detection.audio_processor.external_services import ExternalServiceHandler
from backend.detection.audio_processor.db_operations import DatabaseHandler
from backend.detection.audio_processor.audio_analysis import AudioAnalyzer

@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    return Mock(spec=Session)

@pytest.fixture
def mock_audio_data():
    """Create mock audio data for testing."""
    return b"mock_audio_data"

@pytest.fixture
def mock_track_info():
    """Create mock track information."""
    return {
        'title': 'Test Track',
        'artist': 'Test Artist',
        'duration': 180.0,
        'confidence': 0.9,
        'source': 'local'
    }

@pytest.fixture
async def recognizer(db_session):
    """Create a MusicRecognizer instance for testing."""
    with patch.dict(os.environ, {'AUDD_API_KEY': 'test_key'}):
        # Create mock components
        mock_local_detector = AsyncMock(spec=LocalDetector)
        mock_external_handler = AsyncMock(spec=ExternalServiceHandler)
        mock_db_handler = AsyncMock(spec=DatabaseHandler)
        mock_audio_analyzer = Mock(spec=AudioAnalyzer)
        
        # Create recognizer
        recognizer = MusicRecognizer(db_session)
        
        # Set mock components
        recognizer.local_detector = mock_local_detector
        recognizer.external_handler = mock_external_handler
        recognizer.db_handler = mock_db_handler
        recognizer.audio_analyzer = mock_audio_analyzer
        
        # Initialize mocks
        mock_local_detector.initialize = AsyncMock()
        mock_external_handler.initialize = AsyncMock()
        mock_db_handler.initialize = AsyncMock()
        mock_local_detector.search_local = AsyncMock()
        mock_external_handler.recognize_with_musicbrainz = AsyncMock()
        mock_external_handler.recognize_with_audd = AsyncMock()
        mock_db_handler.save_track_to_db = AsyncMock()
        mock_db_handler.verify_detections = AsyncMock()
        
        # Set initialized flag
        recognizer.initialized = True
        
        return recognizer

@pytest.mark.asyncio
async def test_initialize(recognizer):
    """Test recognizer initialization."""
    # Reset initialized flag
    recognizer.initialized = False
    
    await recognizer.initialize()
    assert recognizer.initialized
    
    # Verify components are initialized
    assert recognizer.local_detector is not None
    assert recognizer.external_handler is not None
    assert recognizer.db_handler is not None
    assert recognizer.audio_analyzer is not None
    
    # Verify initialize was called
    recognizer.local_detector.initialize.assert_awaited_once()
    recognizer.external_handler.initialize.assert_awaited_once()
    recognizer.db_handler.initialize.assert_awaited_once()

@pytest.mark.asyncio
async def test_recognize_music_local_match(recognizer, mock_audio_data, mock_track_info):
    """Test music recognition with local database match."""
    # Set up mock return values
    recognizer.local_detector.search_local.return_value = mock_track_info
    
    result = await recognizer.recognize_music(mock_audio_data)
    
    assert result == mock_track_info
    assert result['source'] == 'local'
    assert result['confidence'] == 0.9
    
    recognizer.local_detector.search_local.assert_awaited_once_with(mock_audio_data)
    recognizer.external_handler.recognize_with_musicbrainz.assert_not_awaited()
    recognizer.external_handler.recognize_with_audd.assert_not_awaited()

@pytest.mark.asyncio
async def test_recognize_music_musicbrainz_match(recognizer, mock_audio_data):
    """Test music recognition with MusicBrainz match."""
    mock_mb_result = {
        'title': 'MB Track',
        'artist': 'MB Artist',
        'duration': 200.0,
        'confidence': 0.7,
        'source': 'musicbrainz'
    }
    
    # Set up mock return values
    recognizer.local_detector.search_local.return_value = None
    recognizer.external_handler.recognize_with_musicbrainz.return_value = mock_mb_result
    
    result = await recognizer.recognize_music(mock_audio_data)
    
    assert result == mock_mb_result
    assert result['source'] == 'musicbrainz'
    assert result['confidence'] == 0.7
    
    recognizer.local_detector.search_local.assert_awaited_once_with(mock_audio_data)
    recognizer.external_handler.recognize_with_musicbrainz.assert_awaited_once_with(mock_audio_data)
    recognizer.external_handler.recognize_with_audd.assert_not_awaited()

@pytest.mark.asyncio
async def test_recognize_music_audd_match(recognizer, mock_audio_data):
    """Test music recognition with Audd match."""
    mock_audd_result = {
        'title': 'Audd Track',
        'artist': 'Audd Artist',
        'duration': 220.0,
        'confidence': 0.9,
        'source': 'audd'
    }
    
    # Set up mock return values
    recognizer.local_detector.search_local.return_value = None
    recognizer.external_handler.recognize_with_musicbrainz.return_value = None
    recognizer.external_handler.recognize_with_audd.return_value = mock_audd_result
    
    result = await recognizer.recognize_music(mock_audio_data)
    
    assert result == mock_audd_result
    assert result['source'] == 'audd'
    assert result['confidence'] == 0.9
    
    recognizer.local_detector.search_local.assert_awaited_once_with(mock_audio_data)
    recognizer.external_handler.recognize_with_musicbrainz.assert_awaited_once_with(mock_audio_data)
    recognizer.external_handler.recognize_with_audd.assert_awaited_once_with(mock_audio_data)

@pytest.mark.asyncio
async def test_recognize_music_no_match(recognizer, mock_audio_data):
    """Test music recognition with no matches."""
    # Set up mock return values
    recognizer.local_detector.search_local.return_value = None
    recognizer.external_handler.recognize_with_musicbrainz.return_value = None
    recognizer.external_handler.recognize_with_audd.return_value = None
    
    result = await recognizer.recognize_music(mock_audio_data)
    assert result is None
    
    recognizer.local_detector.search_local.assert_awaited_once_with(mock_audio_data)
    recognizer.external_handler.recognize_with_musicbrainz.assert_awaited_once_with(mock_audio_data)
    recognizer.external_handler.recognize_with_audd.assert_awaited_once_with(mock_audio_data)

@pytest.mark.asyncio
async def test_verify_detections(recognizer):
    """Test detection verification."""
    start_time = datetime.now()
    end_time = datetime.now()
    
    await recognizer.verify_detections(start_time, end_time)
    recognizer.db_handler.verify_detections.assert_awaited_once_with(start_time, end_time)

@pytest.mark.asyncio
async def test_error_handling(recognizer, mock_audio_data):
    """Test error handling during recognition."""
    # Set up mock to raise exception
    recognizer.local_detector.search_local.side_effect = Exception("Test error")
    
    result = await recognizer.recognize_music(mock_audio_data)
    assert result is None
    
    recognizer.local_detector.search_local.assert_awaited_once_with(mock_audio_data)
    recognizer.external_handler.recognize_with_musicbrainz.assert_not_awaited()
    recognizer.external_handler.recognize_with_audd.assert_not_awaited()

@pytest.mark.asyncio
async def test_initialize_with_invalid_api_key(db_session):
    """Test initialization with invalid API key."""
    with patch.dict(os.environ, {'AUDD_API_KEY': ''}):
        # Create mock components
        mock_local_detector = AsyncMock(spec=LocalDetector)
        mock_external_handler = AsyncMock(spec=ExternalServiceHandler)
        mock_db_handler = AsyncMock(spec=DatabaseHandler)
        mock_audio_analyzer = Mock(spec=AudioAnalyzer)
        
        # Create recognizer
        recognizer = MusicRecognizer(db_session)
        
        # Set mock components
        recognizer.local_detector = mock_local_detector
        recognizer.external_handler = mock_external_handler
        recognizer.db_handler = mock_db_handler
        recognizer.audio_analyzer = mock_audio_analyzer
        
        # Initialize mocks
        mock_local_detector.initialize = AsyncMock()
        mock_external_handler.initialize = AsyncMock()
        mock_db_handler.initialize = AsyncMock()
        
        await recognizer.initialize()
        assert recognizer.initialized
        # Should still initialize even without API key

@pytest.mark.asyncio
async def test_recognition_with_low_confidence(recognizer, mock_audio_data):
    """Test recognition with low confidence results."""
    low_confidence_result = {
        'title': 'Low Confidence Track',
        'artist': 'Test Artist',
        'duration': 180.0,
        'confidence': 0.3,  # Low confidence
        'source': 'local'
    }
    
    # Set up mock return values
    recognizer.local_detector.search_local.return_value = low_confidence_result
    
    result = await recognizer.recognize_music(mock_audio_data)
    assert result is None  # Should reject low confidence matches
    
    recognizer.local_detector.search_local.assert_awaited_once_with(mock_audio_data)
    recognizer.external_handler.recognize_with_musicbrainz.assert_not_awaited()
    recognizer.external_handler.recognize_with_audd.assert_not_awaited()

@pytest.mark.asyncio
async def test_save_recognized_track(recognizer, mock_audio_data, mock_track_info):
    """Test saving recognized track to database."""
    # Set up mock return values
    recognizer.local_detector.search_local.return_value = None
    recognizer.external_handler.recognize_with_musicbrainz.return_value = mock_track_info
    
    result = await recognizer.recognize_music(mock_audio_data)
    
    assert result == mock_track_info
    recognizer.db_handler.save_track_to_db.assert_awaited_once_with(mock_track_info) 