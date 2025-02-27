"""Unit tests for the StreamHandler class."""

import pytest
import numpy as np
from datetime import datetime, timedelta
from backend.detection.audio_processor import StreamHandler

@pytest.fixture
def stream_handler():
    """Fixture providing a configured StreamHandler instance."""
    return StreamHandler(buffer_size=1000, channels=2)

@pytest.fixture
def sample_chunk():
    """Fixture providing a sample audio chunk."""
    return np.random.random((100, 2))  # 100 stereo samples

class TestStreamHandlerInitialization:
    """Test cases for StreamHandler initialization."""
    
    def test_default_initialization(self):
        """Test initialization with default parameters."""
        handler = StreamHandler()
        assert handler.buffer_size == 4096
        assert handler.channels == 2
        assert handler.buffer.shape == (4096, 2)
        
    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        handler = StreamHandler(buffer_size=1000, channels=1)
        assert handler.buffer_size == 1000
        assert handler.channels == 1
        assert handler.buffer.shape == (1000, 1)
        
    def test_invalid_buffer_size(self):
        """Test initialization with invalid buffer size."""
        with pytest.raises(ValueError):
            StreamHandler(buffer_size=0)
            
    def test_invalid_channels(self):
        """Test initialization with invalid number of channels."""
        with pytest.raises(ValueError):
            StreamHandler(channels=3)

class TestStreamHandlerProcessing:
    """Test cases for audio chunk processing."""
    
    def test_process_valid_chunk(self, stream_handler, sample_chunk):
        """Test processing a valid audio chunk."""
        result = pytest.mark.asyncio(stream_handler.process_chunk(sample_chunk))
        assert result is None  # Buffer not full yet
        assert stream_handler.buffer_position == 100
        
    def test_process_invalid_chunk_type(self, stream_handler):
        """Test processing an invalid chunk type."""
        with pytest.raises(TypeError):
            pytest.mark.asyncio(stream_handler.process_chunk([1, 2, 3]))
            
    def test_process_invalid_chunk_shape(self, stream_handler):
        """Test processing a chunk with wrong shape."""
        invalid_chunk = np.random.random((100, 3))  # 3 channels instead of 2
        with pytest.raises(ValueError):
            pytest.mark.asyncio(stream_handler.process_chunk(invalid_chunk))
            
    def test_buffer_full_processing(self, stream_handler):
        """Test processing when buffer becomes full."""
        # Fill the buffer completely
        chunk = np.random.random((stream_handler.buffer_size, 2))
        result = pytest.mark.asyncio(stream_handler.process_chunk(chunk))
        
        assert result is not None
        assert "timestamp" in result
        assert "buffer_full" in result
        assert "processing_delay_ms" in result
        assert "data" in result
        assert result["buffer_full"] is True
        assert isinstance(result["data"], np.ndarray)
        assert result["data"].shape == (stream_handler.buffer_size, 2)

class TestStreamHandlerBufferManagement:
    """Test cases for buffer management."""
    
    def test_reset_buffer(self, stream_handler, sample_chunk):
        """Test buffer reset functionality."""
        # Process some data
        pytest.mark.asyncio(stream_handler.process_chunk(sample_chunk))
        initial_position = stream_handler.buffer_position
        
        # Reset buffer
        stream_handler._reset_buffer()
        
        assert stream_handler.buffer_position == 0
        assert np.all(stream_handler.buffer == 0)
        assert initial_position > 0  # Verify we had data before reset
        
    def test_buffer_overflow_handling(self, stream_handler):
        """Test handling of buffer overflow."""
        # Create chunk larger than buffer
        large_chunk = np.random.random((stream_handler.buffer_size + 100, 2))
        result = pytest.mark.asyncio(stream_handler.process_chunk(large_chunk))
        
        assert result is not None
        assert stream_handler.buffer_position == 0  # Buffer should be reset
        
    def test_partial_buffer_fill(self, stream_handler):
        """Test partial buffer filling."""
        chunk1 = np.random.random((400, 2))
        chunk2 = np.random.random((300, 2))
        
        # Process first chunk
        result1 = pytest.mark.asyncio(stream_handler.process_chunk(chunk1))
        assert result1 is None
        assert stream_handler.buffer_position == 400
        
        # Process second chunk
        result2 = pytest.mark.asyncio(stream_handler.process_chunk(chunk2))
        assert result2 is None
        assert stream_handler.buffer_position == 700

class TestStreamHandlerStatus:
    """Test cases for stream status reporting."""
    
    def test_buffer_status(self, stream_handler, sample_chunk):
        """Test buffer status reporting."""
        # Process some data
        pytest.mark.asyncio(stream_handler.process_chunk(sample_chunk))
        
        status = stream_handler.get_buffer_status()
        assert "buffer_size" in status
        assert "current_position" in status
        assert "fill_percentage" in status
        assert "channels" in status
        assert "last_process_time" in status
        
        assert status["buffer_size"] == stream_handler.buffer_size
        assert status["current_position"] == stream_handler.buffer_position
        assert status["channels"] == stream_handler.channels
        assert isinstance(datetime.fromisoformat(status["last_process_time"]), datetime)
        
    def test_processing_delay(self, stream_handler):
        """Test processing delay calculation."""
        # Set initial process time
        stream_handler.last_process_time = datetime.now() - timedelta(seconds=1)
        
        # Process full buffer
        chunk = np.random.random((stream_handler.buffer_size, 2))
        result = pytest.mark.asyncio(stream_handler.process_chunk(chunk))
        
        assert result is not None
        assert result["processing_delay_ms"] >= 1000  # Should be at least 1 second 