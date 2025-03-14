"""Tests for the generate_detections module."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.analytics.generate_detections import generate_detections
from backend.models.models import RadioStation, StationStatus, Track, TrackDetection


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = Mock()
    session.query = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.flush = Mock()
    return session


@pytest.fixture
def mock_track():
    """Create a mock track."""
    track = Mock(spec=Track)
    track.id = 1
    track.title = "Test Track"
    track.play_count = 0
    track.total_play_time = timedelta(0)
    track.last_played = None
    return track


@pytest.fixture
def mock_station():
    """Create a mock radio station."""
    station = Mock(spec=RadioStation)
    station.id = 1
    station.name = "Test Station"
    station.total_play_time = timedelta(0)
    station.last_detection_time = None
    station.status = StationStatus.active
    return station


@patch("backend.analytics.generate_detections.create_engine")
@patch("backend.analytics.generate_detections.get_database_url")
@patch("backend.analytics.generate_detections.sessionmaker")
def test_generate_detections_success(
    mock_sessionmaker, mock_get_db_url, mock_create_engine, mock_session, mock_track, mock_station
):
    """Test successful generation of detections."""
    # Setup mocks
    mock_get_db_url.return_value = "mock://db/url"
    mock_create_engine.return_value = Mock()
    mock_sessionmaker.return_value = Mock(return_value=mock_session)

    # Setup query results
    mock_tracks_query = Mock()
    mock_tracks_query.all.return_value = [mock_track]
    mock_session.query.side_effect = lambda x: {
        Track: mock_tracks_query,
        RadioStation: Mock(filter=Mock(return_value=Mock(all=Mock(return_value=[mock_station])))),
    }[x]

    # Run the function
    generate_detections()

    # Verify the results
    assert mock_session.add.call_count >= 5  # At least 5 detections per track
    assert mock_session.commit.called
    assert mock_session.close.called
    assert mock_track.play_count > 0
    assert mock_track.total_play_time > timedelta(0)
    assert mock_track.last_played is not None
    assert mock_station.total_play_time > timedelta(0)
    assert mock_station.last_detection_time is not None


@patch("backend.analytics.generate_detections.create_engine")
@patch("backend.analytics.generate_detections.get_database_url")
@patch("backend.analytics.generate_detections.sessionmaker")
def test_generate_detections_no_tracks(
    mock_sessionmaker, mock_get_db_url, mock_create_engine, mock_session
):
    """Test handling when no tracks are found."""
    # Setup mocks
    mock_get_db_url.return_value = "mock://db/url"
    mock_create_engine.return_value = Mock()
    mock_sessionmaker.return_value = Mock(return_value=mock_session)

    # Setup empty tracks query
    mock_tracks_query = Mock()
    mock_tracks_query.all.return_value = []
    mock_session.query.return_value = mock_tracks_query

    # Run the function
    generate_detections()

    # Verify no detections were generated
    assert not mock_session.add.called
    assert not mock_session.commit.called
    assert mock_session.close.called


@patch("backend.analytics.generate_detections.create_engine")
@patch("backend.analytics.generate_detections.get_database_url")
@patch("backend.analytics.generate_detections.sessionmaker")
def test_generate_detections_no_stations(
    mock_sessionmaker, mock_get_db_url, mock_create_engine, mock_session, mock_track
):
    """Test handling when no stations are found."""
    # Setup mocks
    mock_get_db_url.return_value = "mock://db/url"
    mock_create_engine.return_value = Mock()
    mock_sessionmaker.return_value = Mock(return_value=mock_session)

    # Setup query results
    mock_tracks_query = Mock()
    mock_tracks_query.all.return_value = [mock_track]
    mock_stations_query = Mock()
    mock_stations_query.filter.return_value = Mock(all=Mock(return_value=[]))
    mock_session.query.side_effect = lambda x: {
        Track: mock_tracks_query,
        RadioStation: mock_stations_query,
    }[x]

    # Capture the station being added
    added_stations = []

    def mock_add(obj):
        if isinstance(obj, RadioStation):
            added_stations.append(obj)

    mock_session.add.side_effect = mock_add

    # Run the function
    generate_detections()

    # Verify default station was created with correct attributes
    assert len(added_stations) >= 1
    default_station = added_stations[0]
    assert default_station.name == "Radio Teranga FM"
    assert default_station.stream_url == "http://stream.teranga.sn/live"
    assert default_station.country == "Senegal"
    assert default_station.region == "Dakar"
    assert default_station.language == "Wolof"
    assert default_station.status == StationStatus.active
    assert default_station.is_active is True
    assert isinstance(default_station.last_checked, datetime)

    # Verify session operations
    assert mock_session.flush.called
    assert mock_session.commit.called
    assert mock_session.close.called


@patch("backend.analytics.generate_detections.create_engine")
@patch("backend.analytics.generate_detections.get_database_url")
def test_generate_detections_db_connection_error(mock_get_db_url, mock_create_engine):
    """Test handling of database connection errors."""
    # Setup mocks to raise an error
    mock_get_db_url.return_value = "mock://db/url"
    mock_create_engine.side_effect = SQLAlchemyError("Connection error")

    # Run the function and check for error
    with pytest.raises(SQLAlchemyError, match="Connection error"):
        generate_detections()


@patch("backend.analytics.generate_detections.create_engine")
@patch("backend.analytics.generate_detections.get_database_url")
@patch("backend.analytics.generate_detections.sessionmaker")
def test_generate_detections_session_error(
    mock_sessionmaker, mock_get_db_url, mock_create_engine, mock_session, mock_track, mock_station
):
    """Test handling of session errors."""
    # Setup mocks
    mock_get_db_url.return_value = "mock://db/url"
    mock_create_engine.return_value = Mock()
    mock_sessionmaker.return_value = Mock(return_value=mock_session)

    # Setup query results
    mock_tracks_query = Mock()
    mock_tracks_query.all.return_value = [mock_track]
    mock_session.query.side_effect = lambda x: {
        Track: mock_tracks_query,
        RadioStation: Mock(filter=Mock(return_value=Mock(all=Mock(return_value=[mock_station])))),
    }[x]

    # Make session.add raise an error
    mock_session.add.side_effect = SQLAlchemyError("Session error")

    # Run the function and check for error handling
    with pytest.raises(SQLAlchemyError, match="Session error"):
        generate_detections()

    # Verify error handling
    assert mock_session.rollback.called
    assert mock_session.close.called
