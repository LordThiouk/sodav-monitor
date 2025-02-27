"""Tests for the stream checker utility module."""

import pytest
import asyncio
from aioresponses import aioresponses
from aiohttp import ClientTimeout, ClientError, ContentTypeError, ClientResponseError, TooManyRedirects
from backend.utils.streams.stream_checker import StreamChecker

@pytest.fixture
def stream_checker():
    return StreamChecker()

@pytest.fixture
def mock_aioresponse():
    with aioresponses() as m:
        yield m

@pytest.mark.asyncio
async def test_check_stream_availability_success(stream_checker, mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.head(url, status=200, headers={'content-type': 'audio/mpeg'})
    
    result = await stream_checker.check_stream_availability(url)
    assert result['is_available'] is True
    assert result['is_audio_stream'] is True

@pytest.mark.asyncio
async def test_check_stream_availability_different_audio_types(stream_checker, mock_aioresponse):
    url = "http://test.stream"
    audio_types = [
        'audio/mpeg',
        'application/ogg',
        'application/x-mpegurl',
        'application/vnd.apple.mpegurl'
    ]
    
    for content_type in audio_types:
        mock_aioresponse.head(url, status=200, headers={'content-type': content_type})
        result = await stream_checker.check_stream_availability(url)
        assert result['is_available'] is True
        assert result['is_audio_stream'] is True

@pytest.mark.asyncio
async def test_check_stream_availability_not_audio(stream_checker, mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.head(url, status=200, headers={'content-type': 'text/html'})
    
    result = await stream_checker.check_stream_availability(url)
    assert result['is_available'] is True
    assert result['is_audio_stream'] is False

@pytest.mark.asyncio
async def test_check_stream_availability_http_errors(stream_checker, mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.head(url, status=404)
    
    result = await stream_checker.check_stream_availability(url)
    assert result['is_available'] is False
    assert result['is_audio_stream'] is False

@pytest.mark.asyncio
async def test_check_stream_availability_timeout(stream_checker, mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.head(url, timeout=True)
    
    result = await stream_checker.check_stream_availability(url)
    assert result['is_available'] is False
    assert result['is_audio_stream'] is False

@pytest.mark.asyncio
async def test_check_stream_availability_network_errors(stream_checker, mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.head(url, exception=ClientError())
    
    result = await stream_checker.check_stream_availability(url)
    assert result['is_available'] is False
    assert result['is_audio_stream'] is False

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
    mock_aioresponse.get(url, exception=ClientError())
    
    result = await stream_checker.get_stream_metadata(url)
    assert result is None 