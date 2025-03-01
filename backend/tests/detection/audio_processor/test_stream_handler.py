"""Unit tests for the StreamHandler class."""

import pytest
import numpy as np
import asyncio
from datetime import datetime, timedelta
from backend.detection.audio_processor.stream_handler import StreamHandler

@pytest.fixture
async def stream_handler():
    """Create a StreamHandler instance for testing."""
    handler = StreamHandler(buffer_size=1024, channels=2)  # Smaller buffer for faster tests
    await handler.start_stream()
    yield handler
    await handler.cleanup()

@pytest.mark.asyncio
async def test_initialization():
    """Test StreamHandler initialization."""
    handler = StreamHandler(buffer_size=1024, channels=2)
    assert handler.buffer_size == 1024
    assert handler.channels == 2
    assert handler.buffer.shape == (1024, 2)
    assert handler.buffer_position == 0

@pytest.mark.asyncio
async def test_invalid_initialization():
    """Test StreamHandler initialization with invalid parameters."""
    with pytest.raises(ValueError):
        StreamHandler(buffer_size=0)
    with pytest.raises(ValueError):
        StreamHandler(channels=3)

@pytest.mark.asyncio
async def test_process_valid_chunk(stream_handler):
    """Test processing a valid audio chunk."""
    # Fill buffer completely
    chunk = np.random.rand(1024, 2)  # Full buffer size
    result = await stream_handler.process_chunk(chunk)
    assert isinstance(result, np.ndarray)
    assert result.shape == (1024, 2)

@pytest.mark.asyncio
async def test_process_silence(stream_handler):
    """Test processing silent audio."""
    chunk = np.zeros((1024, 2))
    result = await stream_handler.process_chunk(chunk)
    assert isinstance(result, np.ndarray)
    assert result.shape == (1024, 2)
    assert np.all(result == 0)

@pytest.mark.asyncio
async def test_process_invalid_chunk(stream_handler):
    """Test processing invalid audio chunks."""
    with pytest.raises(TypeError):
        await stream_handler.process_chunk([1, 2, 3])  # Not numpy array
        
    with pytest.raises(ValueError):
        await stream_handler.process_chunk(np.random.rand(1024, 3))  # Wrong channels

@pytest.mark.asyncio
async def test_process_nan_chunk(stream_handler):
    """Test processing chunk with NaN values."""
    chunk = np.array([[np.nan, np.nan]] * 1024)
    with pytest.raises(ValueError):
        await stream_handler.process_chunk(chunk)

@pytest.mark.asyncio
async def test_buffer_overflow(stream_handler):
    """Test handling buffer overflow."""
    # Try to add more samples than buffer size
    chunk = np.random.rand(2000, 2)
    result = await stream_handler.process_chunk(chunk)
    assert isinstance(result, np.ndarray)
    assert result.shape == (1024, 2)
    assert stream_handler.buffer_position == 976  # 2000 - 1024 samples remaining

@pytest.mark.asyncio
async def test_stream_lifecycle(stream_handler):
    """Test stream start/stop lifecycle."""
    assert await stream_handler.stop_stream()
    assert stream_handler.buffer_position == 0
    assert await stream_handler.start_stream()
    assert stream_handler.buffer_position == 0

@pytest.mark.asyncio
async def test_buffer_status(stream_handler):
    """Test getting buffer status."""
    chunk = np.random.rand(512, 2)  # Half buffer
    await stream_handler.process_chunk(chunk)
    
    status = stream_handler.get_buffer_status()
    assert status["buffer_size"] == 1024
    assert status["current_position"] == 512
    assert status["fill_percentage"] == 50.0
    assert status["channels"] == 2
    assert "last_process_time" in status
    assert "processing_delay_ms" in status

@pytest.mark.asyncio
async def test_concurrent_processing():
    """Test concurrent chunk processing."""
    handler = StreamHandler(buffer_size=1024, channels=2)
    await handler.start_stream()
    
    chunks = [np.random.rand(256, 2) for _ in range(4)]  # 4 chunks of 256 samples
    tasks = [handler.process_chunk(chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks)
    
    # Last task should return data
    assert results[-1] is not None
    assert isinstance(results[-1], np.ndarray)
    assert results[-1].shape == (1024, 2)
    
    await handler.cleanup()

@pytest.mark.asyncio
async def test_long_running_stream():
    """Test long-running stream processing."""
    handler = StreamHandler(buffer_size=1024, channels=2)
    await handler.start_stream()
    
    start_time = datetime.now()
    chunk_count = 0
    chunk_size = 256  # Quarter buffer size
    
    while (datetime.now() - start_time) < timedelta(seconds=1):
        chunk = np.random.rand(chunk_size, 2)
        result = await handler.process_chunk(chunk)
        if result is not None:
            chunk_count += 1
            
    assert chunk_count > 0
    await handler.cleanup()

@pytest.mark.asyncio
async def test_cleanup(stream_handler):
    """Test cleanup functionality."""
    chunk = np.random.rand(512, 2)
    await stream_handler.process_chunk(chunk)
    await stream_handler.cleanup()
    assert stream_handler.buffer_position == 0
    assert np.all(stream_handler.buffer == 0)

@pytest.mark.asyncio
async def test_mono_to_stereo_conversion(stream_handler):
    """Test mono to stereo conversion."""
    mono_chunk = np.random.rand(1024)  # Mono audio
    result = await stream_handler.process_chunk(mono_chunk)
    assert isinstance(result, np.ndarray)
    assert result.shape == (1024, 2)
    # Check if both channels are identical
    assert np.allclose(result[:, 0], result[:, 1])

@pytest.mark.asyncio
async def test_bit_depth_conversion(stream_handler):
    """Test bit depth conversion."""
    # Create 16-bit audio data
    chunk = (np.random.rand(1024, 2) * 65535 - 32768).astype(np.int16)
    chunk_float = chunk.astype(np.float32) / 32768.0
    
    result = await stream_handler.process_chunk(chunk_float)
    assert isinstance(result, np.ndarray)
    assert result.shape == (1024, 2)
    assert result.dtype == np.float64  # Default numpy float type

@pytest.mark.asyncio
async def test_buffer_efficiency(stream_handler):
    """Test buffer usage efficiency."""
    chunk = np.random.rand(256, 2)  # Quarter buffer size
    
    # Fill buffer multiple times
    buffer_usage = []
    for i in range(4):
        await stream_handler.process_chunk(chunk)
        # Calculate expected buffer position
        expected_position = min((i + 1) * 256, 1024)
        assert stream_handler.buffer_position == expected_position % 1024
        buffer_usage.append(stream_handler.buffer_position / stream_handler.buffer_size)
    
    # Buffer should be filled efficiently
    assert all(usage > 0 for usage in buffer_usage[:-1])  # All but last should be non-zero
    assert buffer_usage[-1] == 0  # Last position should be 0 after full buffer processed 