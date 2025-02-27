"""Performance tests for the AudioProcessor class."""

import pytest
import numpy as np
from backend.detection.audio_processor import AudioProcessor

@pytest.fixture
def large_audio_data():
    """Generate a large audio sample for performance testing."""
    duration = 10.0  # 10 seconds
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration))
    # Generate a complex signal with multiple frequencies
    signal = (np.sin(2 * np.pi * 440 * t) +  # A4 note
             np.sin(2 * np.pi * 880 * t) +   # A5 note
             np.sin(2 * np.pi * 1760 * t))   # A6 note
    return signal

@pytest.fixture
def large_fingerprint_database():
    """Generate a large database of fingerprints for performance testing."""
    return [np.random.random((128,)) for _ in range(1000)]

@pytest.mark.benchmark(
    group="audio_processor",
    min_rounds=100,
    max_time=2.0
)
def test_process_stream_performance(benchmark, large_audio_data):
    """Benchmark the process_stream method."""
    processor = AudioProcessor()
    
    def run_process():
        return processor.process_stream(large_audio_data)
    
    result = benchmark(run_process)
    assert isinstance(result, tuple)
    assert len(result) == 2

@pytest.mark.benchmark(
    group="audio_processor",
    min_rounds=100,
    max_time=2.0
)
def test_feature_extraction_performance(benchmark, large_audio_data):
    """Benchmark the feature extraction method."""
    processor = AudioProcessor()
    
    def run_extraction():
        return processor.extract_features(large_audio_data)
    
    result = benchmark(run_extraction)
    assert isinstance(result, np.ndarray)
    assert result.shape == (128,)

@pytest.mark.benchmark(
    group="audio_processor",
    min_rounds=100,
    max_time=2.0
)
def test_fingerprint_matching_performance(benchmark, large_fingerprint_database):
    """Benchmark the fingerprint matching method."""
    processor = AudioProcessor()
    features = np.random.random((128,))
    
    def run_matching():
        return processor.match_fingerprint(features, large_fingerprint_database)
    
    result = benchmark(run_matching)
    assert result is None or isinstance(result, int)

@pytest.mark.benchmark(
    group="audio_processor",
    min_rounds=5,
    max_time=5.0
)
def test_end_to_end_performance(benchmark, large_audio_data, large_fingerprint_database):
    """Benchmark the entire audio processing pipeline."""
    processor = AudioProcessor()
    
    def run_pipeline():
        # Process audio stream
        is_music, confidence = processor.process_stream(large_audio_data)
        if is_music and confidence > 0.5:
            # Extract features
            features = processor.extract_features(large_audio_data)
            # Match fingerprint
            return processor.match_fingerprint(features, large_fingerprint_database)
        return None
    
    result = benchmark(run_pipeline)
    assert result is None or isinstance(result, int)

@pytest.mark.benchmark(
    group="audio_processor",
    min_rounds=10,
    max_time=2.0
)
def test_memory_usage(benchmark, large_audio_data):
    """Test memory usage during audio processing."""
    import psutil
    import os
    
    def get_memory_usage():
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # Convert to MB
    
    processor = AudioProcessor()
    initial_memory = get_memory_usage()
    
    def run_memory_test():
        # Process a large chunk of audio data
        processor.process_stream(large_audio_data)
        processor.extract_features(large_audio_data)
        return get_memory_usage() - initial_memory
    
    memory_increase = benchmark(run_memory_test)
    # Memory increase should be reasonable (less than 100MB)
    assert memory_increase < 100 