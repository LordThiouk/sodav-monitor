"""Tests for the stream checker utility module."""

import pytest
import asyncio
from aioresponses import aioresponses
from aiohttp import ClientTimeout, ClientError, ContentTypeError, ClientResponseError, TooManyRedirects
from backend.utils.stream_checker import check_stream_availability, get_stream_metadata

@pytest.fixture
def mock_aioresponse():
    with aioresponses() as m:
        yield m

@pytest.mark.asyncio
async def test_check_stream_availability_success(mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.head(url, status=200, headers={'content-type': 'audio/mpeg'})
    
    result = await check_stream_availability(url)
    assert result['is_available'] is True
    assert result['is_audio_stream'] is True

@pytest.mark.asyncio
async def test_check_stream_availability_different_audio_types(mock_aioresponse):
    url = "http://test.stream"
    audio_types = [
        'audio/mpeg',
        'application/ogg',
        'application/x-mpegurl',
        'application/vnd.apple.mpegurl'
    ]
    
    for content_type in audio_types:
        mock_aioresponse.head(url, status=200, headers={'content-type': content_type})
        result = await check_stream_availability(url)
        assert result['is_available'] is True
        assert result['is_audio_stream'] is True

@pytest.mark.asyncio
async def test_check_stream_availability_not_audio(mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.head(url, status=200, headers={'content-type': 'text/html'})
    
    result = await check_stream_availability(url)
    assert result['is_available'] is True
    assert result['is_audio_stream'] is False

@pytest.mark.asyncio
async def test_check_stream_availability_http_errors(mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.head(url, status=404)
    
    result = await check_stream_availability(url)
    assert result['is_available'] is False
    assert result['is_audio_stream'] is False

@pytest.mark.asyncio
async def test_check_stream_availability_timeout(mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.head(url, exception=asyncio.TimeoutError())
    
    result = await check_stream_availability(url)
    assert result['is_available'] is False
    assert result['is_audio_stream'] is False

@pytest.mark.asyncio
async def test_check_stream_availability_network_errors(mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.head(url, exception=ClientError())
    
    result = await check_stream_availability(url)
    assert result['is_available'] is False
    assert result['is_audio_stream'] is False

@pytest.mark.asyncio
async def test_get_stream_metadata_success(mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.get(url, status=200, headers={
        'content-type': 'audio/mpeg',
        'icy-name': 'Test Radio',
        'icy-genre': 'Test Genre',
        'icy-br': '128',
        'icy-description': 'Test Description',
        'icy-url': 'http://test.radio'
    })
    
    result = await get_stream_metadata(url)
    assert result == {
        'name': 'Test Radio',
        'genre': 'Test Genre',
        'bitrate': '128'
    }

@pytest.mark.asyncio
async def test_get_stream_metadata_partial(mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.get(url, status=200, headers={
        'content-type': 'audio/mpeg',
        'icy-name': 'Test Radio'
    })
    
    result = await get_stream_metadata(url)
    assert result == {
        'name': 'Test Radio',
        'genre': None,
        'bitrate': None
    }

@pytest.mark.asyncio
async def test_get_stream_metadata_no_metadata(mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.get(url, status=200, headers={'content-type': 'audio/mpeg'})
    
    result = await get_stream_metadata(url)
    assert result is None

@pytest.mark.asyncio
async def test_get_stream_metadata_invalid_url():
    invalid_urls = ['', 'not_a_url', 'http://', 'https://', 'ftp://test.stream']
    
    for url in invalid_urls:
        result = await get_stream_metadata(url)
        assert result is None

@pytest.mark.asyncio
async def test_get_stream_metadata_timeout(mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.get(url, exception=asyncio.TimeoutError())
    
    result = await get_stream_metadata(url)
    assert result is None

@pytest.mark.asyncio
async def test_get_stream_metadata_network_errors(mock_aioresponse):
    url = "http://test.stream"
    mock_aioresponse.get(url, exception=ClientError())
    
    result = await get_stream_metadata(url)
    assert result is None 