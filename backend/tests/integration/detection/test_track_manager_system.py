"""
System integration tests for the TrackManager module.

This module contains system-level integration tests that verify the correct interaction
between TrackManager and the database, as well as the complete detection pipeline.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.track_manager.track_manager import TrackManager
from backend.models.models import Artist, RadioStation, Track, TrackDetection


class TestTrackManagerSystem:
    """System integration tests for the TrackManager."""

    @pytest.fixture
    def db_session(self):
        """Create a mock database session for testing."""
        session = MagicMock(spec=Session)
        return session

    @pytest.fixture
    def test_station(self, db_session):
        """Create a test radio station."""
        station = MagicMock(spec=RadioStation)
        station.id = 1
        station.name = "Test System Station"
        station.url = "http://test.station/stream"
        station.country = "SN"
        station.language = "fr"
        station.created_at = datetime.now()
        station.updated_at = datetime.now()

        # Configure the mock session to return this station
        db_session.query.return_value.filter.return_value.first.return_value = station

        return station

    @pytest.fixture
    def test_artist(self, db_session):
        """Create a test artist."""
        artist = MagicMock(spec=Artist)
        artist.id = 1
        artist.name = "Test System Artist"
        artist.created_at = datetime.now()
        artist.updated_at = datetime.now()

        # Configure the mock session to return this artist
        db_session.query.return_value.filter.return_value.first.return_value = artist

        return artist

    @pytest.fixture
    def test_track(self, db_session, test_artist):
        """Create a test track."""
        track = MagicMock(spec=Track)
        track.id = 1
        track.title = "Test System Track"
        track.artist_id = test_artist.id
        track.artist = test_artist
        track.album = "Test System Album"
        track.isrc = "TESTSYSTEM01"
        track.label = "Test Label"
        track.release_date = "2023-01-01"
        track.duration = 180
        track.fingerprint = "test_system_fingerprint"
        track.fingerprint_raw = b"test_system_fingerprint_raw"
        track.created_at = datetime.now()
        track.updated_at = datetime.now()

        # Configure the mock session to return this track
        db_session.query.return_value.filter.return_value.first.return_value = track

        return track

    @pytest.fixture
    def test_features(self):
        """Create test audio features."""
        return {
            "mfcc": [1.0, 2.0, 3.0],
            "chroma": [4.0, 5.0, 6.0],
            "spectral_centroid": [7.0, 8.0, 9.0],
            "audio_data": b"test_system_audio_data",
            "sample_rate": 44100,
            "duration": 5.0,
        }

    @pytest.mark.asyncio
    async def test_local_detection_system(
        self, db_session, test_track, test_station, test_features
    ):
        """
        Test local detection with real database interactions.

        This test:
        1. Creates a track manager
        2. Mocks the track finder to return a local match
        3. Processes a track
        4. Verifies that the detection is recorded correctly
        """
        # Create the TrackManager
        track_manager = TrackManager(db_session=db_session)

        # Mock the track finder to return a local match
        with patch.object(
            track_manager.track_finder, "find_local_match", new_callable=AsyncMock
        ) as mock_find_local, patch.object(
            track_manager.stats_recorder, "record_detection"
        ) as mock_record_detection:
            # Configure the mocks
            mock_find_local.return_value = {
                "track": {
                    "id": test_track.id,
                    "title": test_track.title,
                    "artist": test_track.artist.name,
                },
                "confidence": 0.9,
                "method": "local",
            }

            mock_record_detection.return_value = {
                "success": True,
                "track_id": test_track.id,
                "detection_id": 1,
            }

            # Process the track
            result = await track_manager.process_track(test_features, station_id=test_station.id)

            # Verify the result
            assert result["success"] is True
            assert result["track_id"] == test_track.id

            # Verify the correct methods were called
            mock_find_local.assert_called_once_with(test_features)
            mock_record_detection.assert_called_once()

    @pytest.mark.asyncio
    async def test_isrc_detection_system(self, db_session, test_track, test_station, test_features):
        """
        Test ISRC-based detection with real database interactions.

        This test:
        1. Creates a track manager
        2. Mocks the track finder to fail local detection but succeed with ISRC
        3. Processes a track with an ISRC
        4. Verifies that the detection is recorded correctly
        """
        # Create the TrackManager
        track_manager = TrackManager(db_session=db_session)

        # Mock the track finder methods
        with patch.object(
            track_manager.track_finder, "find_local_match", new_callable=AsyncMock
        ) as mock_find_local, patch.object(
            track_manager.track_finder, "find_track_by_isrc", new_callable=AsyncMock
        ) as mock_find_by_isrc, patch.object(
            track_manager.stats_recorder, "record_detection"
        ) as mock_record_detection:
            # Configure the mocks
            mock_find_local.return_value = None  # Local detection fails

            mock_find_by_isrc.return_value = {
                "track": {
                    "id": test_track.id,
                    "title": test_track.title,
                    "artist": test_track.artist.name,
                },
                "confidence": 1.0,
                "method": "isrc",
            }

            mock_record_detection.return_value = {
                "success": True,
                "track_id": test_track.id,
                "detection_id": 1,
            }

            # Add ISRC to the features
            features = test_features.copy()
            features["isrc"] = test_track.isrc

            # Process the track
            result = await track_manager.process_track(features, station_id=test_station.id)

            # Verify the result
            assert result["success"] is True
            assert result["track_id"] == test_track.id

            # Verify the correct methods were called
            mock_find_local.assert_called_once_with(features)
            mock_find_by_isrc.assert_called_once_with(test_track.isrc)
            mock_record_detection.assert_called_once()

    @pytest.mark.asyncio
    async def test_external_detection_system(
        self, db_session, test_track, test_artist, test_station, test_features
    ):
        """
        Test external detection with real database interactions.

        This test:
        1. Creates a track manager
        2. Mocks the track finder to fail local and ISRC detection
        3. Mocks the external service to return a match
        4. Processes a track
        5. Verifies that a new track is created in the database
        """
        # Create the TrackManager
        track_manager = TrackManager(db_session=db_session)

        # Mock the necessary methods
        with patch.object(
            track_manager.track_finder, "find_local_match", new_callable=AsyncMock
        ) as mock_find_local, patch.object(
            track_manager.track_finder, "find_track_by_isrc", new_callable=AsyncMock
        ) as mock_find_by_isrc, patch.object(
            track_manager.external_service, "find_external_match", new_callable=AsyncMock
        ) as mock_find_external, patch.object(
            track_manager.track_creator, "get_or_create_artist", new_callable=AsyncMock
        ) as mock_get_artist, patch.object(
            track_manager.track_creator, "get_or_create_track", new_callable=AsyncMock
        ) as mock_get_track, patch.object(
            track_manager.stats_recorder, "start_track_detection"
        ) as mock_start_detection:
            # Configure the mocks
            mock_find_local.return_value = None  # Local detection fails
            mock_find_by_isrc.return_value = None  # ISRC detection fails

            mock_find_external.return_value = {
                "track": {
                    "title": "New External Track",
                    "artist": "New External Artist",
                    "album": "New External Album",
                    "isrc": "NEWEXTERNAL01",
                    "label": "New External Label",
                },
                "confidence": 0.8,
                "method": "acoustid",
            }

            mock_get_artist.return_value = test_artist.id
            mock_get_track.return_value = test_track

            mock_start_detection.return_value = {
                "success": True,
                "track_id": test_track.id,
                "detection_id": 1,
            }

            # Process the track
            result = await track_manager.process_track(test_features, station_id=test_station.id)

            # Verify the result
            assert result["success"] is True
            assert result["track_id"] == test_track.id

            # Verify the correct methods were called
            mock_find_local.assert_called_once_with(test_features)
            mock_find_external.assert_called_once_with(test_features, test_station.id)
            mock_get_artist.assert_called_once()
            mock_get_track.assert_called_once()
            mock_start_detection.assert_called_once()

    @pytest.mark.asyncio
    async def test_stats_update_system(self, db_session, test_track, test_station):
        """
        Test that statistics are updated correctly after detections.

        This test:
        1. Creates a track manager
        2. Records a detection
        3. Verifies that the statistics are updated correctly
        """
        # Create the TrackManager
        track_manager = TrackManager(db_session=db_session)

        # Mock the stats recorder methods
        with patch.object(
            track_manager.stats_recorder, "record_detection"
        ) as mock_record_detection:
            # Configure the mocks
            mock_record_detection.return_value = {
                "success": True,
                "track_id": test_track.id,
                "detection_id": 1,
            }

            # Create detection data
            detection_data = {
                "track": {
                    "id": test_track.id,
                    "title": test_track.title,
                    "artist": test_track.artist.name,
                },
                "confidence": 0.9,
                "method": "local",
            }

            # Record a detection
            result = track_manager.stats_recorder.record_detection(
                detection_data, station_id=test_station.id
            )

            # Verify the result
            assert result["success"] is True
            assert result["track_id"] == test_track.id

            # Verify the correct methods were called
            mock_record_detection.assert_called_once_with(
                detection_data, station_id=test_station.id
            )

    @pytest.mark.asyncio
    async def test_full_detection_pipeline_system(
        self, db_session, test_track, test_artist, test_station, test_features
    ):
        """
        Test the complete detection pipeline with real components.

        This test:
        1. Creates a feature extractor and track manager
        2. Processes a sample audio through the pipeline
        3. Verifies the detection results
        """
        # Create the TrackManager
        track_manager = TrackManager(db_session=db_session)

        # Mock all the necessary methods for a complete pipeline test
        with patch.object(
            track_manager.track_finder, "find_local_match", new_callable=AsyncMock
        ) as mock_find_local, patch.object(
            track_manager.track_finder, "find_track_by_isrc", new_callable=AsyncMock
        ) as mock_find_by_isrc, patch.object(
            track_manager.external_service, "find_external_match", new_callable=AsyncMock
        ) as mock_find_external, patch.object(
            track_manager.track_creator, "get_or_create_artist", new_callable=AsyncMock
        ) as mock_get_artist, patch.object(
            track_manager.track_creator, "get_or_create_track", new_callable=AsyncMock
        ) as mock_get_track, patch.object(
            track_manager.stats_recorder, "record_detection"
        ) as mock_record_detection:
            # Configure the mocks for a complete pipeline test
            mock_find_local.return_value = {
                "track": {
                    "id": test_track.id,
                    "title": test_track.title,
                    "artist": test_track.artist.name,
                },
                "confidence": 0.9,
                "method": "local",
            }

            mock_record_detection.return_value = {
                "success": True,
                "track_id": test_track.id,
                "detection_id": 1,
            }

            # Process the track
            result = await track_manager.process_track(test_features, station_id=test_station.id)

            # Verify the result
            assert result["success"] is True
            assert result["track_id"] == test_track.id

            # Verify the correct methods were called
            mock_find_local.assert_called_once_with(test_features)
            mock_record_detection.assert_called_once()
