"""
Integration tests for the analytics pipeline.

These tests verify that detection data is properly processed and statistics are updated.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytest
from sqlalchemy.orm import Session

from backend.analytics.init_statistics import StatisticsInitializer
from backend.analytics.stats_manager import StatsManager
from backend.models.models import (
    AnalyticsData,
    Artist,
    ArtistStats,
    RadioStation,
    StationStats,
    StationTrackStats,
    Track,
    TrackDetection,
    TrackStats,
)


class TestAnalyticsPipeline:
    """Integration tests for the analytics pipeline."""

    @pytest.fixture
    def test_station(self, db_session: Session) -> RadioStation:
        """Create a test radio station."""
        # Create a unique station name for each test run
        unique_station_name = f"Analytics Test Station {uuid.uuid4()}"

        station = RadioStation(
            name=unique_station_name,
            stream_url=f"http://example.com/analytics_test_stream_{uuid.uuid4()}",
            country="FR",
            language="fr",
            is_active=True,
            status="active",
        )
        db_session.add(station)
        db_session.commit()
        db_session.refresh(station)
        return station

    @pytest.fixture
    def test_artist(self, db_session: Session) -> Artist:
        """Create a test artist."""
        # Create a unique artist name for each test run
        unique_artist_name = f"Analytics Test Artist {uuid.uuid4()}"

        artist = Artist(name=unique_artist_name, country="FR", label="Analytics Test Label")
        db_session.add(artist)
        db_session.commit()
        db_session.refresh(artist)
        return artist

    @pytest.fixture
    def test_track(self, db_session: Session, test_artist: Artist) -> Track:
        """Create a test track."""
        # Create a unique track title for each test run
        unique_track_title = f"Analytics Test Track {uuid.uuid4()}"
        unique_fingerprint = f"analytics_test_fingerprint_{uuid.uuid4()}"

        track = Track(
            title=unique_track_title,
            artist_id=test_artist.id,
            fingerprint=unique_fingerprint,
            fingerprint_raw=b"analytics_test_fingerprint_raw",
        )
        db_session.add(track)
        db_session.commit()
        db_session.refresh(track)
        return track

    @pytest.fixture
    def test_detection(
        self, db_session: Session, test_track: Track, test_station: RadioStation
    ) -> TrackDetection:
        """Create a test detection."""
        detection = TrackDetection(
            track_id=test_track.id,
            station_id=test_station.id,
            confidence=0.9,
            detected_at=datetime.utcnow(),
            play_duration=timedelta(seconds=180),  # 3 minutes
            fingerprint=test_track.fingerprint,
            audio_hash="analytics_test_audio_hash",
        )
        db_session.add(detection)
        db_session.commit()
        db_session.refresh(detection)
        return detection

    def test_track_stats_update(
        self, db_session: Session, test_track: Track, test_detection: TrackDetection
    ):
        """
        Test that track statistics are updated after a detection:
        1. Create a detection
        2. Update track statistics
        3. Verify that track statistics are updated correctly
        """
        # Create stats manager
        stats_manager = StatsManager(db_session)

        # Update track statistics
        stats_manager.update_track_stats(test_track.id)

        # Verify track statistics
        track_stats = (
            db_session.query(TrackStats).filter(TrackStats.track_id == test_track.id).first()
        )

        assert track_stats is not None, "Track stats not created"
        assert track_stats.total_plays == 1, "Total plays not updated"
        assert track_stats.total_play_time == timedelta(seconds=180), "Total play time not updated"
        assert (
            track_stats.last_detected == test_detection.detected_at
        ), "Last detected time not updated"

    def test_artist_stats_update(
        self, db_session: Session, test_artist: Artist, test_detection: TrackDetection
    ):
        """
        Test that artist statistics are updated after a detection:
        1. Create a detection
        2. Update artist statistics
        3. Verify that artist statistics are updated correctly
        """
        # Create stats manager
        stats_manager = StatsManager(db_session)

        # Update artist statistics
        stats_manager.update_artist_stats(test_artist.id)

        # Verify artist statistics
        artist_stats = (
            db_session.query(ArtistStats).filter(ArtistStats.artist_id == test_artist.id).first()
        )

        assert artist_stats is not None, "Artist stats not created"
        assert artist_stats.total_plays == 1, "Total plays not updated"
        assert artist_stats.total_play_time == timedelta(seconds=180), "Total play time not updated"
        assert (
            artist_stats.last_detected == test_detection.detected_at
        ), "Last detected time not updated"

    def test_station_stats_update(
        self, db_session: Session, test_station: RadioStation, test_detection: TrackDetection
    ):
        """
        Test that station statistics are updated after a detection:
        1. Create a detection
        2. Update station statistics
        3. Verify that station statistics are updated correctly
        """
        # Create stats manager
        stats_manager = StatsManager(db_session)

        # Update station statistics
        stats_manager.update_station_stats(test_station.id)

        # Verify station statistics
        station_stats = (
            db_session.query(StationStats)
            .filter(StationStats.station_id == test_station.id)
            .first()
        )

        assert station_stats is not None, "Station stats not created"
        assert station_stats.detection_count == 1, "Detection count not updated"
        assert (
            station_stats.last_detected == test_detection.detected_at
        ), "Last detected time not updated"

    def test_station_track_stats_update(
        self,
        db_session: Session,
        test_station: RadioStation,
        test_track: Track,
        test_detection: TrackDetection,
    ):
        """
        Test that station-track statistics are updated after a detection:
        1. Create a detection
        2. Update station-track statistics
        3. Verify that station-track statistics are updated correctly
        """
        # Create stats manager
        stats_manager = StatsManager(db_session)

        # Update station-track statistics
        stats_manager.update_station_track_stats(test_station.id, test_track.id)

        # Verify station-track statistics
        station_track_stats = (
            db_session.query(StationTrackStats)
            .filter(
                StationTrackStats.station_id == test_station.id,
                StationTrackStats.track_id == test_track.id,
            )
            .first()
        )

        assert station_track_stats is not None, "Station-track stats not created"
        assert station_track_stats.play_count == 1, "Play count not updated"
        assert station_track_stats.total_play_time == timedelta(
            seconds=180
        ), "Total play time not updated"

        # Compare only the timestamp parts, ignoring timezone info
        assert station_track_stats.last_played.replace(
            tzinfo=None
        ) == test_detection.detected_at.replace(tzinfo=None), "Last played time not updated"

    def test_multiple_detections_stats(
        self,
        db_session: Session,
        test_track: Track,
        test_station: RadioStation,
        test_detection: TrackDetection,
    ):
        """
        Test that statistics are updated correctly after multiple detections:
        1. Create multiple detections
        2. Update all statistics
        3. Verify that statistics are updated correctly
        """
        # Create additional detections
        for i in range(2):
            detection = TrackDetection(
                track_id=test_track.id,
                station_id=test_station.id,
                confidence=0.85 + i * 0.05,
                detected_at=datetime.utcnow() + timedelta(minutes=i + 1),
                play_duration=timedelta(seconds=120),  # 2 minutes
                fingerprint=test_track.fingerprint,
                audio_hash=f"analytics_test_audio_hash_{i}",
            )
            db_session.add(detection)

        db_session.commit()

        # Create stats manager
        stats_manager = StatsManager(db_session)

        # Update all statistics
        stats_manager.update_all_stats()

        # Verify track statistics
        track_stats = (
            db_session.query(TrackStats).filter(TrackStats.track_id == test_track.id).first()
        )
        assert track_stats.total_plays == 3, "Track detection count not updated correctly"
        assert track_stats.total_play_time == timedelta(
            seconds=180 + 120 * 2
        ), "Track total play time not updated correctly"

        # Verify artist statistics
        artist_stats = (
            db_session.query(ArtistStats)
            .filter(ArtistStats.artist_id == test_track.artist_id)
            .first()
        )
        assert artist_stats.total_plays == 3, "Artist detection count not updated correctly"
        assert artist_stats.total_play_time == timedelta(
            seconds=180 + 120 * 2
        ), "Artist total play time not updated correctly"

        # Verify station statistics
        station_stats = (
            db_session.query(StationStats)
            .filter(StationStats.station_id == test_station.id)
            .first()
        )
        assert station_stats.detection_count == 3, "Station detection count not updated correctly"

        # Verify station-track statistics
        station_track_stats = (
            db_session.query(StationTrackStats)
            .filter(
                StationTrackStats.station_id == test_station.id,
                StationTrackStats.track_id == test_track.id,
            )
            .first()
        )
        assert station_track_stats.play_count == 3, "Station-track play count not updated correctly"
        assert station_track_stats.total_play_time == timedelta(
            seconds=180 + 120 * 2
        ), "Station-track total play time not updated correctly"

    def test_analytics_data_generation(
        self,
        db_session: Session,
        test_track: Track,
        test_station: RadioStation,
        test_detection: TrackDetection,
    ):
        """
        Test that analytics data is generated correctly:
        1. Create detections
        2. Generate analytics data
        3. Verify that analytics data is generated correctly
        """
        # Create stats manager and statistics initializer
        stats_manager = StatsManager(db_session)
        stats_initializer = StatisticsInitializer(db_session)

        # Update all statistics
        stats_manager.update_all_stats()

        # Generate daily analytics data
        stats_initializer._initialize_analytics_data()

        # Verify analytics data
        analytics_data = (
            db_session.query(AnalyticsData).order_by(AnalyticsData.timestamp.desc()).first()
        )

        assert analytics_data is not None, "Analytics data not generated"
        assert analytics_data.detection_count > 0, "Total detections not recorded"
        assert analytics_data.active_stations > 0, "Active stations not recorded"
        assert analytics_data.average_confidence is not None, "Average confidence not recorded"
