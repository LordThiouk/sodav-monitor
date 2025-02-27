"""Tests for the StreamHandler class."""

import pytest
import numpy as np
from unittest.mock import patch, AsyncMock
import asyncio
from datetime import datetime, timedelta

from backend.detection.audio_processor.stream_handler import StreamHandler

class TestStreamHandlerInitialization:
    """Test StreamHandler initialization and parameter validation."""
    
    def test_default_initialization(self):
        """Test initialization with default parameters."""
        handler = StreamHandler()
        assert handler.buffer_size == 4096
        assert handler.channels == 2
        assert handler.buffer.shape == (4096, 2)
        assert handler.buffer_position == 0
        
    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        handler = StreamHandler(buffer_size=8192, channels=1)
        assert handler.buffer_size == 8192
        assert handler.channels == 1
        assert handler.buffer.shape == (8192, 1)
        
    def test_invalid_buffer_size(self):
        """Test initialization with invalid buffer size."""
        with pytest.raises(ValueError):
            StreamHandler(buffer_size=0)
            
    def test_invalid_channels(self):
        """Test initialization with invalid number of channels."""
        with pytest.raises(ValueError):
            StreamHandler(channels=3)  # Only 1 or 2 channels allowed

@pytest.mark.asyncio
class TestStreamProcessing:
    """Test audio stream processing functionality."""
    
    async def test_process_chunk_valid(self, stream_handler, mock_audio_chunk):
        """Test processing a valid audio chunk."""
        result = await stream_handler.process_chunk(mock_audio_chunk)
        assert result is None  # Buffer not full yet
        assert stream_handler.buffer_position == len(mock_audio_chunk)
        
    async def test_process_chunk_buffer_full(self, stream_handler, mock_audio_chunk):
        """Test processing chunk when buffer becomes full."""
        # Fill the buffer
        large_chunk = np.random.random((stream_handler.buffer_size, 2))
        result = await stream_handler.process_chunk(large_chunk)
        
        assert result is not None
        assert "timestamp" in result
        assert "buffer_full" in result
        assert "data" in result
        assert result["buffer_full"] is True
        assert isinstance(result["data"], np.ndarray)
        
    async def test_process_chunk_invalid_shape(self, stream_handler):
        """Test processing chunk with wrong shape."""
        invalid_chunk = np.random.random((1024, 3))  # 3 channels instead of 2
        with pytest.raises(ValueError):
            await stream_handler.process_chunk(invalid_chunk)
            
    async def test_process_chunk_invalid_type(self, stream_handler):
        """Test processing invalid chunk type."""
        with pytest.raises(TypeError):
            await stream_handler.process_chunk([1, 2, 3])  # Not numpy array

@pytest.mark.asyncio
class TestStreamManagement:
    """Test stream management functionality."""
    
    async def test_start_stream(self, stream_handler):
        """Test starting stream processing."""
        success = await stream_handler.start_stream()
        assert success is True
        assert stream_handler.buffer_position == 0
        
    async def test_stop_stream(self, filled_stream_handler):
        """Test stopping stream processing."""
        success = await filled_stream_handler.stop_stream()
        assert success is True
        assert filled_stream_handler.buffer_position == 0
        
    async def test_reset_buffer(self, filled_stream_handler):
        """Test buffer reset functionality."""
        initial_position = filled_stream_handler.buffer_position
        filled_stream_handler._reset_buffer()
        
        assert filled_stream_handler.buffer_position == 0
        assert np.all(filled_stream_handler.buffer == 0)
        assert initial_position > 0  # Verify we had data before reset

@pytest.mark.asyncio
class TestStreamPerformance:
    """Test stream processing performance."""
    
    def test_processing_latency(self, stream_handler, mock_audio_chunk, benchmark):
        """Test audio processing latency."""
        def process_chunk():
            # Create a new event loop for each call
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(stream_handler.process_chunk(mock_audio_chunk))
            finally:
                loop.close()

        benchmark(process_chunk)
        # Check that mean processing time is less than 100ms (100,000 microseconds)
        assert benchmark.stats['mean'] < 100000  # Less than 100ms per chunk

    def test_memory_usage(self, benchmark):
        """Test memory usage during stream processing."""
        import psutil
        import os
        
        def measure_memory():
            handler = StreamHandler(buffer_size=16384)  # Larger buffer
            initial = psutil.Process(os.getpid()).memory_info().rss
            # Process some data
            chunk = np.random.random((1024, 2))
            # Create a new event loop for each call
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(handler.process_chunk(chunk))
            finally:
                loop.close()
            final = psutil.Process(os.getpid()).memory_info().rss
            return (final - initial) / 1024 / 1024  # MB
            
        memory_increase = benchmark(measure_memory)
        assert memory_increase < 50  # Should use less than 50MB additional memory

@pytest.mark.asyncio
class TestStreamErrorHandling:
    """Test error handling in stream processing."""
    
    async def test_buffer_overflow_handling(self, stream_handler):
        """Test handling of buffer overflow."""
        # Create chunk larger than buffer
        large_chunk = np.random.random((stream_handler.buffer_size + 100, 2))
        result = await stream_handler.process_chunk(large_chunk)
        
        assert result is not None
        assert stream_handler.buffer_position == 0  # Buffer should be reset
        
    async def test_partial_buffer_fill(self, stream_handler):
        """Test partial buffer filling."""
        chunk1 = np.random.random((1000, 2))
        chunk2 = np.random.random((500, 2))
        
        # Process first chunk
        result1 = await stream_handler.process_chunk(chunk1)
        assert result1 is None
        assert stream_handler.buffer_position == 1000
        
        # Process second chunk
        result2 = await stream_handler.process_chunk(chunk2)
        assert result2 is None
        assert stream_handler.buffer_position == 1500
        
    async def test_error_recovery(self, stream_handler):
        """Test recovery from processing errors."""
        # Simulate error during processing
        with patch.object(stream_handler, '_process_buffer', side_effect=Exception("Processing error")):
            # Should handle error and continue
            large_chunk = np.random.random((stream_handler.buffer_size, 2))
            with pytest.raises(Exception, match="Processing error"):
                await stream_handler.process_chunk(large_chunk)
            # Buffer should be filled since error occurred during processing
            assert stream_handler.buffer_position == stream_handler.buffer_size
            # Reset buffer for cleanup
            stream_handler._reset_buffer()

class TestStreamStatus:
    """Test stream status reporting."""
    
    def test_buffer_status(self, filled_stream_handler):
        """Test buffer status reporting."""
        status = filled_stream_handler.get_buffer_status()
        
        assert "buffer_size" in status
        assert "current_position" in status
        assert "fill_percentage" in status
        assert "channels" in status
        assert "last_process_time" in status
        
        assert status["buffer_size"] == filled_stream_handler.buffer_size
        assert status["current_position"] == filled_stream_handler.buffer_position
        assert status["channels"] == filled_stream_handler.channels
        assert isinstance(datetime.fromisoformat(status["last_process_time"]), datetime)
        
    def test_processing_delay(self, stream_handler):
        """Test processing delay calculation."""
        # Set initial process time
        stream_handler.last_process_time = datetime.now() - timedelta(seconds=1)
        
        # Process full buffer
        chunk = np.random.random((stream_handler.buffer_size, 2))
        result = asyncio.run(stream_handler.process_chunk(chunk))
        
        assert result is not None
        assert result["processing_delay_ms"] >= 1000  # Should be at least 1 second 