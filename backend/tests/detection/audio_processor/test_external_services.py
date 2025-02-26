"""Tests for the external services module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import os
import aiohttp
import musicbrainzngs
from backend.detection.audio_processor.external_services import ExternalServiceHandler
from backend.detection.audio_processor.audio_analysis import AudioAnalyzer

@pytest.fixture
def mock_audio_data():
    """Create mock audio data for testing."""
    return b"mock_audio_data"

@pytest.fixture
def handler():
    """Create an ExternalServiceHandler instance for testing."""
    return ExternalServiceHandler('test_key')

@pytest.mark.asyncio
async def test_initialize(handler):
    """Test handler initialization."""
    assert not handler.initialized
    await handler.initialize()
    assert handler.initialized
    assert handler.audd_api_key == 'test_key'

@pytest.mark.asyncio
async def test_initialize_no_api_key():
    """Test initialization without API key."""
    handler = ExternalServiceHandler(None)
    await handler.initialize()
    assert handler.initialized
    assert handler.audd_api_key is None

@pytest.mark.asyncio
async def test_recognize_with_musicbrainz(handler, mock_audio_data):
    """Test music recognition with MusicBrainz."""
    mock_features = {'tempo': 120, 'key': 'C'}
    mock_duration = 180.0
    
    # Mock feature extraction and duration calculation
    with patch.object(AudioAnalyzer, 'extract_features', return_value=mock_features):
        with patch.object(AudioAnalyzer, 'calculate_duration', return_value=mock_duration):
            # Mock MusicBrainz response
            mock_mb_result = {
                'recording-list': [{
                    'id': 'mb-123',
                    'title': 'Test Track',
                    'artist-credit-phrase': 'Test Artist',
                    'release-list': [{
                        'title': 'Test Album',
                        'date': '2024-01-01'
                    }]
                }]
            }
            
            with patch.object(musicbrainzngs, 'search_recordings', 
                            return_value=mock_mb_result):
                result = await handler.recognize_with_musicbrainz(mock_audio_data)
                
                assert result is not None
                assert result['title'] == 'Test Track'
                assert result['artist'] == 'Test Artist'
                assert result['duration'] == 180.0
                assert result['confidence'] == 0.7
                assert result['source'] == 'musicbrainz'
                assert result['external_id'] == 'mb-123'
                assert result['metadata']['release'] == 'Test Album'
                assert result['metadata']['year'] == '2024'

@pytest.mark.asyncio
async def test_recognize_with_musicbrainz_no_results(handler, mock_audio_data):
    """Test MusicBrainz recognition with no results."""
    with patch.object(AudioAnalyzer, 'extract_features'):
        with patch.object(AudioAnalyzer, 'calculate_duration'):
            with patch.object(musicbrainzngs, 'search_recordings', 
                            return_value={'recording-list': []}):
                result = await handler.recognize_with_musicbrainz(mock_audio_data)
                assert result is None

@pytest.mark.asyncio
async def test_recognize_with_audd_success(handler, mock_audio_data):
    """Test music recognition with Audd API success."""
    mock_response = {
        'status': 'success',
        'result': {
            'title': 'Audd Track',
            'artist': 'Audd Artist',
            'album': 'Audd Album',
            'release_date': '2024-02-01',
            'label': 'Test Label',
            'song_id': 'audd-123'
        }
    }
    
    mock_response_obj = AsyncMock()
    mock_response_obj.status = 200
    mock_response_obj.json.return_value = mock_response
    
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response_obj
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        with patch('tempfile.NamedTemporaryFile'):
            with patch('os.unlink'):
                result = await handler.recognize_with_audd(mock_audio_data)
                
                assert result is not None
                assert result['title'] == 'Audd Track'
                assert result['artist'] == 'Audd Artist'
                assert result['source'] == 'audd'
                assert result['confidence'] == 0.9
                assert result['external_id'] == 'audd-123'
                assert result['metadata']['release'] == 'Audd Album'
                assert result['metadata']['label'] == 'Test Label'

@pytest.mark.asyncio
async def test_recognize_with_audd_no_api_key(mock_audio_data):
    """Test Audd recognition without API key."""
    handler = ExternalServiceHandler(None)
    result = await handler.recognize_with_audd(mock_audio_data)
    assert result is None

@pytest.mark.asyncio
async def test_recognize_with_audd_api_error(handler, mock_audio_data):
    """Test Audd recognition with API error."""
    mock_response = AsyncMock()
    mock_response.status = 400
    
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        with patch('tempfile.NamedTemporaryFile'):
            with patch('os.unlink'):
                result = await handler.recognize_with_audd(mock_audio_data)
                assert result is None

@pytest.mark.asyncio
async def test_recognize_with_audd_no_match(handler, mock_audio_data):
    """Test Audd recognition with no match."""
    mock_response = {
        'status': 'success',
        'result': None
    }
    
    mock_response_obj = AsyncMock()
    mock_response_obj.status = 200
    mock_response_obj.json.return_value = mock_response
    
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response_obj
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        with patch('tempfile.NamedTemporaryFile'):
            with patch('os.unlink'):
                result = await handler.recognize_with_audd(mock_audio_data)
                assert result is None

@pytest.mark.asyncio
async def test_error_handling(handler, mock_audio_data):
    """Test error handling in external services."""
    with patch.object(AudioAnalyzer, 'extract_features', 
                     side_effect=Exception("Test error")):
        result = await handler.recognize_with_musicbrainz(mock_audio_data)
        assert result is None 