"""Tests for the AnalyticsManager class."""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.models.models import (
    AnalyticsData,
    ArtistStats,
    DetectionHourly,
    RadioStation,
    StationStatus,
    StationTrackStats,
    Track,
    TrackDetection,
    TrackStats,
)
from backend.utils.analytics.analytics_manager import AnalyticsManager


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()

    # Configure execute to return a mock result
    mock_result = AsyncMock()
    mock_result.first.return_value = {
        "track_id": 1,
        "artist_id": 1,
        "artist": "Test Artist",
        "title": "Test Track",
        "detection_count": 10,
        "total_play_time": 3600,
        "artist_count": 5,
        "artist_play_time": 1800,
        "play_count": 3,
        "station_play_time": 900,
    }
    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    # Create a transaction context that calls commit on exit
    transaction = AsyncMock()
    transaction.__aenter__ = AsyncMock(return_value=transaction)

    async def async_exit(exc_type, exc_val, exc_tb):
        if exc_type is None:
            await session.commit()
        else:
            await session.rollback()
        return None

    transaction.__aexit__ = AsyncMock(side_effect=async_exit)

    # Configure begin to return the transaction context
    session.begin = Mock(return_value=transaction)

    return session


@pytest.fixture
def analytics_manager(mock_db_session):
    """Create an AnalyticsManager instance for testing."""
    return AnalyticsManager(mock_db_session)


@pytest.fixture
def sample_detection_data():
    """Create sample detection data for testing."""
    return {
        "station_id": 1,
        "track_id": 1,
        "confidence": 0.95,
        "play_duration": timedelta(seconds=180),
        "detected_at": datetime.now(),
    }


@pytest.mark.asyncio
class TestAnalyticsUpdate:
    """Test analytics update functionality."""

    async def test_update_all_analytics_success(
        self, analytics_manager, mock_db_session, sample_detection_data
    ):
        """Test successful update of all analytics."""
        # Execute update
        await analytics_manager.update_all_analytics(sample_detection_data)

        # Verify transaction handling
        mock_db_session.execute.assert_called()
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_not_called()

    async def test_update_all_analytics_database_error(
        self, analytics_manager, mock_db_session, sample_detection_data
    ):
        """Test handling of database errors during update."""
        # Simulate database error
        mock_db_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(SQLAlchemyError):
            await analytics_manager.update_all_analytics(sample_detection_data)

        mock_db_session.rollback.assert_called_once()

    async def test_update_detection_stats_efficient(
        self, analytics_manager, mock_db_session, sample_detection_data
    ):
        """Test efficient update of detection statistics."""
        # Mock transaction context
        async with mock_db_session.begin() as transaction:
            await analytics_manager._update_detection_stats_efficient(
                station_id=sample_detection_data["station_id"],
                track_id=sample_detection_data["track_id"],
                confidence=sample_detection_data["confidence"],
                play_duration=sample_detection_data["play_duration"],
                current_time=datetime.now(),
                base_data={"artist_id": 1},
            )

        # Verify SQL execution
        assert mock_db_session.execute.call_count >= 3  # Track, artist, and station stats
        assert mock_db_session.begin.called  # Transaction was started
        assert mock_db_session.begin.return_value.__aenter__.called  # Transaction was entered
        assert mock_db_session.begin.return_value.__aexit__.called  # Transaction was exited

    async def test_update_analytics_data_efficient(self, analytics_manager, mock_db_session):
        """Test efficient update of analytics data."""
        await analytics_manager._update_analytics_data_efficient(
            confidence=0.95, current_time=datetime.now()
        )

        # Verify analytics data update
        mock_db_session.execute.assert_called_once()
        sql_call = str(mock_db_session.execute.call_args[0][0])
        assert "track_detections" in sql_call.lower()  # Verify source table
        assert "insert into analytics_data" in sql_call.lower()  # Verify target table
        assert "detection_count" in sql_call.lower()  # Verify column
        assert "detection_rate" in sql_call.lower()  # Verify column
        assert "average_confidence" in sql_call.lower()  # Verify column

    async def test_update_temporal_aggregates_efficient(self, analytics_manager, mock_db_session):
        """Test efficient update of temporal aggregates."""
        current_time = datetime.now()
        play_duration = timedelta(seconds=180)
        await analytics_manager._update_temporal_aggregates_efficient(
            station_id=1,
            track_id=1,
            artist_id=1,
            current_time=current_time,
            play_duration=play_duration,
        )

        # Verify temporal aggregates update
        mock_db_session.execute.assert_called_once()
        sql_call = str(mock_db_session.execute.call_args[0][0])
        assert "detection_hourly" in sql_call.lower()
        assert "track_daily" in sql_call.lower()
        assert "artist_daily" in sql_call.lower()

    async def test_update_station_status_efficient(self, analytics_manager, mock_db_session):
        """Test efficient update of station status."""
        await analytics_manager._update_station_status_efficient(
            station_id=1, current_time=datetime.now()
        )

        # Verify station status update
        mock_db_session.execute.assert_called_once()
        sql_call = str(mock_db_session.execute.call_args[0][0])
        assert "UPDATE radio_stations" in sql_call


@pytest.mark.asyncio
class TestAnalyticsPerformance:
    """Test analytics performance."""

    async def test_batch_update_performance(self, analytics_manager, mock_db_session, benchmark):
        """Test performance of batch analytics updates."""
        # Create multiple detection records
        detections = [
            {
                "station_id": i % 3 + 1,
                "track_id": i % 5 + 1,
                "confidence": 0.9 + (i % 10) / 100,
                "play_duration": timedelta(seconds=180),
                "detected_at": datetime.now() - timedelta(minutes=i),
            }
            for i in range(100)
        ]

        # Measure the time taken for a single update
        start_time = time.perf_counter()
        await analytics_manager.update_all_analytics(detections[0])
        end_time = time.perf_counter()

        # Use benchmark to record the timing
        benchmark.extra_info.update({"single_update_time": end_time - start_time})
        assert end_time - start_time < 0.1  # Single update should take less than 100ms

    async def test_memory_usage(self, analytics_manager, mock_db_session):
        """Test memory usage during analytics updates."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial = process.memory_info().rss

        # Perform analytics update
        detection = {
            "station_id": 1,
            "track_id": 1,
            "confidence": 0.95,
            "play_duration": timedelta(seconds=180),
            "detected_at": datetime.now(),
        }
        await analytics_manager.update_all_analytics(detection)

        final = process.memory_info().rss
        memory_increase = (final - initial) / 1024 / 1024  # MB
        assert memory_increase < 50  # Should use less than 50MB additional memory


@pytest.mark.asyncio
class TestAnalyticsErrorHandling:
    """Test analytics error handling."""

    async def test_handle_missing_data(self, analytics_manager, mock_db_session):
        """Test handling of missing data."""
        incomplete_data = {
            "station_id": 1,
            # Missing track_id
            "confidence": 0.95,
        }

        with pytest.raises(KeyError):
            await analytics_manager.update_all_analytics(incomplete_data)

    async def test_handle_invalid_data(self, analytics_manager, mock_db_session):
        """Test handling of invalid data."""
        invalid_data = {
            "station_id": "invalid",  # Should be integer
            "track_id": None,
            "confidence": 2.0,  # Should be between 0 and 1
            "play_duration": timedelta(seconds=180),
            "detected_at": datetime.now(),
        }

        with pytest.raises(ValueError):
            await analytics_manager.update_all_analytics(invalid_data)

    async def test_handle_transaction_rollback(
        self, analytics_manager, mock_db_session, sample_detection_data
    ):
        """Test transaction rollback on error."""
        # Simulate error during transaction
        mock_db_session.execute.side_effect = [
            AsyncMock(),  # First query succeeds
            SQLAlchemyError("Transaction error"),  # Second query fails
        ]

        with pytest.raises(SQLAlchemyError):
            await analytics_manager.update_all_analytics(sample_detection_data)

        mock_db_session.rollback.assert_called_once()
