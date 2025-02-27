"""Tests for the StreamHandler class."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import time
from datetime import datetime, timedelta
import psutil
import os
from backend.detection.audio_processor.stream_handler import StreamHandler

# Test Fixtures
@pytest.fixture
def stream_handler():
    """Create a StreamHandler instance for testing."""
    return StreamHandler(buffer_size=4096, channels=2)

@pytest.fixture
def mock_audio_chunk():
    """Generate a mock audio chunk for testing."""
    return np.random.random((1024, 2))

@pytest.fixture
def filled_stream_handler(stream_handler, mock_audio_chunk):
    """Create a StreamHandler with pre-filled buffer."""
    for _ in range(4):  # Fill the buffer
        asyncio.run(stream_handler.process_chunk(mock_audio_chunk))
    return stream_handler

class TestInitialization:
    """Test StreamHandler initialization and configuration."""
    
    def test_default_initialization(self):
        """Test initialization with default parameters."""
        handler = StreamHandler()
        assert handler.buffer_size == 4096
        assert handler.channels == 2
        assert handler.buffer.shape == (4096, 2)
        assert handler.buffer_position == 0
        assert not handler.processing
        
    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        handler = StreamHandler(buffer_size=8192, channels=1)
        assert handler.buffer_size == 8192
        assert handler.channels == 1
        assert handler.buffer.shape == (8192, 1)
        
    @pytest.mark.parametrize("buffer_size,channels", [
        (0, 2),      # Invalid buffer size
        (-1024, 2),  # Negative buffer size
        (4096, 0),   # Invalid channels
        (4096, 3),   # Too many channels
    ])
    def test_invalid_parameters(self, buffer_size, channels):
        """Test initialization with invalid parameters."""
        with pytest.raises(ValueError):
            StreamHandler(buffer_size=buffer_size, channels=channels)

@pytest.mark.asyncio
class TestRealTimeProcessing:
    """Test real-time audio processing capabilities."""
    
    async def test_continuous_stream_processing(self, stream_handler):
        """Test processing a continuous stream of audio data."""
        chunk_size = 1024
        num_chunks = 10
        processing_times = []
        
        for _ in range(num_chunks):
            chunk = np.random.random((chunk_size, 2))
            start_time = time.perf_counter()
            result = await stream_handler.process_chunk(chunk)
            processing_time = time.perf_counter() - start_time
            processing_times.append(processing_time)
            await asyncio.sleep(0.01)  # Simulate real-time stream
        
        avg_processing_time = sum(processing_times) / len(processing_times)
        assert avg_processing_time < 0.05  # Less than 50ms average processing time
    
    async def test_stream_backpressure(self, stream_handler):
        """Test handling of backpressure when processing is slower than input."""
        # Fill the buffer first
        chunk = np.random.random((4096, 2))
        await stream_handler.process_chunk(chunk)
        
        # Set processing flag to simulate ongoing processing
        stream_handler.processing = True
        
        # Try to process another chunk while processing
        chunk = np.random.random((1024, 2))
        result = await stream_handler.process_chunk(chunk)
        
        assert result is not None
        assert result["buffer_full"]
        assert result["backpressure"]

@pytest.mark.asyncio
class TestBufferManagement:
    """Test buffer management and overflow handling."""
    
    async def test_buffer_overflow(self, stream_handler):
        """Test handling of buffer overflow conditions."""
        large_chunk = np.random.random((stream_handler.buffer_size + 100, 2))
        result = await stream_handler.process_chunk(large_chunk)
        assert result is not None
        assert result["buffer_full"]
        assert stream_handler.buffer_position == 0  # Buffer should be reset
    
    async def test_partial_buffer_fill(self, stream_handler):
        """Test partial buffer filling."""
        chunk1 = np.random.random((1000, 2))
        chunk2 = np.random.random((500, 2))
        
        result1 = await stream_handler.process_chunk(chunk1)
        assert result1 is None
        assert stream_handler.buffer_position == 1000
        
        result2 = await stream_handler.process_chunk(chunk2)
        assert result2 is None
        assert stream_handler.buffer_position == 1500

@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling and recovery."""
    
    async def test_processing_error_recovery(self, stream_handler):
        """Test recovery from processing errors."""
        error_count = 0
        success_count = 0
        
        async def unstable_process(*args, **kwargs):
            nonlocal error_count
            if error_count < 2:  # Fail twice
                error_count += 1
                raise Exception("Processing error")
            return {"buffer_full": True, "data": np.zeros((1024, 2))}
        
        with patch.object(stream_handler, '_process_buffer', side_effect=unstable_process):
            # Fill buffer to trigger processing
            chunk = np.random.random((4096, 2))
            for _ in range(3):  # Try multiple times to get both errors
                result = await stream_handler.process_chunk(chunk)
                if result and "error" in result:
                    success_count += 1
        
        assert error_count == 2  # Should have failed twice
        assert success_count >= 2  # Should have received error results
    
    async def test_invalid_input_handling(self, stream_handler):
        """Test handling of invalid input data."""
        with pytest.raises(TypeError):
            await stream_handler.process_chunk([1, 2, 3])  # Not numpy array
        
        with pytest.raises(ValueError):
            await stream_handler.process_chunk(np.random.random((1024, 3)))  # Wrong channels

@pytest.mark.benchmark
class TestPerformance:
    """Performance benchmarks for stream processing."""
    
    def test_processing_latency(self, stream_handler, benchmark):
        """Benchmark processing latency."""
        chunk = np.random.random((1024, 2))
        
        def process_chunk():
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(stream_handler.process_chunk(chunk))
            finally:
                loop.close()
        
        benchmark(process_chunk)
        assert benchmark.stats['mean'] < 0.01  # Mean processing time < 10ms
    
    def test_memory_usage_stability(self, benchmark):
        """Test memory usage stability during extended processing."""
        def measure_memory():
            handler = StreamHandler(buffer_size=16384)  # Large buffer
            chunk = np.random.random((1024, 2))
            loop = asyncio.new_event_loop()
            try:
                for _ in range(10):
                    loop.run_until_complete(handler.process_chunk(chunk))
            finally:
                loop.close()
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # MB
        
        initial_memory = measure_memory()
        final_memory = benchmark(measure_memory)
        assert abs(final_memory - initial_memory) < 50  # Less than 50MB growth

class TestStreamStatus:
    """Test stream status reporting and monitoring."""
    
    def test_buffer_status(self, filled_stream_handler):
        """Test buffer status reporting."""
        status = filled_stream_handler.get_buffer_status()
        
        assert isinstance(status, dict)
        assert all(key in status for key in [
            "buffer_size", "current_position", "fill_percentage",
            "channels", "last_process_time"
        ])
        assert status["buffer_size"] == filled_stream_handler.buffer_size
        assert status["channels"] == filled_stream_handler.channels
        assert isinstance(datetime.fromisoformat(status["last_process_time"]), datetime)
    
    def test_processing_delay(self, stream_handler):
        """Test processing delay calculation."""
        stream_handler.last_process_time = datetime.now() - timedelta(seconds=1)
        chunk = np.random.random((stream_handler.buffer_size, 2))
        result = asyncio.run(stream_handler.process_chunk(chunk))
        
        assert result is not None
        assert result["processing_delay_ms"] >= 1000  # Should be at least 1 second 