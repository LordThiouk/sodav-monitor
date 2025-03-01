"""Tests for the stream checker module."""

import pytest
import aiohttp
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from backend.utils.streams.stream_checker import StreamChecker

@pytest.fixture
def stream_checker():
    """Create a StreamChecker instance for testing."""
    return StreamChecker()

@pytest.mark.asyncio
async def test_check_stream_availability_success():
    """Test successful stream availability check."""
    checker = StreamChecker()
    mock_response = Mock()
    mock_response.status = 200
    mock_response.headers = {'content-type': 'audio/mpeg'}
    
    with patch('aiohttp.ClientSession.head', return_value=mock_response):
        result = await checker.check_stream_availability("http://test.stream")
        
        assert result['is_available'] is True
        assert result['is_audio_stream'] is True
        assert result['status_code'] == 200

@pytest.mark.asyncio
async def test_check_stream_availability_failure():
    """Test stream availability check failure."""
    checker = StreamChecker()
    
    with patch('aiohttp.ClientSession.head', side_effect=aiohttp.ClientError()):
        result = await checker.check_stream_availability("http://test.stream")
        
        assert result['is_available'] is False
        assert 'error' in result

@pytest.mark.asyncio
async def test_check_stream_non_audio():
    """Test checking a non-audio stream."""
    checker = StreamChecker()
    mock_response = Mock()
    mock_response.status = 200
    mock_response.headers = {'content-type': 'text/html'}
    
    with patch('aiohttp.ClientSession.head', return_value=mock_response):
        result = await checker.check_stream_availability("http://test.stream")
        
        assert result['is_available'] is True
        assert result['is_audio_stream'] is False

@pytest.mark.asyncio
async def test_check_stream_timeout():
    """Test stream check with timeout."""
    checker = StreamChecker()
    
    with patch('aiohttp.ClientSession.head', side_effect=asyncio.TimeoutError()):
        result = await checker.check_stream_availability("http://test.stream")
        
        assert result['is_available'] is False
        assert 'timeout' in result['error'].lower()

@pytest.mark.asyncio
async def test_check_stream_invalid_url():
    """Test checking an invalid stream URL."""
    checker = StreamChecker()
    result = await checker.check_stream_availability("invalid_url")
    
    assert result['is_available'] is False
    assert 'invalid url' in result['error'].lower()

@pytest.mark.asyncio
async def test_check_stream_retry():
    """Test stream check retry logic."""
    checker = StreamChecker()
    mock_response = Mock()
    mock_response.status = 200
    mock_response.headers = {'content-type': 'audio/mpeg'}
    
    with patch('aiohttp.ClientSession.head') as mock_head:
        # First call fails, second succeeds
        mock_head.side_effect = [
            aiohttp.ClientError(),
            mock_response
        ]
        
        result = await checker.check_stream_availability("http://test.stream", retries=1)
        
        assert result['is_available'] is True
        assert result['is_audio_stream'] is True
        assert mock_head.call_count == 2

@pytest.mark.asyncio
async def test_get_stream_metadata_success(stream_checker, mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.get(url, status=200, headers={
        'icy-name': 'Test Radio',
        'icy-genre': 'Test Genre',
        'icy-br': '128'
    })
    
    result = await stream_checker.get_stream_metadata(url)
    assert result is not None
    assert result['name'] == 'Test Radio'
    assert result['genre'] == 'Test Genre'
    assert result['bitrate'] == '128'

@pytest.mark.asyncio
async def test_get_stream_metadata_partial(stream_checker, mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.get(url, status=200, headers={
        'icy-name': 'Test Radio'
    })
    
    result = await stream_checker.get_stream_metadata(url)
    assert result is not None
    assert result['name'] == 'Test Radio'
    assert result['genre'] is None
    assert result['bitrate'] is None

@pytest.mark.asyncio
async def test_get_stream_metadata_no_metadata(stream_checker, mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.get(url, status=200, headers={})
    
    result = await stream_checker.get_stream_metadata(url)
    assert result is None

@pytest.mark.asyncio
async def test_get_stream_metadata_invalid_url(stream_checker):
    url = "invalid://url"
    result = await stream_checker.get_stream_metadata(url)
    assert result is None

@pytest.mark.asyncio
async def test_get_stream_metadata_timeout(stream_checker, mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.get(url, timeout=True)
    
    result = await stream_checker.get_stream_metadata(url)
    assert result is None

@pytest.mark.asyncio
async def test_get_stream_metadata_network_errors(stream_checker, mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.get(url, exception=aiohttp.ClientError())
    
    result = await stream_checker.get_stream_metadata(url)
    assert result is None 