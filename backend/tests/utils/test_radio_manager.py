"""Tests for the RadioManager module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session

from backend.utils.radio_manager import RadioManager
from backend.models.models import RadioStation, StationStatus, Track, TrackDetection, TrackStats
from backend.audio_processor import AudioProcessor

@pytest.fixture
def mock_audio_processor():
    """Fixture for mocked AudioProcessor."""
    processor = Mock(spec=AudioProcessor)
    processor.process_stream = AsyncMock()
    processor.analyze_stream = AsyncMock()
    processor.detect_music = AsyncMock()
    processor.recognize = AsyncMock(return_value={
        'is_music': True,
        'track': {
            'title': 'Test Track',
            'artist': 'Test Artist',
            'album': 'Test Album'
        },
        'confidence': 0.95,
        'duration_seconds': 180
    })
    return processor

@pytest.fixture
def db_session():
    """Create a mock database session."""
    session = Mock(spec=Session)
    session.query = Mock(return_value=session)
    session.filter = Mock(return_value=session)
    session.first = Mock(return_value=None)
    session.all = Mock(return_value=[])
    return session

@pytest.fixture
def sample_station():
    return RadioStation(
        id=1,
        name="Test Radio",
        stream_url="http://test.stream",
        country="SN",
        language="fr",
        region="Dakar",
        type="radio",
        status=StationStatus.active,
        is_active=True,
        last_checked=datetime.utcnow()
    )

@pytest.fixture
def sample_track():
    return Track(
        id=1,
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        play_count=1,
        total_play_time=timedelta(minutes=3),
        last_played=datetime.utcnow()
    )

@pytest.fixture
def sample_detection(sample_station, sample_track):
    return TrackDetection(
        id=1,
        station_id=sample_station.id,
        track_id=sample_track.id,
        confidence=0.95,
        detected_at=datetime.utcnow(),
        play_duration=timedelta(minutes=3)
    )

@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.query = Mock()
    mock.query.return_value.filter = Mock()
    mock.query.return_value.filter.return_value.first = Mock()
    mock.query.return_value.filter.return_value.all = Mock()
    mock.query.return_value.get = Mock()
    return mock

@pytest.fixture
async def radio_manager(mock_db, mock_audio_processor):
    """Create a RadioManager instance for testing."""
    manager = RadioManager(db=mock_db, audio_processor=mock_audio_processor)
    manager._download_audio_sample = AsyncMock(return_value=b'audio_data')
    manager.monitoring_tasks = {}
    manager.detection_tasks = {}
    manager.music_recognizer = mock_audio_processor
    return manager

@pytest.mark.asyncio
async def test_check_station_status(radio_manager, sample_station):
    """Test checking station status."""
    with patch('backend.utils.radio_fetcher.check_stream_status', return_value=True):
        result = await radio_manager.check_station_status(sample_station)
        assert result is True

@pytest.mark.asyncio
async def test_detect_music_all_stations(radio_manager, sample_station, sample_track):
    """Test detecting music on all stations."""
    radio_manager.db.query.return_value.filter.return_value.all.return_value = [sample_station]
    radio_manager.db.query.return_value.filter.return_value.first.return_value = sample_track
    
    await radio_manager.detect_music_all_stations()
    
    radio_manager.music_recognizer.recognize.assert_called_once()
    radio_manager.db.add.assert_called()
    radio_manager.db.commit.assert_called()

@pytest.mark.asyncio
async def test_process_detection(radio_manager, sample_detection):
    """Test processing a detection."""
    await radio_manager.process_detection(sample_detection)
    radio_manager.db.add.assert_called_once()
    radio_manager.db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_update_senegal_stations(radio_manager):
    """Test updating Senegal radio stations."""
    with patch('backend.utils.radio_fetcher.RadioFetcher.get_senegal_stations', return_value=[{
        'name': 'Test Radio',
        'stream_url': 'http://test.stream',
        'country': 'SN',
        'city': 'Dakar',
        'language': 'fr',
        'is_active': True
    }]):
        result = radio_manager.update_senegal_stations()
        assert result['status'] == 'success'
        radio_manager.db.add.assert_called()
        radio_manager.db.commit.assert_called()

@pytest.mark.asyncio
async def test_start_stop_monitoring(radio_manager, sample_station):
    """Test starting and stopping station monitoring."""
    await radio_manager.start_monitoring(sample_station)
    assert sample_station.id in radio_manager.monitoring_tasks
    await radio_manager.stop_monitoring(sample_station)
    assert sample_station.id not in radio_manager.monitoring_tasks

@pytest.mark.asyncio
async def test_get_performance_metrics(radio_manager):
    """Test getting performance metrics."""
    metrics = await radio_manager.get_performance_metrics()
    assert 'total_detections' in metrics
    assert 'active_stations' in metrics
    assert 'average_confidence' in metrics
    assert 'monitoring_tasks' in metrics

@pytest.mark.asyncio
async def test_cleanup(radio_manager):
    """Test cleanup of resources."""
    # Add some tasks to cleanup
    task1 = AsyncMock()
    task2 = AsyncMock()
    radio_manager.detection_tasks = {1: task1, 2: task2}
    radio_manager.active_stations = {1: {'status': 'active'}, 2: {'status': 'active'}}
    
    radio_manager.cleanup()
    
    task1.cancel.assert_called_once()
    task2.cancel.assert_called_once()
    assert len(radio_manager.detection_tasks) == 0
    assert len(radio_manager.active_stations) == 0

@pytest.mark.asyncio
async def test_get_redis(mock_redis):
    """Test getting Redis connection."""
    from backend.utils.redis_config import get_redis
    
    with patch('backend.utils.redis_config.get_settings') as mock_settings:
        mock_settings.return_value.REDIS_HOST = 'localhost'
        mock_settings.return_value.REDIS_PORT = 6379
        mock_settings.return_value.REDIS_DB = 0
        
        redis_client = get_redis()
        assert redis_client is not None
        mock_redis.assert_called_once()

@pytest.mark.asyncio
async def test_get_active_stations(radio_manager, sample_station):
    """Test getting active stations."""
    radio_manager.db.query.return_value.filter.return_value.all.return_value = [sample_station]
    stations = radio_manager.get_active_stations()
    assert len(stations) == 1
    assert stations[0].name == "Test Radio"

@pytest.mark.asyncio
async def test_update_station_status(radio_manager, sample_station):
    """Test updating station status."""
    radio_manager.db.query.return_value.get.return_value = sample_station
    radio_manager.update_station_status(1, StationStatus.inactive)
    assert sample_station.status == StationStatus.inactive
    radio_manager.db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_get_station_by_url(radio_manager, sample_station):
    """Test getting station by URL."""
    radio_manager.db.query.return_value.filter.return_value.first.return_value = sample_station
    station = radio_manager.get_station_by_url("http://test.stream")
    assert station == sample_station 