"""Tests for the Stream Handler module."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
import asyncio
import io
import soundfile as sf

from ...detection.audio_processor.stream_handler import StreamHandler

@pytest.fixture
def stream_handler():
    """Create a StreamHandler instance for testing."""
    return StreamHandler()

@pytest.fixture
def mock_stream_url():
    """Create a mock stream URL for testing."""
    return "http://test.radio/stream"

@pytest.fixture
def mock_audio_chunk():
    """Create a mock audio chunk for testing."""
    # Generate 1 second of audio at 44.1kHz
    audio_data = np.random.random(44100).astype(np.float32)
    buffer = io.BytesIO()
    sf.write(buffer, audio_data, 44100, format='WAV')
    return buffer.getvalue()

@pytest.mark.asyncio
async def test_stream_handler_initialization():
    """Test StreamHandler initialization."""
    handler = StreamHandler()
    assert handler is not None
    assert hasattr(handler, 'process_stream')
    assert hasattr(handler, 'check_stream_health')

@pytest.mark.asyncio
async def test_process_stream_success(stream_handler, mock_stream_url, mock_audio_chunk):
    """Test successful stream processing."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content.read = AsyncMock(return_value=mock_audio_chunk)
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        audio_data = await stream_handler.process_stream(mock_stream_url)
        
        assert isinstance(audio_data, np.ndarray)
        assert len(audio_data) > 0
        assert not np.isnan(audio_data).any()

@pytest.mark.asyncio
async def test_process_stream_connection_error(stream_handler, mock_stream_url):
    """Test stream processing with connection error."""
    with patch('aiohttp.ClientSession.get', side_effect=aiohttp.ClientError):
        with pytest.raises(ConnectionError):
            await stream_handler.process_stream(mock_stream_url)

@pytest.mark.asyncio
async def test_process_stream_timeout(stream_handler, mock_stream_url):
    """Test stream processing with timeout."""
    with patch('aiohttp.ClientSession.get', side_effect=asyncio.TimeoutError):
        with pytest.raises(TimeoutError):
            await stream_handler.process_stream(mock_stream_url)

@pytest.mark.asyncio
async def test_process_stream_invalid_audio(stream_handler, mock_stream_url):
    """Test stream processing with invalid audio data."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content.read = AsyncMock(return_value=b'invalid audio data')
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        with pytest.raises(ValueError):
            await stream_handler.process_stream(mock_stream_url)

@pytest.mark.asyncio
async def test_check_stream_health_success(stream_handler, mock_stream_url):
    """Test successful stream health check."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {'content-type': 'audio/mpeg'}
    
    with patch('aiohttp.ClientSession.head', return_value=mock_response):
        health_status = await stream_handler.check_stream_health(mock_stream_url)
        
        assert health_status['is_available'] is True
        assert health_status['is_audio_stream'] is True
        assert health_status['status_code'] == 200

@pytest.mark.asyncio
async def test_check_stream_health_not_audio(stream_handler, mock_stream_url):
    """Test stream health check with non-audio content."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {'content-type': 'text/html'}
    
    with patch('aiohttp.ClientSession.head', return_value=mock_response):
        health_status = await stream_handler.check_stream_health(mock_stream_url)
        
        assert health_status['is_available'] is True
        assert health_status['is_audio_stream'] is False

@pytest.mark.asyncio
async def test_check_stream_health_unavailable(stream_handler, mock_stream_url):
    """Test stream health check with unavailable stream."""
    mock_response = AsyncMock()
    mock_response.status = 404
    
    with patch('aiohttp.ClientSession.head', return_value=mock_response):
        health_status = await stream_handler.check_stream_health(mock_stream_url)
        
        assert health_status['is_available'] is False
        assert health_status['status_code'] == 404

@pytest.mark.asyncio
async def test_stream_reconnection(stream_handler, mock_stream_url, mock_audio_chunk):
    """Test stream reconnection after failure."""
    mock_response_fail = AsyncMock()
    mock_response_fail.status = 500
    
    mock_response_success = AsyncMock()
    mock_response_success.status = 200
    mock_response_success.content.read = AsyncMock(return_value=mock_audio_chunk)
    
    with patch('aiohttp.ClientSession.get', side_effect=[
        aiohttp.ClientError,  # First attempt fails
        mock_response_success  # Second attempt succeeds
    ]):
        with pytest.raises(ConnectionError):
            await stream_handler.process_stream(mock_stream_url)
        
        # Second attempt should succeed
        audio_data = await stream_handler.process_stream(mock_stream_url)
        assert isinstance(audio_data, np.ndarray)
        assert len(audio_data) > 0

@pytest.mark.asyncio
async def test_stream_buffer_management(stream_handler, mock_stream_url, mock_audio_chunk):
    """Test stream buffer management."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content.read = AsyncMock(return_value=mock_audio_chunk)
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        # Process multiple chunks
        for _ in range(3):
            audio_data = await stream_handler.process_stream(mock_stream_url)
            assert isinstance(audio_data, np.ndarray)
            assert len(audio_data) > 0
            
        # Verify memory usage remains reasonable
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss
        assert memory_usage < 500 * 1024 * 1024  # Should use less than 500MB 