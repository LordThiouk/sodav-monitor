"""
Database operations module for SODAV Monitor.

This module provides functionality for database operations related to music detection.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import func
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

# Configure logging
logger = logging.getLogger(__name__)


class DBOperations:
    """
    Class for database operations related to music detection.

    This class provides methods for creating, updating, and retrieving
    tracks, artists, and detections in the database.
    """

    def __init__(self, db_session: Session):
        """
        Initialize the DBOperations with a database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session

    def get_or_create_artist(self, name: str, label: Optional[str] = None) -> Artist:
        """
        Get or create an artist in the database.

        Args:
            name: Artist name
            label: Artist label

        Returns:
            Artist object
        """
        try:
            # Search for existing artist
            artist = (
                self.db_session.query(Artist)
                .filter(func.lower(Artist.name) == func.lower(name))
                .first()
            )

            if artist:
                return artist

            # Create new artist
            artist = Artist(name=name, label=label)

            self.db_session.add(artist)
            self.db_session.commit()
            self.db_session.refresh(artist)

            logger.info(f"Created new artist: {name}")
            return artist

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error getting or creating artist: {e}")
            raise

    def get_or_create_track(
        self,
        title: str,
        artist_id: int,
        fingerprint: str,
        fingerprint_raw: Optional[bytes] = None,
        isrc: Optional[str] = None,
        label: Optional[str] = None,
    ) -> Track:
        """
        Get or create a track in the database.

        Args:
            title: Track title
            artist_id: Artist ID
            fingerprint: Track fingerprint
            fingerprint_raw: Raw fingerprint data
            isrc: International Standard Recording Code
            label: Track label

        Returns:
            Track object
        """
        try:
            # Search for existing track by fingerprint
            track = self.db_session.query(Track).filter(Track.fingerprint == fingerprint).first()

            if track:
                return track

            # Search for existing track by title and artist
            track = (
                self.db_session.query(Track)
                .filter(func.lower(Track.title) == func.lower(title), Track.artist_id == artist_id)
                .first()
            )

            if track:
                # Update fingerprint if not set
                if not track.fingerprint:
                    track.fingerprint = fingerprint
                    track.fingerprint_raw = fingerprint_raw
                    self.db_session.commit()
                    self.db_session.refresh(track)

                return track

            # Create new track
            track = Track(
                title=title,
                artist_id=artist_id,
                fingerprint=fingerprint,
                fingerprint_raw=fingerprint_raw,
                isrc=isrc,
                label=label,
            )

            self.db_session.add(track)
            self.db_session.commit()
            self.db_session.refresh(track)

            # Create track stats
            track_stats = TrackStats(
                track_id=track.id,
                total_plays=0,
                average_confidence=0.0,
                total_play_time=timedelta(0),
            )

            self.db_session.add(track_stats)
            self.db_session.commit()

            logger.info(f"Created new track: {title} by artist ID {artist_id}")
            return track

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error getting or creating track: {e}")
            raise

    def create_detection(
        self,
        track_id: int,
        station_id: int,
        confidence: float,
        play_duration: timedelta,
        fingerprint: str,
        audio_hash: Optional[str] = None,
    ) -> TrackDetection:
        """
        Create a new detection in the database.

        Args:
            track_id: Track ID
            station_id: Station ID
            confidence: Detection confidence
            play_duration: Play duration
            fingerprint: Detection fingerprint
            audio_hash: Audio hash

        Returns:
            TrackDetection object
        """
        try:
            # Create detection
            detection = TrackDetection(
                track_id=track_id,
                station_id=station_id,
                confidence=confidence,
                detected_at=datetime.utcnow(),
                play_duration=play_duration,
                fingerprint=fingerprint,
                audio_hash=audio_hash,
            )

            self.db_session.add(detection)
            self.db_session.commit()
            self.db_session.refresh(detection)

            # Update track stats
            self._update_track_stats(track_id, confidence, play_duration)

            # Update artist stats
            track = self.db_session.query(Track).filter(Track.id == track_id).first()
            if track and track.artist_id:
                self._update_artist_stats(track.artist_id, confidence, play_duration)

            # Update station-track stats
            self._update_station_track_stats(station_id, track_id, play_duration)

            logger.info(f"Created new detection: Track ID {track_id} on Station ID {station_id}")
            return detection

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error creating detection: {e}")
            raise

    def _update_track_stats(
        self, track_id: int, confidence: float, play_duration: timedelta
    ) -> None:
        """
        Update track statistics.

        Args:
            track_id: Track ID
            confidence: Detection confidence
            play_duration: Play duration
        """
        try:
            # Get track stats
            track_stats = (
                self.db_session.query(TrackStats).filter(TrackStats.track_id == track_id).first()
            )

            if not track_stats:
                # Create track stats if not exists
                track_stats = TrackStats(
                    track_id=track_id,
                    total_plays=0,
                    average_confidence=0.0,
                    total_play_time=timedelta(0),
                )
                self.db_session.add(track_stats)

            # Update stats
            track_stats.total_plays += 1
            track_stats.last_detected = datetime.utcnow()
            track_stats.total_play_time += play_duration

            # Update average confidence
            track_stats.average_confidence = (
                track_stats.average_confidence * (track_stats.total_plays - 1) + confidence
            ) / track_stats.total_plays

            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating track stats: {e}")
            raise

    def _update_artist_stats(
        self, artist_id: int, confidence: float, play_duration: timedelta
    ) -> None:
        """
        Update artist statistics.

        Args:
            artist_id: Artist ID
            confidence: Detection confidence
            play_duration: Play duration
        """
        try:
            # Get artist stats
            artist_stats = (
                self.db_session.query(ArtistStats)
                .filter(ArtistStats.artist_id == artist_id)
                .first()
            )

            if not artist_stats:
                # Create artist stats if not exists
                artist_stats = ArtistStats(
                    artist_id=artist_id,
                    total_plays=0,
                    average_confidence=0.0,
                    total_play_time=timedelta(0),
                )
                self.db_session.add(artist_stats)

            # Update stats
            artist_stats.total_plays += 1
            artist_stats.last_detected = datetime.utcnow()
            artist_stats.total_play_time += play_duration

            # Update average confidence
            artist_stats.average_confidence = (
                artist_stats.average_confidence * (artist_stats.total_plays - 1) + confidence
            ) / artist_stats.total_plays

            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating artist stats: {e}")
            raise

    def _update_station_track_stats(
        self, station_id: int, track_id: int, play_duration: timedelta
    ) -> None:
        """
        Update station-track statistics.

        Args:
            station_id: Station ID
            track_id: Track ID
            play_duration: Play duration
        """
        try:
            # Get station-track stats
            station_track_stats = (
                self.db_session.query(StationTrackStats)
                .filter(
                    StationTrackStats.station_id == station_id,
                    StationTrackStats.track_id == track_id,
                )
                .first()
            )

            if not station_track_stats:
                # Create station-track stats if not exists
                station_track_stats = StationTrackStats(
                    station_id=station_id, track_id=track_id, play_count=0
                )
                self.db_session.add(station_track_stats)

            # Update stats
            station_track_stats.play_count += 1

            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating station-track stats: {e}")
            raise

    def get_recent_detections(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent detections with track and station information.

        Args:
            limit: Maximum number of detections to return

        Returns:
            List of detection dictionaries
        """
        try:
            # Query recent detections with track and station information
            detections = (
                self.db_session.query(TrackDetection, Track, Artist, RadioStation)
                .join(Track, TrackDetection.track_id == Track.id)
                .join(Artist, Track.artist_id == Artist.id)
                .join(RadioStation, TrackDetection.station_id == RadioStation.id)
                .order_by(TrackDetection.detected_at.desc())
                .limit(limit)
                .all()
            )

            # Format results
            result = []
            for detection, track, artist, station in detections:
                result.append(
                    {
                        "id": detection.id,
                        "detected_at": detection.detected_at.isoformat(),
                        "confidence": detection.confidence,
                        "play_duration": str(detection.play_duration),
                        "track": {
                            "id": track.id,
                            "title": track.title,
                            "isrc": track.isrc,
                            "label": track.label,
                        },
                        "artist": {"id": artist.id, "name": artist.name, "label": artist.label},
                        "station": {
                            "id": station.id,
                            "name": station.name,
                            "country": station.country,
                            "language": station.language,
                        },
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error getting recent detections: {e}")
            return []
