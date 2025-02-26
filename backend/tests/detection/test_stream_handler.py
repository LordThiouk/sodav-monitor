"""Tests for the Stream Handler component."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
import soundfile as sf
import io
import asyncio

from detection.audio_processor.stream_handler import StreamHandler
from models.models import RadioStation

@pytest.fixture
def stream_handler():
    """Create a StreamHandler instance for testing."""
    return StreamHandler()

@pytest.fixture
def sample_station():
    """Create a sample radio station for testing."""
    return RadioStation(
        id=1,
        name="Test Radio",
        stream_url="http://test.stream/audio",
        country="SN",
        language="fr",
        is_active=True
    )

@pytest.fixture
def mock_audio_response():
    """Create a mock audio response."""
    # Generate 1 second of audio data
    audio_data = np.random.random(44100).astype(np.float32)
    buffer = io.BytesIO()
    sf.write(buffer, audio_data, 44100, format='WAV')
    buffer.seek(0)
    return buffer.read()

@pytest.mark.asyncio
async def test_init_stream_handler():
    """Test StreamHandler initialization."""
    handler = StreamHandler()
    assert handler is not None
    assert hasattr(handler, 'connect')
    assert hasattr(handler, 'disconnect')
    assert hasattr(handler, 'get_stream_chunk')

@pytest.mark.asyncio
async def test_connect_to_stream(stream_handler, sample_station, mock_audio_response):
    """Test connecting to an audio stream."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {'content-type': 'audio/mpeg'}
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        success = await stream_handler.connect(sample_station.stream_url)
        assert success is True
        assert stream_handler.is_connected is True

@pytest.mark.asyncio
async def test_connect_invalid_url(stream_handler):
    """Test connecting to an invalid URL."""
    with patch('aiohttp.ClientSession.get', side_effect=aiohttp.ClientError):
        success = await stream_handler.connect("invalid_url")
        assert success is False
        assert stream_handler.is_connected is False

@pytest.mark.asyncio
async def test_connect_non_audio_stream(stream_handler, sample_station):
    """Test connecting to a non-audio stream."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {'content-type': 'text/html'}
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        success = await stream_handler.connect(sample_station.stream_url)
        assert success is False
        assert stream_handler.is_connected is False

@pytest.mark.asyncio
async def test_get_stream_chunk_success(stream_handler, sample_station, mock_audio_response):
    """Test getting a chunk of audio data from the stream."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {'content-type': 'audio/mpeg'}
    mock_response.content.read = AsyncMock(return_value=mock_audio_response)
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        await stream_handler.connect(sample_station.stream_url)
        chunk = await stream_handler.get_stream_chunk()
        
        assert chunk is not None
        assert isinstance(chunk, np.ndarray)
        assert len(chunk) > 0

@pytest.mark.asyncio
async def test_get_stream_chunk_not_connected(stream_handler):
    """Test getting a chunk when not connected."""
    with pytest.raises(RuntimeError, match="Not connected to any stream"):
        await stream_handler.get_stream_chunk()

@pytest.mark.asyncio
async def test_disconnect_success(stream_handler, sample_station, mock_audio_response):
    """Test disconnecting from a stream."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {'content-type': 'audio/mpeg'}
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        await stream_handler.connect(sample_station.stream_url)
        await stream_handler.disconnect()
        
        assert stream_handler.is_connected is False

@pytest.mark.asyncio
async def test_stream_timeout(stream_handler, sample_station):
    """Test handling stream timeout."""
    with patch('aiohttp.ClientSession.get', side_effect=asyncio.TimeoutError):
        success = await stream_handler.connect(sample_station.stream_url)
        assert success is False
        assert stream_handler.is_connected is False

@pytest.mark.asyncio
async def test_stream_reconnection(stream_handler, sample_station, mock_audio_response):
    """Test stream reconnection after disconnection."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {'content-type': 'audio/mpeg'}
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        # First connection
        await stream_handler.connect(sample_station.stream_url)
        assert stream_handler.is_connected is True
        
        # Disconnect
        await stream_handler.disconnect()
        assert stream_handler.is_connected is False
        
        # Reconnect
        await stream_handler.connect(sample_station.stream_url)
        assert stream_handler.is_connected is True

@pytest.mark.asyncio
async def test_stream_error_handling(stream_handler, sample_station):
    """Test handling various stream errors."""
    error_cases = [
        (aiohttp.ClientError(), "Connection error"),
        (aiohttp.ServerDisconnectedError(), "Server disconnected"),
        (asyncio.TimeoutError(), "Connection timeout"),
        (Exception(), "Unknown error")
    ]
    
    for error, error_type in error_cases:
        with patch('aiohttp.ClientSession.get', side_effect=error):
            success = await stream_handler.connect(sample_station.stream_url)
            assert success is False
            assert stream_handler.is_connected is False

@pytest.mark.asyncio
async def test_stream_metadata(stream_handler, sample_station):
    """Test handling stream metadata."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {
        'content-type': 'audio/mpeg',
        'icy-name': 'Test Radio',
        'icy-genre': 'Test Genre',
        'icy-br': '128'
    }
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        await stream_handler.connect(sample_station.stream_url)
        metadata = stream_handler.get_stream_metadata()
        
        assert metadata is not None
        assert metadata.get('name') == 'Test Radio'
        assert metadata.get('genre') == 'Test Genre'
        assert metadata.get('bitrate') == '128' 