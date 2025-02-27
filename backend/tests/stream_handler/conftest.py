"""Test configuration for stream handler tests."""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock
import asyncio

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
        stream_handler.buffer[start_idx:start_idx + 1024] = mock_audio_chunk
    stream_handler.buffer_position = 2048
    return stream_handler

@pytest.fixture
def mock_stream_url():
    """Provide a mock stream URL for testing."""
    return "http://test.stream/audio"

@pytest.fixture
def mock_stream_response():
    """Create a mock successful response for stream requests."""
    response = AsyncMock()
    response.status = 200
    response.headers = {'Content-Type': 'audio/mpeg'}
    return response

@pytest.fixture
def mock_stream_error_response():
    """Create a mock error response for stream requests."""
    response = AsyncMock()
    response.status = 404
    response.headers = {}
    return response

@pytest.fixture
def benchmark_stream_handler():
    """Create a StreamHandler instance optimized for benchmarking."""
    from backend.detection.audio_processor.stream_handler import StreamHandler
    return StreamHandler(buffer_size=8192, channels=2)  # Larger buffer for benchmarks

@pytest.fixture
def real_time_stream_handler():
    """Create a StreamHandler instance configured for real-time processing."""
    from backend.detection.audio_processor.stream_handler import StreamHandler
    handler = StreamHandler(buffer_size=2048, channels=2)  # Smaller buffer for lower latency
    handler.set_real_time_mode(True)  # Enable real-time processing optimizations
    return handler

@pytest.fixture
def mock_audio_stream():
    """Create a mock audio stream generator for continuous testing."""
    async def generate_chunks(num_chunks=10, chunk_size=1024):
        for _ in range(num_chunks):
            yield np.random.random((chunk_size, 2))
            await asyncio.sleep(0.01)  # Simulate realistic timing
    return generate_chunks

@pytest.fixture
def mock_unstable_stream():
    """Create a mock stream that occasionally produces errors."""
    async def generate_unstable_chunks(num_chunks=10, error_rate=0.2):
        for i in range(num_chunks):
            if np.random.random() < error_rate:
                raise ConnectionError("Simulated stream error")
            yield np.random.random((1024, 2))
            await asyncio.sleep(0.01)
    return generate_unstable_chunks

@pytest.fixture
def mock_variable_rate_stream():
    """Create a mock stream with variable data rates."""
    async def generate_variable_rate_chunks(num_chunks=10):
        for i in range(num_chunks):
            # Vary chunk size to simulate network jitter
            chunk_size = int(1024 * (1 + 0.5 * np.sin(i / 2)))
            yield np.random.random((chunk_size, 2))
            # Variable delay to simulate network conditions
            await asyncio.sleep(0.01 * (1 + 0.5 * np.cos(i / 2)))
    return generate_variable_rate_chunks 