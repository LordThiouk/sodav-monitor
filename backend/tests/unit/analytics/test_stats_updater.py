"""Tests for the StatsUpdater class."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from backend.models.models import (
    Artist,
    ArtistStats,
    RadioStation,
    StationTrackStats,
    Track,
    TrackDetection,
    TrackStats,
)
from backend.utils.analytics.stats_updater import StatsUpdater


class TestStatsUpdater(unittest.TestCase):
    """Test cases for the StatsUpdater class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the database session
        self.db_session = MagicMock(spec=Session)

        # Create a StatsUpdater instance with the mock session
        self.stats_updater = StatsUpdater(self.db_session)

        # Create mock objects for testing
        self.artist = MagicMock(spec=Artist)
        self.artist.id = 1
        self.artist.name = "Test Artist"

        self.track = MagicMock(spec=Track)
        self.track.id = 1
        self.track.title = "Test Track"
        self.track.artist_id = self.artist.id
        self.track.artist = self.artist
        self.track.isrc = "ABCDE1234567"

        self.station = MagicMock(spec=RadioStation)
        self.station.id = 1
        self.station.name = "Test Station"

        # Mock the query results
        self.db_session.query.return_value.filter.return_value.first.return_value = None

        # Mock the execute method for SQL queries
        self.db_session.execute.return_value.fetchone.return_value = MagicMock(
            track_count=1, artist_play_count=1
        )

    def test_validate_duration(self):
        """Test the _validate_duration method."""
        # Test with a valid duration
        duration = timedelta(seconds=120)
        result = self.stats_updater._validate_duration(duration)
        self.assertEqual(result, duration)

        # Test with a negative duration
        duration = timedelta(seconds=-10)
        result = self.stats_updater._validate_duration(duration)
        self.assertEqual(
            result, timedelta(seconds=15)
        )  # La méthode retourne 15 secondes par défaut pour les durées négatives

        # Test with a very large duration
        duration = timedelta(days=2)
        result = self.stats_updater._validate_duration(duration)
        self.assertEqual(result, timedelta(seconds=3600))  # Should be capped at 1 hour

    def test_update_all_stats(self):
        """Test the update_all_stats method."""
        # Create a detection result
        detection_result = {
            "track_id": self.track.id,
            "confidence": 0.8,
            "detection_method": "audd",
        }

        # Set up the play duration
        play_duration = timedelta(seconds=120)

        # Call the method
        self.stats_updater.update_all_stats(
            detection_result=detection_result,
            station_id=self.station.id,
            track=self.track,
            play_duration=play_duration,
        )

        # Verify that the appropriate methods were called
        self.db_session.execute.assert_called()
        self.db_session.commit.assert_called_once()

    def test_update_detection_stats_efficient(self):
        """Test the _update_detection_stats_efficient method."""
        # Set up the parameters
        station_id = self.station.id
        track_id = self.track.id
        artist_id = self.artist.id
        confidence = 0.8
        play_duration = timedelta(seconds=120)
        current_time = datetime.now()

        # Call the method
        self.stats_updater._update_detection_stats_efficient(
            station_id=station_id,
            track_id=track_id,
            artist_id=artist_id,
            confidence=confidence,
            play_duration=play_duration,
            current_time=current_time,
        )

        # Verify that the SQL execution was called
        self.db_session.execute.assert_called_once()

    @patch("backend.utils.analytics.stats_updater.StatsUpdater._update_detection_stats_efficient")
    @patch(
        "backend.utils.analytics.stats_updater.StatsUpdater._update_temporal_aggregates_efficient"
    )
    @patch("backend.utils.analytics.stats_updater.StatsUpdater._update_analytics_data_efficient")
    @patch("backend.utils.analytics.stats_updater.StatsUpdater._update_station_status_efficient")
    def test_update_all_stats_calls_all_methods(
        self,
        mock_update_station,
        mock_update_analytics,
        mock_update_temporal,
        mock_update_detection,
    ):
        """Test that update_all_stats calls all the required methods."""
        # Create a detection result
        detection_result = {
            "track_id": self.track.id,
            "confidence": 0.8,
            "detection_method": "audd",
        }

        # Set up the play duration
        play_duration = timedelta(seconds=120)

        # Call the method
        self.stats_updater.update_all_stats(
            detection_result=detection_result,
            station_id=self.station.id,
            track=self.track,
            play_duration=play_duration,
        )

        # Verify that all methods were called
        mock_update_detection.assert_called_once()
        mock_update_temporal.assert_called_once()
        mock_update_analytics.assert_called_once()
        mock_update_station.assert_called_once()

        # Verify that commit was called
        self.db_session.commit.assert_called_once()

    def test_integration_with_track_manager(self):
        """Test the integration with TrackManager._record_play_time."""
        # This test requires a more complex setup with actual database objects
        # and would be better implemented as an integration test.
        # For now, we'll just verify that the StatsUpdater can be initialized
        # and that its methods can be called without errors.
        self.assertIsNotNone(self.stats_updater)

        # Verify that we can call the methods without errors
        try:
            # Create a detection result
            detection_result = {
                "track_id": self.track.id,
                "confidence": 0.8,
                "detection_method": "audd",
            }

            # Set up the play duration
            play_duration = timedelta(seconds=120)

            # Call the method
            self.stats_updater.update_all_stats(
                detection_result=detection_result,
                station_id=self.station.id,
                track=self.track,
                play_duration=play_duration,
            )

            # If we get here without errors, the test passes
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"StatsUpdater methods raised an exception: {e}")


if __name__ == "__main__":
    unittest.main()
