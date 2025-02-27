import pytest
import asyncio
import time
import psutil
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict
from datetime import datetime, timedelta

from backend.detection.audio_processor.core import AudioProcessor
from backend.models.models import RadioStation as Station, Track, TrackDetection as Detection

@pytest.fixture
def audio_processor():
    return AudioProcessor()

@pytest.fixture
def test_stations(db_session) -> List[Station]:
    """Create test stations for performance testing."""
    stations = []
    for i in range(10):
        station = Station(
            name=f"Test Station {i}",
            url=f"http://test{i}.stream",
            is_active=True
        )
        db_session.add(station)
        stations.append(station)
    db_session.commit()
    return stations

@pytest.fixture
def test_tracks(db_session) -> List[Track]:
    """Create test tracks for performance testing."""
    tracks = []
    for i in range(100):
        track = Track(
            title=f"Test Track {i}",
            artist=f"Test Artist {i % 10}",
            duration=180
        )
        db_session.add(track)
        tracks.append(track)
    db_session.commit()
    return tracks

def generate_audio_data(duration_seconds: int) -> bytes:
    """Generate synthetic audio data for testing."""
    sample_rate = 44100
    num_samples = duration_seconds * sample_rate
    audio_data = np.random.uniform(-1, 1, num_samples)
    return audio_data.tobytes()

@pytest.mark.benchmark
async def test_audio_processing_performance(audio_processor, benchmark):
    """Test audio processing performance."""
    audio_data = generate_audio_data(10)  # 10 seconds of audio
    
    def process_audio():
        return asyncio.run(audio_processor.process_audio(audio_data))
    
    # Run benchmark
    result = benchmark(process_audio)
    
    # Assert performance requirements
    assert result.stats["mean"] < 1.0  # Mean processing time should be under 1 second
    assert result.stats["max"] < 2.0   # Max processing time should be under 2 seconds

@pytest.mark.benchmark
async def test_concurrent_stream_processing(audio_processor, test_stations, benchmark):
    """Test performance of concurrent stream processing."""
    async def process_streams():
        tasks = [
            audio_processor.process_stream(station)
            for station in test_stations
        ]
        return await asyncio.gather(*tasks)
    
    # Run benchmark
    result = benchmark(process_streams)
    
    # Assert performance requirements
    assert result.stats["mean"] < 5.0  # Mean processing time should be under 5 seconds
    assert result.stats["max"] < 10.0  # Max processing time should be under 10 seconds

@pytest.mark.benchmark
async def test_database_write_performance(db_session, test_stations, test_tracks, benchmark):
    """Test database write performance."""
    detections = []
    now = datetime.utcnow()
    
    # Prepare test data
    for i in range(1000):  # Test with 1000 detections
        detection = Detection(
            track_id=test_tracks[i % 100].id,
            station_id=test_stations[i % 10].id,
            detected_at=now + timedelta(seconds=i),
            confidence=0.95
        )
        detections.append(detection)
    
    def bulk_insert():
        db_session.bulk_save_objects(detections)
        db_session.commit()
    
    # Run benchmark
    result = benchmark(bulk_insert)
    
    # Assert performance requirements
    assert result.stats["mean"] < 2.0  # Mean insert time should be under 2 seconds
    assert result.stats["max"] < 4.0   # Max insert time should be under 4 seconds

@pytest.mark.benchmark
async def test_memory_usage(audio_processor):
    """Test memory usage during processing."""
    initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    
    # Process multiple audio streams
    audio_data = [generate_audio_data(5) for _ in range(10)]
    tasks = [audio_processor.process_audio(data) for data in audio_data]
    await asyncio.gather(*tasks)
    
    final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    # Assert memory usage requirements
    assert memory_increase < 500  # Memory increase should be under 500MB

@pytest.mark.benchmark
async def test_cpu_usage(audio_processor):
    """Test CPU usage during processing."""
    cpu_percent = psutil.cpu_percent()
    
    # Process multiple audio streams
    audio_data = [generate_audio_data(5) for _ in range(10)]
    tasks = [audio_processor.process_audio(data) for data in audio_data]
    await asyncio.gather(*tasks)
    
    final_cpu_percent = psutil.cpu_percent()
    cpu_increase = final_cpu_percent - cpu_percent
    
    # Assert CPU usage requirements
    assert cpu_increase < 80  # CPU usage increase should be under 80%

@pytest.mark.benchmark
async def test_redis_cache_performance(audio_processor, redis_client, benchmark):
    """Test Redis cache performance."""
    test_data = {f"key_{i}": f"value_{i}" for i in range(1000)}
    
    async def cache_operations():
        # Write operations
        await redis_client.mset(test_data)
        
        # Read operations
        await redis_client.mget(test_data.keys())
    
    # Run benchmark
    result = benchmark(cache_operations)
    
    # Assert performance requirements
    assert result.stats["mean"] < 0.5  # Mean operation time should be under 0.5 seconds
    assert result.stats["max"] < 1.0   # Max operation time should be under 1 second

@pytest.mark.benchmark
async def test_websocket_broadcast_performance(audio_processor, benchmark):
    """Test WebSocket broadcast performance."""
    message = {"type": "detection", "data": {"track": "Test Track", "station": "Test Station"}}
    connections = [MagicMock() for _ in range(100)]  # Simulate 100 connections
    
    async def broadcast():
        await audio_processor.websocket_manager.broadcast(message, connections)
    
    # Run benchmark
    result = benchmark(broadcast)
    
    # Assert performance requirements
    assert result.stats["mean"] < 0.1  # Mean broadcast time should be under 0.1 seconds
    assert result.stats["max"] < 0.2   # Max broadcast time should be under 0.2 seconds

@pytest.mark.benchmark
async def test_api_endpoint_performance(client, benchmark):
    """Test API endpoint performance."""
    async def api_request():
        response = await client.get("/api/stations")
        assert response.status_code == 200
    
    # Run benchmark
    result = benchmark(api_request)
    
    # Assert performance requirements
    assert result.stats["mean"] < 0.1  # Mean response time should be under 0.1 seconds
    assert result.stats["max"] < 0.2   # Max response time should be under 0.2 seconds

@pytest.mark.benchmark
async def test_detection_pipeline_performance(audio_processor, benchmark):
    """Test end-to-end detection pipeline performance."""
    audio_data = generate_audio_data(30)  # 30 seconds of audio
    
    async def process_pipeline():
        # Feature extraction
        features = await audio_processor.extract_features(audio_data)
        
        # Music detection
        is_music = await audio_processor.detect_music(features)
        
        if is_music:
            # Track detection
            track = await audio_processor.detect_track(features)
            
            if track:
                # Save detection
                await audio_processor.save_detection(track)
    
    # Run benchmark
    result = benchmark(process_pipeline)
    
    # Assert performance requirements
    assert result.stats["mean"] < 3.0  # Mean pipeline time should be under 3 seconds
    assert result.stats["max"] < 5.0   # Max pipeline time should be under 5 seconds

@pytest.mark.benchmark
async def test_load_handling(audio_processor, test_stations):
    """Test system behavior under load."""
    start_time = time.time()
    cpu_samples = []
    memory_samples = []
    
    # Monitor system resources while processing
    async def monitor_resources():
        while time.time() - start_time < 60:  # Monitor for 60 seconds
            cpu_samples.append(psutil.cpu_percent())
            memory_samples.append(psutil.Process().memory_info().rss / 1024 / 1024)
            await asyncio.sleep(1)
    
    # Generate load
    async def generate_load():
        while time.time() - start_time < 60:
            tasks = [
                audio_processor.process_stream(station)
                for station in test_stations
            ]
            await asyncio.gather(*tasks)
    
    # Run monitoring and load generation concurrently
    await asyncio.gather(
        monitor_resources(),
        generate_load()
    )
    
    # Assert resource usage requirements
    assert max(cpu_samples) < 90     # Max CPU usage should be under 90%
    assert max(memory_samples) < 1024  # Max memory usage should be under 1GB 