"""Tests for the Station Monitor module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.models.models import RadioStation, StationHealth
from backend.detection.station_monitor import StationMonitor

@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    session = Mock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
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
        last_check=datetime.now(),
        health_status="healthy"
    )

@pytest.mark.asyncio
async def test_start_monitoring_success(station_monitor, sample_station, db_session):
    """Test successful start of station monitoring."""
    # Mock database query
    db_session.query.return_value.filter.return_value.first.return_value = sample_station
    
    # Mock stream health check
    mock_health = {'is_available': True, 'is_audio_stream': True, 'status_code': 200}
    with patch.object(station_monitor, 'check_stream_health', return_value=mock_health):
        success = await station_monitor.start_monitoring(sample_station.id)
        
        assert success is True
        assert sample_station.is_active is True
        assert sample_station.health_status == "healthy"
        assert isinstance(sample_station.last_check, datetime)

@pytest.mark.asyncio
async def test_start_monitoring_stream_unavailable(station_monitor, sample_station, db_session):
    """Test monitoring start with unavailable stream."""
    db_session.query.return_value.filter.return_value.first.return_value = sample_station
    
    mock_health = {'is_available': False, 'status_code': 404}
    with patch.object(station_monitor, 'check_stream_health', return_value=mock_health):
        success = await station_monitor.start_monitoring(sample_station.id)
        
        assert success is False
        assert sample_station.health_status == "unavailable"

@pytest.mark.asyncio
async def test_start_monitoring_non_audio_stream(station_monitor, sample_station, db_session):
    """Test monitoring start with non-audio stream."""
    db_session.query.return_value.filter.return_value.first.return_value = sample_station
    
    mock_health = {'is_available': True, 'is_audio_stream': False, 'status_code': 200}
    with patch.object(station_monitor, 'check_stream_health', return_value=mock_health):
        success = await station_monitor.start_monitoring(sample_station.id)
        
        assert success is False
        assert sample_station.health_status == "invalid_stream"

@pytest.mark.asyncio
async def test_stop_monitoring_success(station_monitor, sample_station, db_session):
    """Test successful stop of station monitoring."""
    db_session.query.return_value.filter.return_value.first.return_value = sample_station
    
    success = await station_monitor.stop_monitoring(sample_station.id)
    
    assert success is True
    assert sample_station.is_active is False
    assert db_session.commit.called

@pytest.mark.asyncio
async def test_check_stream_health_success(station_monitor):
    """Test successful stream health check."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {'content-type': 'audio/mpeg'}
    
    with patch('aiohttp.ClientSession.head', return_value=mock_response):
        health = await station_monitor.check_stream_health("http://test.stream/audio")
        
        assert health['is_available'] is True
        assert health['is_audio_stream'] is True
        assert health['status_code'] == 200

@pytest.mark.asyncio
async def test_check_stream_health_connection_error(station_monitor):
    """Test stream health check with connection error."""
    with patch('aiohttp.ClientSession.head', side_effect=Exception("Connection error")):
        health = await station_monitor.check_stream_health("http://test.stream/audio")
        
        assert health['is_available'] is False
        assert health['error'] == "Connection error"

@pytest.mark.asyncio
async def test_update_station_health_success(station_monitor, sample_station, db_session):
    """Test successful station health update."""
    health_data = {
        'is_available': True,
        'is_audio_stream': True,
        'status_code': 200,
        'latency': 150  # ms
    }
    
    await station_monitor.update_station_health(sample_station, health_data)
    
    assert sample_station.health_status == "healthy"
    assert sample_station.last_check is not None
    assert db_session.add.called
    assert db_session.commit.called

@pytest.mark.asyncio
async def test_update_station_health_with_issues(station_monitor, sample_station, db_session):
    """Test station health update with issues."""
    health_data = {
        'is_available': True,
        'is_audio_stream': True,
        'status_code': 200,
        'latency': 5000  # High latency
    }
    
    await station_monitor.update_station_health(sample_station, health_data)
    
    assert sample_station.health_status == "degraded"
    assert db_session.add.called

@pytest.mark.asyncio
async def test_monitor_all_stations(station_monitor, db_session):
    """Test monitoring of all active stations."""
    # Create multiple test stations
    stations = [
        RadioStation(id=1, stream_url="http://test1.stream", is_active=True),
        RadioStation(id=2, stream_url="http://test2.stream", is_active=True),
        RadioStation(id=3, stream_url="http://test3.stream", is_active=False)
    ]
    
    # Mock database query
    db_session.query.return_value.filter.return_value.all.return_value = stations
    
    # Mock health checks
    mock_health = {'is_available': True, 'is_audio_stream': True, 'status_code': 200}
    with patch.object(station_monitor, 'check_stream_health', return_value=mock_health):
        results = await station_monitor.monitor_all_stations()
        
        assert len(results) == 2  # Only active stations
        assert all(result['success'] for result in results)

@pytest.mark.asyncio
async def test_handle_station_recovery(station_monitor, sample_station, db_session):
    """Test handling of station recovery after failure."""
    # Set initial failed state
    sample_station.health_status = "unavailable"
    sample_station.failure_count = 3
    
    db_session.query.return_value.filter.return_value.first.return_value = sample_station
    
    # Mock successful health check
    mock_health = {'is_available': True, 'is_audio_stream': True, 'status_code': 200}
    with patch.object(station_monitor, 'check_stream_health', return_value=mock_health):
        await station_monitor.handle_station_recovery(sample_station.id)
        
        assert sample_station.health_status == "healthy"
        assert sample_station.failure_count == 0
        assert db_session.commit.called

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