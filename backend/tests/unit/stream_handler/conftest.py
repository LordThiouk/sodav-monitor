"""Test configuration for stream handler tests."""

import asyncio
from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest


@pytest.fixture
def mock_audio_chunk():
    """Generate a mock audio chunk for testing."""
    # Create a stereo chunk (1024 samples, 2 channels)
    return np.random.random((1024, 2))


@pytest.fixture
def mock_audio_stream():
    """Create a mock audio stream that yields chunks."""

    async def stream_generator():
        for _ in range(5):  # Generate 5 chunks
            yield np.random.random((1024, 2))

    return stream_generator()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    websocket = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.receive_json = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = Mock()
    redis.publish = Mock()
    redis.subscribe = Mock()
    redis.get_message = Mock()
    return redis


@pytest.fixture
def stream_handler():
    """Create a StreamHandler instance for testing."""
    from backend.detection.audio_processor.stream_handler import StreamHandler

    return StreamHandler(buffer_size=4096, channels=2)


@pytest.fixture
def filled_stream_handler(stream_handler, mock_audio_chunk):
    """Create a StreamHandler with some data in the buffer."""
    # Fill half the buffer with repeated chunks
    for i in range(2):
        start_idx = i * 1024
        stream_handler.buffer[start_idx : start_idx + 1024] = mock_audio_chunk
    stream_handler.buffer_position = 2048
    return stream_handler


@pytest.fixture
def mock_stream_url():
    """Provide a mock stream URL for testing."""
    return "http://test.stream/audio"


@pytest.fixture
def mock_stream_response():
    """Create a mock response for stream requests."""
    response = AsyncMock()
    response.status = 200
    response.headers = {"content-type": "audio/mpeg", "icy-br": "128", "icy-name": "Test Radio"}
    return response


@pytest.fixture
def mock_stream_error_response():
    """Create a mock error response for stream requests."""
    response = AsyncMock()
    response.status = 404
    response.headers = {}
    return response
