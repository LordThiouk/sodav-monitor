"""Tests for the analytics module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.analytics.stats_manager import StatsManager
from backend.models.models import (
    Track, Artist, TrackDetection, StationTrackStats,
    TrackStats, ArtistStats, RadioStation
)

@pytest.fixture
def mock_track():
    """Create a mock track for testing."""
    track = Mock(spec=Track)
    track.id = 1
    track.title = "Test Track"
    track.artist_id = 1
    track.artist = Mock(spec=Artist)
    track.artist.name = "Test Artist"
    return track

@pytest.fixture
def mock_detection(mock_track):
    """Create a mock detection for testing."""
    detection = Mock(spec=TrackDetection)
    detection.id = 1
    detection.track_id = mock_track.id
    detection.track = mock_track
    detection.station_id = 1
    detection.confidence = 0.9
    detection.play_duration = timedelta(seconds=180)
    detection.detected_at = datetime.now()
    return detection

@pytest.fixture
def mock_track_without_artist():
    """Create a mock track without artist for testing edge cases."""
    track = Mock(spec=Track)
    track.id = 2
    track.title = "Test Track No Artist"
    track.artist_id = None
    track.artist = None
    return track

@pytest.fixture
def mock_detection_without_artist(mock_track_without_artist):
    """Create a mock detection for a track without artist."""
    detection = Mock(spec=TrackDetection)
    detection.id = 2
    detection.track_id = mock_track_without_artist.id
    detection.track = mock_track_without_artist
    detection.station_id = 1
    detection.confidence = 0.85
    detection.play_duration = timedelta(seconds=240)
    detection.detected_at = datetime.now()
    return detection

@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    session = Mock(spec=Session)
    session.query = Mock(return_value=session)
    session.filter = Mock(return_value=session)
    session.filter_by = Mock(return_value=session)
    session.join = Mock(return_value=session)
    session.group_by = Mock(return_value=session)
    session.order_by = Mock(return_value=session)
    session.limit = Mock(return_value=session)
    session.between = Mock(return_value=session)
    session.first = Mock(return_value=None)
    session.all = Mock(return_value=[])
    session.scalar = Mock(return_value=0)
    return session

@pytest.fixture
def stats_manager(db_session):
    """Create a StatsManager instance for testing."""
    return StatsManager(db_session)

@pytest.mark.asyncio
async def test_update_detection_stats_new_track(stats_manager, db_session, mock_detection):
    """Test updating stats for a new track detection."""
    # Setup mocks for new stats objects
    track_stats = TrackStats(
        track_id=mock_detection.track_id,
        detection_count=0,
        total_play_time=timedelta(),
        average_confidence=0.0,
        last_detected=datetime.now()
    )

    artist_stats = ArtistStats(
        artist_id=mock_detection.track.artist_id,
        detection_count=0,
        total_play_time=timedelta()
    )

    station_track_stats = StationTrackStats(
        station_id=mock_detection.station_id,
        track_id=mock_detection.track_id,
        play_count=0,
        total_play_time=timedelta(),
        last_played=datetime.now(),
        average_confidence=0.0
    )

    db_session.query.return_value.filter_by.return_value.first.side_effect = [
        None,  # First call for TrackStats
        None,  # First call for ArtistStats
        None   # First call for StationTrackStats
    ]

    await stats_manager.update_detection_stats(mock_detection)

    assert db_session.add.call_count == 3
    assert db_session.commit.called

@pytest.mark.asyncio
async def test_update_detection_stats_track_without_artist(stats_manager, db_session, mock_detection_without_artist):
    """Test updating stats for a track without artist."""
    track_stats = TrackStats(
        track_id=mock_detection_without_artist.track_id,
        detection_count=0,
        total_play_time=timedelta(),
        average_confidence=0.0,
        last_detected=datetime.now()
    )

    station_track_stats = StationTrackStats(
        station_id=mock_detection_without_artist.station_id,
        track_id=mock_detection_without_artist.track_id,
        play_count=0,
        total_play_time=timedelta(),
        last_played=datetime.now(),
        average_confidence=0.0
    )

    db_session.query.return_value.filter_by.return_value.first.side_effect = [
        None,  # First call for TrackStats
        None   # First call for StationTrackStats
    ]

    await stats_manager.update_detection_stats(mock_detection_without_artist)

    assert db_session.add.call_count == 2  # Only track and station stats, no artist stats
    assert db_session.commit.called

@pytest.mark.asyncio
async def test_generate_daily_report_empty_data(stats_manager, db_session):
    """Test daily report generation with no data."""
    db_session.query.return_value.filter.return_value.scalar.side_effect = [
        0,  # total_detections
        None  # total_play_time
    ]

    db_session.query.return_value.join.return_value.filter.return_value.group_by.return_value \
        .order_by.return_value.limit.return_value.all.side_effect = [
            [],  # top_tracks
            [],  # top_artists
            []   # station_stats
        ]

    report = await stats_manager.generate_daily_report()

    assert report["total_detections"] == 0
    assert report["total_play_time"] == "0:00:00"
    assert len(report["top_tracks"]) == 0
    assert len(report["top_artists"]) == 0
    assert len(report["station_stats"]) == 0

@pytest.mark.asyncio
async def test_get_trend_analysis_custom_period(stats_manager, db_session):
    """Test trend analysis with custom time period."""
    mock_track = Mock(spec=Track)
    mock_track.title = "Test Track"
    mock_track.artist = Mock(spec=Artist)
    mock_track.artist.name = "Test Artist"

    mock_artist = Mock(spec=Artist)
    mock_artist.name = "Test Artist"

    db_session.query.return_value.join.return_value.filter.return_value.group_by.return_value \
        .order_by.return_value.limit.return_value.all.side_effect = [
            [(mock_track, 15, timedelta(hours=3))],  # track_trends
            [(mock_artist, 25, timedelta(hours=5))]  # artist_trends
        ]

    # Test with 30 days period
    trends = await stats_manager.get_trend_analysis(days=30)

    assert trends["period"]["days"] == 30
    assert len(trends["track_trends"]) == 1
    assert len(trends["artist_trends"]) == 1
    assert trends["track_trends"][0]["detections"] == 15
    assert trends["artist_trends"][0]["detections"] == 25

@pytest.mark.asyncio
async def test_get_trend_analysis_no_data(stats_manager, db_session):
    """Test trend analysis when no data is available."""
    db_session.query.return_value.join.return_value.filter.return_value.group_by.return_value \
        .order_by.return_value.limit.return_value.all.side_effect = [
            [],  # track_trends
            []   # artist_trends
        ]

    trends = await stats_manager.get_trend_analysis()

    assert len(trends["track_trends"]) == 0
    assert len(trends["artist_trends"]) == 0
    assert "period" in trends
    assert trends["period"]["days"] == 7  # Default period

@pytest.mark.asyncio
async def test_update_detection_stats_existing_track(stats_manager, db_session, mock_detection):
    """Test updating stats for an existing track detection."""
    # Setup mocks for existing stats
    track_stats = TrackStats(
        track_id=mock_detection.track_id,
        detection_count=1,
        total_play_time=timedelta(seconds=180),
        average_confidence=0.8,
        last_detected=datetime.now()
    )

    artist_stats = ArtistStats(
        artist_id=mock_detection.track.artist_id,
        detection_count=1,
        total_play_time=timedelta(seconds=180)
    )

    station_track_stats = StationTrackStats(
        station_id=mock_detection.station_id,
        track_id=mock_detection.track_id,
        play_count=1,
        total_play_time=timedelta(seconds=180),
        last_played=datetime.now(),
        average_confidence=0.8
    )

    # Configure session to return existing stats
    db_session.query.return_value.filter_by.return_value.first.side_effect = [
        track_stats,
        artist_stats,
        station_track_stats
    ]

    # Test the update
    await stats_manager.update_detection_stats(mock_detection)

    # Verify stats were updated
    assert track_stats.detection_count == 2
    assert isinstance(track_stats.total_play_time, timedelta)
    assert abs(track_stats.average_confidence - 0.85) < 0.0001  # Use approximate comparison
    assert abs(station_track_stats.average_confidence - 0.85) < 0.0001  # Use approximate comparison
    assert db_session.commit.called

@pytest.mark.asyncio
async def test_update_detection_stats_error(stats_manager, db_session, mock_detection):
    """Test error handling in update_detection_stats."""
    # Configure session to raise an error
    db_session.commit.side_effect = Exception("Database error")
    
    # Configure session to return a valid stats object first
    track_stats = TrackStats(
        track_id=mock_detection.track_id,
        detection_count=1,
        total_play_time=timedelta(seconds=180),
        average_confidence=0.8,
        last_detected=datetime.now()
    )

    artist_stats = ArtistStats(
        artist_id=mock_detection.track.artist_id,
        detection_count=1,
        total_play_time=timedelta(seconds=180)
    )

    station_track_stats = StationTrackStats(
        station_id=mock_detection.station_id,
        track_id=mock_detection.track_id,
        play_count=1,
        total_play_time=timedelta(seconds=180),
        last_played=datetime.now(),
        average_confidence=0.8
    )

    db_session.query.return_value.filter_by.return_value.first.side_effect = [
        track_stats,
        artist_stats,
        station_track_stats
    ]

    # Test error handling
    with pytest.raises(Exception) as exc_info:
        await stats_manager.update_detection_stats(mock_detection)
    
    assert "Database error" in str(exc_info.value)
    assert db_session.rollback.called

@pytest.mark.asyncio
async def test_generate_daily_report(stats_manager, db_session):
    """Test daily report generation."""
    # Mock data for the report
    mock_track = Mock(spec=Track)
    mock_track.title = "Test Track"
    mock_track.artist = Mock(spec=Artist)
    mock_track.artist.name = "Test Artist"

    mock_artist = Mock(spec=Artist)
    mock_artist.name = "Test Artist"

    mock_station = Mock(spec=RadioStation)
    mock_station.name = "Test Station"

    # Configure query results
    db_session.query.return_value.filter.return_value.scalar.side_effect = [
        10,  # total_detections
        timedelta(hours=2)  # total_play_time
    ]

    db_session.query.return_value.join.return_value.filter.return_value.group_by.return_value \
        .order_by.return_value.limit.return_value.all.side_effect = [
            [(mock_track, 5, timedelta(hours=1))],  # top_tracks
            [(mock_artist, 5, timedelta(hours=1))],  # top_artists
            [(mock_station, 5, timedelta(hours=1))]  # station_stats
        ]

    # Generate report
    report = await stats_manager.generate_daily_report()

    # Verify report structure and content
    assert isinstance(report, dict)
    assert "date" in report
    assert report["total_detections"] == 10
    assert isinstance(report["total_play_time"], str)
    assert len(report["top_tracks"]) == 1
    assert len(report["top_artists"]) == 1
    assert len(report["station_stats"]) == 1

@pytest.mark.asyncio
async def test_generate_daily_report_error(stats_manager, db_session):
    """Test error handling in daily report generation."""
    # Simulate database error
    db_session.query.side_effect = Exception("Database error")

    # Test error handling
    with pytest.raises(Exception) as exc_info:
        await stats_manager.generate_daily_report()
    
    assert "Database error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_trend_analysis(stats_manager, db_session):
    """Test trend analysis generation."""
    # Mock data for trends
    mock_track = Mock(spec=Track)
    mock_track.title = "Test Track"
    mock_track.artist = Mock(spec=Artist)
    mock_track.artist.name = "Test Artist"

    mock_artist = Mock(spec=Artist)
    mock_artist.name = "Test Artist"

    # Configure query results
    db_session.query.return_value.join.return_value.filter.return_value.group_by.return_value \
        .order_by.return_value.limit.return_value.all.side_effect = [
            [(mock_track, 5, timedelta(hours=1))],  # track_trends
            [(mock_artist, 5, timedelta(hours=1))]  # artist_trends
        ]

    # Generate trends
    trends = await stats_manager.get_trend_analysis(days=7)

    # Verify trends structure and content
    assert isinstance(trends, dict)
    assert "period" in trends
    assert trends["period"]["days"] == 7
    assert len(trends["track_trends"]) == 1
    assert len(trends["artist_trends"]) == 1

@pytest.mark.asyncio
async def test_get_trend_analysis_error(stats_manager, db_session):
    """Test error handling in trend analysis."""
    # Simulate database error
    db_session.query.side_effect = Exception("Database error")

    # Test error handling
    with pytest.raises(Exception) as exc_info:
        await stats_manager.get_trend_analysis()
    
    assert "Database error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_update_all_stats(stats_manager, db_session):
    """Test updating all statistics."""
    # Mock data for testing
    mock_detections = [
        Mock(
            track_id=1,
            confidence=0.9,
            play_duration=timedelta(seconds=180),
            detected_at=datetime.now()
        ),
        Mock(
            track_id=2,
            confidence=0.85,
            play_duration=timedelta(seconds=200),
            detected_at=datetime.now()
        )
    ]
    
    # Configure session mocks
    db_session.query.return_value.all.return_value = mock_detections

    # Test updating all stats
    with patch.object(stats_manager, 'update_detection_stats') as mock_update:
        for detection in mock_detections:
            await stats_manager.update_detection_stats(detection)
        
        assert mock_update.call_count == len(mock_detections)

@pytest.mark.asyncio
async def test_error_handling(stats_manager, db_session):
    """Test error handling in statistics calculation."""
    # Simulate database error
    db_session.query.side_effect = Exception("Database error")
    
    # Test error handling for daily report
    with pytest.raises(Exception) as exc_info:
        await stats_manager.generate_daily_report()
    assert "Database error" in str(exc_info.value)

    # Test error handling for trend analysis
    with pytest.raises(Exception) as exc_info:
        await stats_manager.get_trend_analysis()
    assert "Database error" in str(exc_info.value)

    # Test error handling for detection stats update
    mock_detection = Mock(spec=TrackDetection)
    mock_detection.track_id = 1
    mock_detection.station_id = 1
    mock_detection.confidence = 0.9
    mock_detection.play_duration = timedelta(seconds=180)
    mock_detection.detected_at = datetime.now()
    mock_detection.track = Mock(spec=Track)
    mock_detection.track.artist_id = 1

    with pytest.raises(Exception) as exc_info:
        await stats_manager.update_detection_stats(mock_detection)
    assert "Database error" in str(exc_info.value) 