"""Tests for the radio manager module."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from backend.models.database import SessionLocal
from backend.models.models import RadioStation, Track, TrackDetection
from backend.utils.radio.manager import RadioManager


@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    session = Mock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def radio_manager(db_session):
    """Create a RadioManager instance for testing."""
    return RadioManager(db_session)


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
    )


@pytest.mark.asyncio
async def test_start_monitoring(radio_manager, sample_station, db_session):
    """Test starting station monitoring."""
    db_session.query.return_value.filter.return_value.first.return_value = sample_station

    success = await radio_manager.start_monitoring(sample_station.id)
    assert success is True
    assert sample_station.is_active is True


@pytest.mark.asyncio
async def test_stop_monitoring(radio_manager, sample_station, db_session):
    """Test stopping station monitoring."""
    db_session.query.return_value.filter.return_value.first.return_value = sample_station

    success = await radio_manager.stop_monitoring(sample_station.id)
    assert success is True
    assert sample_station.is_active is False


@pytest.mark.asyncio
async def test_process_station_stream(radio_manager, sample_station):
    """Test processing station stream."""
    with patch(
        "backend.utils.streams.stream_checker.StreamChecker.check_stream_availability"
    ) as mock_check:
        mock_check.return_value = {
            "is_available": True,
            "is_audio_stream": True,
            "status_code": 200,
        }

        result = await radio_manager.process_station_stream(sample_station.id)
        assert result is not None
        assert result["status"] == "success"


@pytest.mark.asyncio
async def test_get_active_stations(radio_manager, db_session):
    """Test getting active stations."""
    stations = [
        RadioStation(id=1, name="Radio 1", is_active=True),
        RadioStation(id=2, name="Radio 2", is_active=True),
        RadioStation(id=3, name="Radio 3", is_active=False),
    ]
    db_session.query.return_value.filter.return_value.all.return_value = stations

    active_stations = radio_manager.get_active_stations()
    assert len(active_stations) == 2
    assert all(station.is_active for station in active_stations)


@pytest.mark.asyncio
async def test_get_performance_metrics(radio_manager):
    """Test getting performance metrics."""
    metrics = radio_manager.get_performance_metrics()
    assert isinstance(metrics, dict)
    assert "total_detections" in metrics
    assert "average_confidence" in metrics
    assert "active_monitors" in metrics
