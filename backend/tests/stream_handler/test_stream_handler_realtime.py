"""Real-time processing tests for the StreamHandler class."""

import pytest
import numpy as np
import asyncio
import time
from datetime import datetime, timedelta
import psutil
import os
from unittest.mock import patch, AsyncMock

from backend.detection.audio_processor.stream_handler import StreamHandler

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
            
            # Simulate real-time stream by waiting
            await asyncio.sleep(0.01)
        
        avg_processing_time = sum(processing_times) / len(processing_times)
        assert avg_processing_time < 0.05  # Less than 50ms average processing time
    
    async def test_stream_backpressure(self, stream_handler):
        """Test handling of backpressure when processing is slower than input."""
        chunk_size = 1024
        buffer_full_count = 0
        
        # Simulate slow processing
        async def slow_process_mock(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing delay
            return {
                "timestamp": datetime.now().isoformat(),
                "buffer_full": True,
                "processing_delay_ms": 100,
                "data": np.zeros((chunk_size, 2))
            }
        
        with patch.object(stream_handler, '_process_buffer', side_effect=slow_process_mock):
            for _ in range(10):
                chunk = np.random.random((chunk_size, 2))
                result = await stream_handler.process_chunk(chunk)
                if result and result.get("buffer_full"):
                    buffer_full_count += 1
                
                # Don't wait between chunks to simulate fast input
        
        assert buffer_full_count > 0  # Should detect buffer full condition

@pytest.mark.asyncio
class TestBufferOverflow:
    """Test buffer overflow scenarios and handling."""
    
    async def test_gradual_buffer_overflow(self, stream_handler):
        """Test gradual buffer overflow with increasing chunk sizes."""
        initial_size = 512
        for i in range(5):
            chunk_size = initial_size * (2 ** i)
            chunk = np.random.random((chunk_size, 2))
            result = await stream_handler.process_chunk(chunk)
            
            if chunk_size > stream_handler.buffer_size:
                assert result is not None
                assert result["buffer_full"]
                assert stream_handler.buffer_position == 0  # Buffer should be reset
    
    async def test_rapid_buffer_overflow(self, stream_handler):
        """Test rapid buffer overflow with multiple large chunks."""
        large_chunk = np.random.random((stream_handler.buffer_size * 2, 2))
        results = []
        
        for _ in range(3):
            result = await stream_handler.process_chunk(large_chunk)
            results.append(result)
            
        assert all(r["buffer_full"] for r in results)
        assert stream_handler.buffer_position == 0
    
    async def test_overflow_data_integrity(self, stream_handler):
        """Test data integrity during buffer overflow."""
        # Fill buffer with known pattern
        pattern = np.linspace(0, 1, stream_handler.buffer_size * 2)
        pattern = pattern.reshape(-1, 2)
        
        result = await stream_handler.process_chunk(pattern)
        assert result is not None
        assert result["buffer_full"]
        
        # Verify processed data maintains pattern characteristics
        processed_data = result["data"]
        assert np.allclose(
            np.diff(processed_data[:, 0]).mean(),
            np.diff(pattern[:len(processed_data), 0]).mean(),
            rtol=1e-5
        )

@pytest.mark.asyncio
class TestErrorRecovery:
    """Test error recovery scenarios."""
    
    async def test_processing_error_recovery(self, stream_handler):
        """Test recovery from processing errors."""
        error_count = 0
        success_count = 0

        # Simulate occasional processing errors
        async def unstable_process(*args, **kwargs):
            nonlocal error_count, success_count
            if error_count < 2:  # Fail twice
                error_count += 1
                raise Exception("Processing error")
            success_count += 1
            return {
                "timestamp": datetime.now().isoformat(),
                "buffer_full": True,
                "processing_delay_ms": 0,
                "data": np.zeros((1024, 2))
            }

        with patch.object(stream_handler, '_process_buffer', side_effect=unstable_process):
            # Fill buffer multiple times to trigger processing
            for _ in range(10):  # Increased iterations to ensure buffer fills multiple times
                try:
                    chunk = np.random.random((1024, 2))  # Each chunk is 1/4 of buffer
                    result = await stream_handler.process_chunk(chunk)
                    if result:
                        success_count += 1
                except Exception:
                    continue

        assert error_count == 2  # Should have failed twice
        assert success_count > 0  # Should have recovered and succeeded

    async def test_automatic_reset_after_error(self, stream_handler):
        """Test automatic buffer reset after critical errors."""
        # Fill buffer completely to trigger processing
        chunk_size = 1024
        chunks_needed = stream_handler.buffer_size // chunk_size
        for _ in range(chunks_needed):
            chunk = np.random.random((chunk_size, 2))
            await stream_handler.process_chunk(chunk)
        initial_position = stream_handler.buffer_position

        # Simulate critical error
        async def error_process(*args, **kwargs):
            raise Exception("Critical error")

        with patch.object(stream_handler, '_process_buffer', side_effect=error_process):
            with pytest.raises(Exception):
                # Add one more chunk to trigger buffer processing
                chunk = np.random.random((chunk_size, 2))
                await stream_handler.process_chunk(chunk)

        # Verify buffer was reset
        assert stream_handler.buffer_position < initial_position
        assert not np.any(stream_handler.buffer)  # Buffer should be cleared

@pytest.mark.benchmark
class TestPerformanceBenchmarks:
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
        
        result = benchmark(process_chunk)
        assert benchmark.stats['mean'] < 0.01  # Mean processing time < 10ms
    
    def test_memory_usage_stability(self, benchmark):
        """Test memory usage stability during extended processing."""
        def measure_memory():
            handler = StreamHandler(buffer_size=16384)  # Large buffer
            chunk = np.random.random((1024, 2))
            
            # Process multiple chunks
            loop = asyncio.new_event_loop()
            try:
                for _ in range(10):
                    loop.run_until_complete(handler.process_chunk(chunk))
            finally:
                loop.close()
            
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # MB
        
        initial_memory = measure_memory()
        # Process more chunks
        final_memory = benchmark(measure_memory)
        
        # Memory usage should not grow significantly
        assert abs(final_memory - initial_memory) < 50  # Less than 50MB growth
    
    def test_concurrent_processing(self, stream_handler, benchmark):
        """Test performance with concurrent stream processing."""
        async def process_concurrent_streams(num_streams=3):
            chunks = [np.random.random((1024, 2)) for _ in range(num_streams)]
            tasks = [stream_handler.process_chunk(chunk) for chunk in chunks]
            return await asyncio.gather(*tasks)
        
        def run_concurrent():
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(process_concurrent_streams())
            finally:
                loop.close()
        
        results = benchmark(run_concurrent)
        assert benchmark.stats['mean'] < 0.05  # Mean processing time < 50ms 