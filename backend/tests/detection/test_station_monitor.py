"""Tests for the station monitor module."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.models.models import RadioStation, StationHealth, StationStatus
from backend.detection.station_monitor import StationMonitor
from backend.utils.streams.stream_checker import StreamChecker

@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    session = Mock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.query = Mock()
    return session

@pytest.fixture
def station_monitor(db_session):
    """Create a StationMonitor instance for testing."""
    return StationMonitor(db_session)

@pytest.fixture
def sample_station():
    """Create a sample radio station for testing."""
    return RadioStation(
        id=1,
        name="Test Radio",
        stream_url="http://test.stream/audio",
        country="SN",
        language="fr",
        is_active=True,
        last_checked=datetime.now(),
        status=StationStatus.active,
        failure_count=0
    )

@pytest.fixture
def mock_health_check():
    """Create a mock health check response."""
    return {
        'is_available': True,
        'is_audio_stream': True,
        'status_code': 200,
        'latency': 100,
        'content_type': 'audio/mpeg'
    }

@pytest.mark.asyncio
async def test_start_monitoring_success(station_monitor, sample_station, mock_health_check, db_session):
    """Test successful start of station monitoring."""
    # Mock database query
    db_session.query.return_value.filter.return_value.first.return_value = sample_station
    
    # Mock health check
    with patch.object(station_monitor.stream_checker, 'check_stream_availability', 
                     return_value=mock_health_check):
        success = await station_monitor.start_monitoring(sample_station.id)
        
        assert success is True
        assert sample_station.is_active is True
        assert sample_station.status == StationStatus.active
        assert isinstance(sample_station.last_checked, datetime)
        assert db_session.commit.called

@pytest.mark.asyncio
async def test_start_monitoring_stream_unavailable(station_monitor, sample_station, db_session):
    """Test monitoring start with unavailable stream."""
    db_session.query.return_value.filter.return_value.first.return_value = sample_station
    
    mock_health = {'is_available': False, 'status_code': 404}
    with patch.object(station_monitor.stream_checker, 'check_stream_availability', 
                     return_value=mock_health):
        success = await station_monitor.start_monitoring(sample_station.id)
        
        assert success is False
        assert sample_station.status == StationStatus.inactive
        assert db_session.commit.called

@pytest.mark.asyncio
async def test_start_monitoring_invalid_station(station_monitor, db_session):
    """Test monitoring start with invalid station ID."""
    db_session.query.return_value.filter.return_value.first.return_value = None
    
    success = await station_monitor.start_monitoring(999)
    assert success is False
    assert not db_session.commit.called

@pytest.mark.asyncio
async def test_stop_monitoring_success(station_monitor, sample_station, db_session):
    """Test successful stop of station monitoring."""
    db_session.query.return_value.filter.return_value.first.return_value = sample_station
    
    success = await station_monitor.stop_monitoring(sample_station.id)
    
    assert success is True
    assert sample_station.is_active is False
    assert db_session.commit.called

@pytest.mark.asyncio
async def test_check_stream_health_success(station_monitor, mock_health_check):
    """Test successful stream health check."""
    with patch.object(station_monitor.stream_checker, 'check_stream_availability', 
                     return_value=mock_health_check):
        health = await station_monitor.check_stream_health("http://test.stream")
        
        assert health['is_available'] is True
        assert health['is_audio_stream'] is True
        assert health['status_code'] == 200

@pytest.mark.asyncio
async def test_check_stream_health_error(station_monitor):
    """Test stream health check with error."""
    with patch.object(station_monitor.stream_checker, 'check_stream_availability', 
                     side_effect=Exception("Connection error")):
        health = await station_monitor.check_stream_health("http://test.stream")
        
        assert health['is_available'] is False
        assert health['is_audio_stream'] is False
        assert 'error' in health

@pytest.mark.asyncio
async def test_update_station_health_healthy(station_monitor, sample_station, mock_health_check, db_session):
    """Test updating station health with healthy status."""
    await station_monitor.update_station_health(sample_station, mock_health_check)
    
    assert sample_station.status == StationStatus.active
    assert isinstance(sample_station.last_checked, datetime)
    assert db_session.add.called
    assert db_session.commit.called

@pytest.mark.asyncio
async def test_update_station_health_degraded(station_monitor, sample_station, db_session):
    """Test updating station health with degraded status."""
    health_data = {
        'is_available': True,
        'is_audio_stream': True,
        'latency': 5000  # High latency
    }
    
    await station_monitor.update_station_health(sample_station, health_data)
    
    assert sample_station.status == StationStatus.inactive
    assert db_session.add.called

@pytest.mark.asyncio
async def test_monitor_all_stations(station_monitor, sample_station, mock_health_check, db_session):
    """Test monitoring all active stations."""
    # Mock active stations query
    db_session.query.return_value.filter.return_value.all.return_value = [sample_station]
    
    # Mock health check
    with patch.object(station_monitor.stream_checker, 'check_stream_availability', 
                     return_value=mock_health_check):
        results = await station_monitor.monitor_all_stations()
        
        assert len(results) == 1
        assert results[0]['station_id'] == sample_station.id
        assert results[0]['success'] is True

@pytest.mark.asyncio
async def test_handle_station_recovery_success(station_monitor, sample_station, mock_health_check, db_session):
    """Test successful station recovery."""
    sample_station.status = StationStatus.inactive
    sample_station.failure_count = 3
    db_session.query.return_value.filter.return_value.first.return_value = sample_station
    
    with patch.object(station_monitor.stream_checker, 'check_stream_availability', 
                     return_value=mock_health_check):
        await station_monitor.handle_station_recovery(sample_station.id)
        
        assert sample_station.status == StationStatus.active
        assert sample_station.failure_count == 0
        assert db_session.commit.called

@pytest.mark.asyncio
async def test_handle_station_recovery_invalid_station(station_monitor, db_session):
    """Test station recovery with invalid station ID."""
    db_session.query.return_value.filter.return_value.first.return_value = None
    
    await station_monitor.handle_station_recovery(999)
    assert not db_session.commit.called

@pytest.mark.asyncio
async def test_cleanup_old_health_records(station_monitor, db_session):
    """Test cleanup of old health records."""
    # Mock query for old records
    mock_query = Mock()
    db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.delete.return_value = 10  # 10 records deleted
    
    deleted_count = await station_monitor.cleanup_old_health_records(days=7)
    
    assert deleted_count == 10
    assert db_session.commit.called

@pytest.mark.asyncio
async def test_database_error_handling(station_monitor, sample_station, mock_health_check, db_session):
    """Test handling of database errors."""
    db_session.query.return_value.filter.return_value.first.return_value = sample_station
    db_session.commit.side_effect = SQLAlchemyError("Database error")
    
    with patch.object(station_monitor.stream_checker, 'check_stream_availability', 
                     return_value=mock_health_check):
        success = await station_monitor.start_monitoring(sample_station.id)
        
        assert success is False
        assert db_session.rollback.called

@pytest.mark.asyncio
async def test_concurrent_monitoring(station_monitor, mock_health_check, db_session):
    """Test concurrent monitoring of multiple stations."""
    stations = [
        RadioStation(id=1, name="Radio 1", stream_url="http://test1.stream", is_active=True),
        RadioStation(id=2, name="Radio 2", stream_url="http://test2.stream", is_active=True),
        RadioStation(id=3, name="Radio 3", stream_url="http://test3.stream", is_active=True)
    ]
    
    db_session.query.return_value.filter.return_value.all.return_value = stations
    
    with patch.object(station_monitor.stream_checker, 'check_stream_availability', 
                     return_value=mock_health_check):
        results = await station_monitor.monitor_all_stations()
        
        assert len(results) == 3
        assert all(result['success'] for result in results)

@pytest.mark.asyncio
async def test_performance_monitoring(station_monitor, sample_station, mock_health_check, db_session):
    """Test performance aspects of monitoring."""
    db_session.query.return_value.filter.return_value.first.return_value = sample_station
    
    with patch.object(station_monitor.stream_checker, 'check_stream_availability', 
                     return_value=mock_health_check):
        start_time = datetime.now()
        await station_monitor.start_monitoring(sample_station.id)
        duration = (datetime.now() - start_time).total_seconds()
        
        assert duration < 1.0  # Should complete within 1 second 