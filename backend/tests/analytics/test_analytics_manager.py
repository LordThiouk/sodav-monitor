"""Tests for the AnalyticsManager class."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy.exc import SQLAlchemyError
import asyncio
import time

from backend.utils.analytics.analytics_manager import AnalyticsManager
from backend.models.models import (
    Track, TrackDetection, TrackStats, ArtistStats,
    StationTrackStats, RadioStation, StationStatus,
    AnalyticsData, DetectionHourly
)

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    
    # Configure execute to return a mock result
    mock_result = AsyncMock()
    mock_result.first.return_value = {
        'track_id': 1,
        'artist_id': 1,
        'artist': 'Test Artist',
        'title': 'Test Track',
        'detection_count': 10,
        'total_play_time': 3600,
        'artist_count': 5,
        'artist_play_time': 1800,
        'play_count': 3,
        'station_play_time': 900
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
        'station_id': 1,
        'track_id': 1,
        'confidence': 0.95,
        'play_duration': timedelta(seconds=180),
        'detected_at': datetime.now()
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
                station_id=sample_detection_data['station_id'],
                track_id=sample_detection_data['track_id'],
                confidence=sample_detection_data['confidence'],
                play_duration=sample_detection_data['play_duration'],
                current_time=datetime.now(),
                base_data={'artist_id': 1}
            )

        # Verify SQL execution
        assert mock_db_session.execute.call_count >= 3  # Track, artist, and station stats
        assert mock_db_session.begin.called  # Transaction was started
        assert mock_db_session.begin.return_value.__aenter__.called  # Transaction was entered
        assert mock_db_session.begin.return_value.__aexit__.called  # Transaction was exited
    
    async def test_update_analytics_data_efficient(
        self, analytics_manager, mock_db_session
    ):
        """Test efficient update of analytics data."""
        await analytics_manager._update_analytics_data_efficient(
            confidence=0.95,
            current_time=datetime.now()
        )
        
        # Verify analytics data update
        mock_db_session.execute.assert_called_once()
        sql_call = str(mock_db_session.execute.call_args[0][0])
        assert "track_detections" in sql_call.lower()  # Verify source table
        assert "insert into analytics_data" in sql_call.lower()  # Verify target table
        assert "detection_count" in sql_call.lower()  # Verify column
        assert "detection_rate" in sql_call.lower()  # Verify column
        assert "average_confidence" in sql_call.lower()  # Verify column
    
    async def test_update_temporal_aggregates_efficient(
        self, analytics_manager, mock_db_session
    ):
        """Test efficient update of temporal aggregates."""
        current_time = datetime.now()
        play_duration = timedelta(seconds=180)
        await analytics_manager._update_temporal_aggregates_efficient(
            station_id=1,
            track_id=1,
            artist_id=1,
            current_time=current_time,
            play_duration=play_duration
        )
        
        # Verify temporal aggregates update
        mock_db_session.execute.assert_called_once()
        sql_call = str(mock_db_session.execute.call_args[0][0])
        assert "detection_hourly" in sql_call.lower()
        assert "track_daily" in sql_call.lower()
        assert "artist_daily" in sql_call.lower()
    
    async def test_update_station_status_efficient(
        self, analytics_manager, mock_db_session
    ):
        """Test efficient update of station status."""
        await analytics_manager._update_station_status_efficient(
            station_id=1,
            current_time=datetime.now()
        )
        
        # Verify station status update
        mock_db_session.execute.assert_called_once()
        sql_call = str(mock_db_session.execute.call_args[0][0])
        assert "UPDATE radio_stations" in sql_call

@pytest.mark.asyncio
class TestAnalyticsPerformance:
    """Test analytics performance."""
    
    async def test_batch_update_performance(
        self, analytics_manager, mock_db_session, benchmark
    ):
        """Test performance of batch analytics updates."""
        # Create multiple detection records
        detections = [
            {
                'station_id': i % 3 + 1,
                'track_id': i % 5 + 1,
                'confidence': 0.9 + (i % 10) / 100,
                'play_duration': timedelta(seconds=180),
                'detected_at': datetime.now() - timedelta(minutes=i)
            }
            for i in range(100)
        ]

        # Measure the time taken for a single update
        start_time = time.perf_counter()
        await analytics_manager.update_all_analytics(detections[0])
        end_time = time.perf_counter()
        
        # Use benchmark to record the timing
        benchmark.extra_info.update({'single_update_time': end_time - start_time})
        assert end_time - start_time < 0.1  # Single update should take less than 100ms
    
    async def test_memory_usage(
        self, analytics_manager, mock_db_session
    ):
        """Test memory usage during analytics updates."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial = process.memory_info().rss

        # Perform analytics update
        detection = {
            'station_id': 1,
            'track_id': 1,
            'confidence': 0.95,
            'play_duration': timedelta(seconds=180),
            'detected_at': datetime.now()
        }
        await analytics_manager.update_all_analytics(detection)

        final = process.memory_info().rss
        memory_increase = (final - initial) / 1024 / 1024  # MB
        assert memory_increase < 50  # Should use less than 50MB additional memory

@pytest.mark.asyncio
class TestAnalyticsErrorHandling:
    """Test analytics error handling."""
    
    async def test_handle_missing_data(
        self, analytics_manager, mock_db_session
    ):
        """Test handling of missing data."""
        incomplete_data = {
            'station_id': 1,
            # Missing track_id
            'confidence': 0.95
        }
        
        with pytest.raises(KeyError):
            await analytics_manager.update_all_analytics(incomplete_data)
    
    async def test_handle_invalid_data(
        self, analytics_manager, mock_db_session
    ):
        """Test handling of invalid data."""
        invalid_data = {
            'station_id': 'invalid',  # Should be integer
            'track_id': None,
            'confidence': 2.0,  # Should be between 0 and 1
            'play_duration': timedelta(seconds=180),
            'detected_at': datetime.now()
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
            SQLAlchemyError("Transaction error")  # Second query fails
        ]
        
        with pytest.raises(SQLAlchemyError):
            await analytics_manager.update_all_analytics(sample_detection_data)
        
        mock_db_session.rollback.assert_called_once()

@pytest.mark.asyncio
class TestDataAggregation:
    """Test data aggregation functionality."""
    
    async def test_hourly_aggregation(self, analytics_manager, mock_db_session):
        """Test hourly data aggregation."""
        current_time = datetime.now()
        hour_start = current_time.replace(minute=0, second=0, microsecond=0)
        
        # Create test data
        detections = [
            {
                'station_id': 1,
                'track_id': 1,
                'confidence': 0.95,
                'play_duration': timedelta(seconds=180),
                'detected_at': hour_start + timedelta(minutes=i*10)
            }
            for i in range(6)  # Create detections over 1 hour
        ]
        
        # Process detections
        for detection in detections:
            await analytics_manager.update_all_analytics(detection)
        
        # Verify hourly aggregation
        mock_db_session.execute.assert_called()
        sql_calls = [str(call[0][0]).lower() for call in mock_db_session.execute.call_args_list]
        assert any('detection_hourly' in call for call in sql_calls)
        assert any('sum(play_duration)' in call for call in sql_calls)
    
    async def test_daily_aggregation(self, analytics_manager, mock_db_session):
        """Test daily data aggregation."""
        current_time = datetime.now()
        day_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Create test data across different hours
        detections = [
            {
                'station_id': 1,
                'track_id': 1,
                'confidence': 0.95,
                'play_duration': timedelta(seconds=180),
                'detected_at': day_start + timedelta(hours=i*2)
            }
            for i in range(12)  # Create detections over 24 hours
        ]
        
        # Process detections
        for detection in detections:
            await analytics_manager.update_all_analytics(detection)
        
        # Verify daily aggregation
        mock_db_session.execute.assert_called()
        sql_calls = [str(call[0][0]).lower() for call in mock_db_session.execute.call_args_list]
        assert any('track_daily' in call for call in sql_calls)
        assert any('artist_daily' in call for call in sql_calls)

@pytest.mark.asyncio
class TestReportGeneration:
    """Test report generation functionality."""
    
    async def test_generate_station_report(self, analytics_manager, mock_db_session):
        """Test generation of station-specific report."""
        # Configure mock to return sample data
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [
            {
                'track_id': 1,
                'title': 'Test Track',
                'artist': 'Test Artist',
                'play_count': 10,
                'total_duration': 3600,
                'average_confidence': 0.95
            }
        ]
        mock_db_session.execute.return_value = mock_result
        
        report = await analytics_manager.generate_station_report(
            station_id=1,
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now()
        )
        
        assert report is not None
        assert len(report) > 0
        assert 'track_id' in report[0]
        assert 'play_count' in report[0]
    
    async def test_generate_artist_report(self, analytics_manager, mock_db_session):
        """Test generation of artist-specific report."""
        # Configure mock to return sample data
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [
            {
                'artist_id': 1,
                'artist': 'Test Artist',
                'total_tracks': 5,
                'total_plays': 50,
                'total_duration': 18000,
                'average_confidence': 0.92
            }
        ]
        mock_db_session.execute.return_value = mock_result
        
        report = await analytics_manager.generate_artist_report(
            artist_id=1,
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now()
        )
        
        assert report is not None
        assert len(report) > 0
        assert 'artist_id' in report[0]
        assert 'total_plays' in report[0]

@pytest.mark.asyncio
class TestConcurrentProcessing:
    """Test concurrent analytics processing."""
    
    async def test_concurrent_updates(self, analytics_manager, mock_db_session):
        """Test handling of concurrent analytics updates."""
        # Create multiple concurrent detection updates
        detections = [
            {
                'station_id': i % 3 + 1,
                'track_id': i % 5 + 1,
                'confidence': 0.9 + (i % 10) / 100,
                'play_duration': timedelta(seconds=180),
                'detected_at': datetime.now()
            }
            for i in range(10)
        ]
        
        # Process detections concurrently
        tasks = [
            analytics_manager.update_all_analytics(detection)
            for detection in detections
        ]
        await asyncio.gather(*tasks)
        
        # Verify transaction handling
        assert mock_db_session.begin.call_count >= len(detections)
        assert mock_db_session.commit.call_count >= len(detections)
    
    async def test_concurrent_report_generation(self, analytics_manager, mock_db_session):
        """Test concurrent report generation."""
        # Configure mock to return different data for different queries
        async def mock_execute(*args, **kwargs):
            sql = str(args[0]).lower()
            mock_result = AsyncMock()
            
            if 'station_track_stats' in sql:
                mock_result.fetchall.return_value = [
                    {'station_id': 1, 'track_count': 100, 'total_duration': 36000}
                ]
            elif 'artist_stats' in sql:
                mock_result.fetchall.return_value = [
                    {'artist_id': 1, 'track_count': 50, 'total_duration': 18000}
                ]
            else:
                mock_result.fetchall.return_value = []
            
            return mock_result
        
        mock_db_session.execute = AsyncMock(side_effect=mock_execute)
        
        # Generate multiple reports concurrently
        tasks = [
            analytics_manager.generate_station_report(
                station_id=i,
                start_date=datetime.now() - timedelta(days=1),
                end_date=datetime.now()
            )
            for i in range(1, 4)
        ]
        results = await asyncio.gather(*tasks)
        
        assert all(result is not None for result in results)
        assert mock_db_session.execute.call_count >= len(tasks) 