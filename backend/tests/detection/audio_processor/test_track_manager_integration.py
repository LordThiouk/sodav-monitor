"""
Integration tests for the TrackManager module.

This module contains integration tests that verify the correct interaction
between TrackManager and its associated classes (TrackFinder, TrackCreator,
ExternalDetection, StatsRecorder).
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch

from backend.detection.audio_processor.track_manager.track_manager import TrackManager
from backend.detection.audio_processor.track_manager.track_finder import TrackFinder
from backend.detection.audio_processor.track_manager.track_creator import TrackCreator
from backend.detection.audio_processor.track_manager.external_detection import ExternalDetection
from backend.detection.audio_processor.track_manager.stats_recorder import StatsRecorder
from backend.models.track import Track
from backend.models.artist import Artist


@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    session = MagicMock()
    return session


@pytest.fixture
def mock_track():
    """Create a mock Track for testing."""
    mock_track = MagicMock(spec=Track)
    mock_track.id = 1
    mock_track.title = "Test Track"
    mock_track.artist = MagicMock(spec=Artist)
    mock_track.artist.name = "Test Artist"
    mock_track.album = "Test Album"
    mock_track.isrc = "ABCDE1234567"
    mock_track.label = "Test Label"
    mock_track.release_date = "2023-01-01"
    mock_track.duration = 180
    return mock_track


@pytest.mark.asyncio
async def test_get_or_create_track_integration(mock_db_session, mock_track):
    """
    Test the integration between TrackManager and TrackCreator for creating tracks.
    
    This test verifies that the TrackManager correctly delegates to TrackCreator
    to create or retrieve a track.
    """
    # Configure the mock session
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_track
    
    # Create the TrackManager with its dependencies
    track_creator = TrackCreator(mock_db_session)
    track_finder = TrackFinder(mock_db_session)
    external_detection = ExternalDetection()
    stats_recorder = StatsRecorder(mock_db_session)
    
    track_manager = TrackManager(
        db_session=mock_db_session,
        track_finder=track_finder,
        track_creator=track_creator,
        external_detection=external_detection,
        stats_recorder=stats_recorder
    )
    
    # Patch the TrackCreator methods
    with patch.object(TrackCreator, 'get_or_create_artist', return_value=1), \
         patch.object(TrackCreator, 'get_or_create_track', return_value=mock_track):
         
        # Call the method under test
        track = await track_manager.get_or_create_track(
            title="Test Track",
            artist_name="Test Artist",
            album="Test Album",
            isrc="ABCDE1234567",
            label="Test Label",
            release_date="2023-01-01",
            duration=180.0
        )
        
        # Verify the results
        assert track is not None
        assert track.id == 1
        assert track.title == "Test Track"
        assert track.artist.name == "Test Artist" 