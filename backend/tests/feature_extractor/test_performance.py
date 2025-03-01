"""Performance tests for the FeatureExtractor class."""

import pytest
import numpy as np
import io
import time
import asyncio
import soundfile as sf
import psutil
import os
import threading
from backend.detection.audio_processor.feature_extractor import FeatureExtractor

@pytest.fixture
def performance_audio_data():
    """Generate audio data of different durations for performance testing."""
    sample_rate = 22050
    durations = [1, 2, 3, 5, 10]  # seconds
    audio_data = {}
    
    for duration in durations:
        t = np.linspace(0, duration, int(sample_rate * duration))
        frequency = 440  # Hz (A4 note)
        audio = np.sin(2 * np.pi * frequency * t)
        audio_data[duration] = audio.astype(np.float32)
    
    return audio_data

class TestFeatureExtractorPerformance:
    """Performance test cases for FeatureExtractor."""
    
    def setup_method(self):
        """Set up test environment."""
        self.extractor = FeatureExtractor()
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, performance_audio_data):
        """Test concurrent processing capabilities."""
        async def process_audio(audio: np.ndarray) -> Dict[str, Any]:
            """Process audio and return features."""
            # Convert to bytes
            audio_bytes = io.BytesIO()
            sf.write(audio_bytes, audio, self.extractor.sample_rate, format='WAV')
            return await self.extractor.analyze_audio(audio_bytes.getvalue())
        
        # Process 5 concurrent audio streams
        audio = performance_audio_data[3]  # Use 3s audio
        tasks = [process_audio(audio) for _ in range(5)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        processing_time = time.time() - start_time
        
        assert len(results) == 5
        assert processing_time < 10  # Should process 5 streams in under 10 seconds
    
    def test_feature_extraction_benchmark(self, performance_audio_data, benchmark):
        """Benchmark feature extraction performance."""
        audio = performance_audio_data[3]  # Use 3s audio for benchmarking
        
        result = benchmark(lambda: self.extractor.extract_features(audio))
        
        assert isinstance(result, dict)
        assert all(key in result for key in ["mel_spectrogram", "mfcc", "spectral_contrast", "chroma"])
        
        # Verify benchmark results
        stats = benchmark.stats
        assert stats.mean < 0.3  # Mean time should be less than 300ms
        assert stats.stddev < 0.1  # Standard deviation should be reasonable

def get_process_memory() -> float:
    """Get current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

@pytest.mark.performance
class TestFeatureExtractorPerformance:
    """Performance tests for FeatureExtractor."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up FeatureExtractor instance."""
        self.extractor = FeatureExtractor()
    
    def test_feature_extraction_latency(self, performance_audio_data):
        """Test feature extraction latency for different audio lengths."""
        latencies = {}
        
        for duration, audio in performance_audio_data.items():
            start_time = time.time()
            features = self.extractor.extract_features(audio)
            latency = time.time() - start_time
            latencies[duration] = latency
            
            # Latency requirements:
            # - 1s audio: < 100ms
            # - 3s audio: < 300ms
            # - 5s audio: < 500ms
            # - 10s audio: < 1s
            max_latency = duration / 10  # 10% of audio duration
            assert latency < max_latency, f"Feature extraction for {duration}s audio took {latency:.3f}s"
    
    def test_memory_usage(self, performance_audio_data):
        """Test memory usage during feature extraction."""
        initial_memory = get_process_memory()
        
        # Process audio data
        audio = performance_audio_data[5]  # 5 second audio
        features = self.extractor.extract_features(audio)
        
        # Check memory usage
        final_memory = get_process_memory()
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100, f"Memory increase of {memory_increase:.2f}MB is too high"
    
    def test_cpu_usage(self, performance_audio_data):
        """Test CPU usage during feature extraction."""
        cpu_usage = []
        stop_monitoring = threading.Event()

        def monitor_cpu():
            while not stop_monitoring.is_set():
                cpu_usage.append(psutil.cpu_percent(interval=0.1))
                time.sleep(0.1)

        # Start CPU monitoring
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()

        try:
            # Process 5s audio
            audio = performance_audio_data[5]
            features = self.extractor.extract_features(audio)
        finally:
            # Stop CPU monitoring
            stop_monitoring.set()
            monitor_thread.join()

        # Ensure we have some CPU measurements
        assert len(cpu_usage) > 0, "No CPU measurements collected"
        
        # Calculate average CPU usage
        avg_cpu = np.mean(cpu_usage) if cpu_usage else 0
        max_cpu = np.max(cpu_usage) if cpu_usage else 0
        
        # CPU usage should be reasonable
        assert avg_cpu < 80, f"Average CPU usage of {avg_cpu:.2f}% is too high"
        assert max_cpu < 95, f"Maximum CPU usage of {max_cpu:.2f}% is too high" 