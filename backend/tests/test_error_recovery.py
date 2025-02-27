import pytest
import asyncio
from unittest.mock import patch, MagicMock
from aioresponses import aioresponses
from datetime import datetime, timedelta

from backend.detection.audio_processor.core import AudioProcessor
from backend.detection.audio_processor.external_services import (
    MusicBrainzService,
    AuddService,
    ExternalServiceError
)
from backend.utils.stream_checker import StreamChecker
from backend.models.models import RadioStation as Station
from backend.models.models import Track, TrackDetection as Detection

@pytest.fixture
def mock_audio_processor():
    return AudioProcessor(
        musicbrainz_service=MagicMock(),
        audd_service=MagicMock(),
        stream_checker=MagicMock()
    )

@pytest.fixture
def mock_stream_checker():
    return StreamChecker()

@pytest.mark.asyncio
async def test_stream_reconnection_after_failure(mock_audio_processor, mock_stream_checker):
    """Test automatic stream reconnection after connection failure."""
    station = Station(
        id=1,
        name="Test Radio",
        url="http://test.stream",
        is_active=True
    )
    
    # Simulate stream failure
    mock_stream_checker.check_stream_availability.side_effect = [
        {"is_available": False, "error": "Connection refused"},
        {"is_available": True, "is_audio_stream": True}
    ]
    
    # First attempt fails
    result = await mock_audio_processor.process_stream(station)
    assert result["status"] == "error"
    assert "Connection refused" in result["message"]
    
    # Second attempt succeeds after retry
    result = await mock_audio_processor.process_stream(station)
    assert result["status"] == "success"
    assert result["is_connected"] is True

@pytest.mark.asyncio
async def test_detection_retry_after_service_failure(mock_audio_processor):
    """Test detection retry after external service failure."""
    audio_data = b"test_audio_data"
    
    # Configure MusicBrainz service to fail first, then succeed
    mock_audio_processor.musicbrainz_service.detect_track.side_effect = [
        ExternalServiceError("Service unavailable"),
        {
            "title": "Test Track",
            "artist": "Test Artist",
            "confidence": 0.95
        }
    ]
    
    # First attempt fails
    with pytest.raises(ExternalServiceError):
        await mock_audio_processor.detect_track(audio_data)
    
    # Second attempt succeeds
    result = await mock_audio_processor.detect_track(audio_data)
    assert result["title"] == "Test Track"
    assert result["artist"] == "Test Artist"

@pytest.mark.asyncio
async def test_database_retry_on_lock(mock_audio_processor, db_session):
    """Test database operation retry on lock."""
    detection = Detection(
        track_id=1,
        station_id=1,
        detected_at=datetime.utcnow(),
        confidence=0.95
    )
    
    # Simulate database lock
    with patch("sqlalchemy.orm.Session.commit") as mock_commit:
        mock_commit.side_effect = [
            Exception("database is locked"),
            None  # Success on second attempt
        ]
        
        await mock_audio_processor.save_detection(detection, max_retries=2)
        assert mock_commit.call_count == 2

@pytest.mark.asyncio
async def test_recovery_from_invalid_audio_data(mock_audio_processor):
    """Test recovery from invalid audio data."""
    invalid_audio = b"invalid_data"
    valid_audio = b"valid_audio_data"
    
    # Configure feature extractor to handle invalid then valid data
    mock_audio_processor.feature_extractor.extract_features.side_effect = [
        ValueError("Invalid audio format"),
        {"features": [1.0, 2.0, 3.0]}
    ]
    
    # First attempt with invalid data
    result = await mock_audio_processor.process_audio(invalid_audio)
    assert result["status"] == "error"
    assert "Invalid audio format" in result["message"]
    
    # Second attempt with valid data
    result = await mock_audio_processor.process_audio(valid_audio)
    assert result["status"] == "success"
    assert "features" in result["data"]

@pytest.mark.asyncio
async def test_redis_connection_recovery(mock_audio_processor, redis_client):
    """Test Redis connection recovery after failure."""
    # Simulate Redis connection failure then recovery
    with patch("backend.utils.redis_config.get_redis") as mock_redis:
        mock_redis.side_effect = [
            ConnectionError("Redis connection failed"),
            redis_client
        ]
        
        # First attempt fails
        with pytest.raises(ConnectionError):
            await mock_audio_processor.update_cache()
        
        # Second attempt succeeds
        await mock_audio_processor.update_cache()
        assert mock_redis.call_count == 2

@pytest.mark.asyncio
async def test_websocket_reconnection(mock_audio_processor):
    """Test WebSocket reconnection after connection drop."""
    # Simulate WebSocket connection drop and reconnection
    mock_audio_processor.websocket_manager.is_connected.side_effect = [
        False,
        True
    ]
    
    # First check shows disconnected
    assert not await mock_audio_processor.check_websocket_connection()
    
    # Reconnection attempt
    result = await mock_audio_processor.reconnect_websocket()
    assert result["status"] == "success"
    assert await mock_audio_processor.check_websocket_connection()

@pytest.mark.asyncio
async def test_api_rate_limit_recovery(mock_audio_processor):
    """Test recovery from API rate limiting."""
    audio_data = b"test_audio_data"
    
    # Configure API to simulate rate limit then success
    mock_audio_processor.audd_service.detect_track.side_effect = [
        ExternalServiceError("Rate limit exceeded"),
        {
            "title": "Test Track",
            "artist": "Test Artist",
            "confidence": 0.85
        }
    ]
    
    # First attempt hits rate limit
    with pytest.raises(ExternalServiceError) as exc_info:
        await mock_audio_processor.detect_track(audio_data)
    assert "Rate limit exceeded" in str(exc_info.value)
    
    # Wait for rate limit reset
    await asyncio.sleep(1)
    
    # Second attempt succeeds
    result = await mock_audio_processor.detect_track(audio_data)
    assert result["title"] == "Test Track"
    assert result["artist"] == "Test Artist"

@pytest.mark.asyncio
async def test_memory_recovery(mock_audio_processor):
    """Test recovery from memory pressure."""
    # Simulate high memory usage then normal
    with patch("psutil.virtual_memory") as mock_memory:
        mock_memory.return_value.percent = 95  # High memory usage
        
        # First attempt should trigger memory management
        result = await mock_audio_processor.process_batch()
        assert result["status"] == "warning"
        assert "High memory usage" in result["message"]
        
        mock_memory.return_value.percent = 70  # Normal memory usage
        
        # Second attempt succeeds
        result = await mock_audio_processor.process_batch()
        assert result["status"] == "success"

@pytest.mark.asyncio
async def test_disk_space_recovery(mock_audio_processor):
    """Test recovery from low disk space."""
    # Simulate low disk space then normal
    with patch("psutil.disk_usage") as mock_disk:
        mock_disk.return_value.percent = 95  # Low disk space
        
        # First attempt should trigger disk space management
        result = await mock_audio_processor.save_audio_file(b"test_data")
        assert result["status"] == "warning"
        assert "Low disk space" in result["message"]
        
        mock_disk.return_value.percent = 70  # Normal disk space
        
        # Second attempt succeeds
        result = await mock_audio_processor.save_audio_file(b"test_data")
        assert result["status"] == "success"

@pytest.mark.asyncio
async def test_cpu_load_recovery(mock_audio_processor):
    """Test recovery from high CPU load."""
    # Simulate high CPU load then normal
    with patch("psutil.cpu_percent") as mock_cpu:
        mock_cpu.return_value = 95  # High CPU load
        
        # First attempt should trigger load management
        result = await mock_audio_processor.process_audio(b"test_data")
        assert result["status"] == "warning"
        assert "High CPU load" in result["message"]
        
        mock_cpu.return_value = 50  # Normal CPU load
        
        # Second attempt succeeds
        result = await mock_audio_processor.process_audio(b"test_data")
        assert result["status"] == "success" 