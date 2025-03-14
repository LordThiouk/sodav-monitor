"""Module for updating statistics in the database.

This module provides functionality for updating and maintaining various statistics
in the SODAV Monitor database, including track, artist, and station statistics.
"""
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.models import Track, TrackDetection, TrackStats
from backend.utils.logging_config import setup_logging

logger = setup_logging(__name__)


class StatsUpdater:
    """Statistics manager for the application.

    This class handles all statistics updates and aggregations for tracks,
    artists, and stations in the SODAV Monitor system. It provides efficient
    batch updates and ensures data consistency across all statistics tables.
    """

    def __init__(self, db_session: Session):
        """Initialize the statistics updater.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self.logger = logger

    def _validate_duration(self, duration: timedelta) -> timedelta:
        """Validate and normalize duration values.

        This method ensures that all duration values are valid timedelta objects
        within reasonable bounds (positive and not exceeding 1 hour).

        Args:
            duration: The duration to validate, can be timedelta, int, float, or string

        Returns:
            A valid timedelta object
        """
        try:
            # If duration is None, return minimum duration
            if duration is None:
                self.logger.warning("Duration is None, using default minimum duration")
                return timedelta(seconds=15)

            # Convert to timedelta if not already
            if not isinstance(duration, timedelta):
                self.logger.warning(
                    f"Invalid duration type: {type(duration)}, converting to timedelta"
                )

                # Handle numeric types (int, float)
                if isinstance(duration, (int, float)):
                    # Ensure positive value
                    seconds = max(0, float(duration))
                    duration = timedelta(seconds=seconds)

                # Handle string format (could be "HH:MM:SS" or seconds as string)
                elif isinstance(duration, str):
                    try:
                        # Try to parse as "HH:MM:SS" format
                        if ":" in duration:
                            parts = duration.split(":")
                            if len(parts) == 3:
                                hours, minutes, seconds = map(float, parts)
                                duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
                            elif len(parts) == 2:
                                minutes, seconds = map(float, parts)
                                duration = timedelta(minutes=minutes, seconds=seconds)
                            else:
                                # Invalid format, use default
                                self.logger.error(f"Invalid time format: {duration}")
                                return timedelta(seconds=15)
                        else:
                            # Try to parse as seconds
                            seconds = float(duration)
                            duration = timedelta(seconds=seconds)
                    except Exception as e:
                        self.logger.error(
                            f"Could not parse duration string: {duration}, error: {str(e)}"
                        )
                        return timedelta(seconds=15)
                else:
                    # Unknown type, use default
                    self.logger.error(f"Unsupported duration type: {type(duration)}")
                    return timedelta(seconds=15)

            # Validate the timedelta bounds
            seconds = duration.total_seconds()

            # Handle zero or negative duration
            if seconds <= 0:
                self.logger.warning(
                    f"Duration is zero or negative ({seconds}s), using default minimum"
                )
                return timedelta(seconds=15)

            # Cap maximum duration
            if seconds > 3600:
                self.logger.warning(f"Duration exceeds maximum ({seconds}s), capping at 1 hour")
                return timedelta(hours=1)

            return duration

        except Exception as e:
            self.logger.error(f"Error validating duration: {str(e)}", exc_info=True)
            return timedelta(seconds=15)

    def update_all_stats(
        self, detection_result: dict, station_id: int, track: Track, play_duration: timedelta
    ):
        """Update all statistics after a successful detection using efficient batch updates.

        This method coordinates the update of all statistics tables after a track detection,
        including detection stats, temporal aggregates, analytics data, and station status.

        Args:
            detection_result: The detection result containing confidence and other metadata
            station_id: The ID of the station where the track was detected
            track: The detected Track object
            play_duration: How long the track was played
        """
        play_duration = self._validate_duration(play_duration)
        current_time = datetime.now()

        try:
            self.logger.info(
                "Starting efficient stats update",
                extra={
                    "station_id": station_id,
                    "track_id": track.id if track else None,
                    "duration": str(play_duration),
                },
            )

            # 1. Update all detection-related stats in a single transaction
            if track:
                self._update_detection_stats_efficient(
                    station_id=station_id,
                    track_id=track.id,
                    artist_id=track.artist_id,
                    confidence=detection_result["confidence"],
                    play_duration=play_duration,
                    current_time=current_time,
                )

            # 2. Update temporal aggregates
            self._update_temporal_aggregates_efficient(
                station_id=station_id,
                track_id=track.id if track else None,
                artist_id=track.artist_id if track else None,
                current_time=current_time,
                play_duration=play_duration,
            )

            # 3. Update analytics data
            self._update_analytics_data_efficient(
                confidence=detection_result["confidence"], current_time=current_time
            )

            # 4. Update station status
            self._update_station_status_efficient(station_id=station_id, current_time=current_time)

            self.db_session.commit()
            self.logger.info("Efficient stats update completed successfully")

        except Exception as e:
            self.logger.error("Error in stats update", extra={"error": str(e)}, exc_info=True)
            self.db_session.rollback()
            raise

    def _update_detection_stats_efficient(
        self,
        station_id: int,
        track_id: int,
        artist_id: int,
        confidence: float,
        play_duration: timedelta,
        current_time: datetime,
    ):
        """Update all detection-related statistics using efficient batch updates.

        This method updates track, artist, and station-track statistics in a single
        database transaction for improved performance.

        Args:
            station_id: The ID of the station where the track was detected
            track_id: The ID of the detected track
            artist_id: The ID of the track's artist
            confidence: The detection confidence score
            play_duration: How long the track was played
            current_time: The current timestamp
        """
        try:
            self.logger.info(
                "Starting stats update",
                extra={
                    "station_id": station_id,
                    "track_id": track_id,
                    "artist_id": artist_id,
                    "confidence": confidence,
                    "play_duration": str(play_duration),
                },
            )

            # Use a single transaction for all updates
            result = self.db_session.execute(
                text(
                    """
                -- Update track stats
                WITH track_update AS (
                    INSERT INTO track_stats (
                        track_id, total_plays, average_confidence,
                        last_detected, total_play_time
                    ) VALUES (
                        :track_id, 1, :confidence,
                        :current_time, :play_duration
                    )
                    ON CONFLICT (track_id) DO UPDATE SET
                        total_plays = track_stats.total_plays + 1,
                        average_confidence = (
                            track_stats.average_confidence * track_stats.total_plays + :confidence
                        ) / (track_stats.total_plays + 1),
                        last_detected = :current_time,
                        total_play_time = COALESCE(track_stats.total_play_time,
                                                  '0 seconds'::interval) + :play_duration
                    RETURNING total_plays, average_confidence
                ),
                -- Update artist stats
                artist_update AS (
                    INSERT INTO artist_stats (
                        artist_id, total_plays,
                        last_detected, total_play_time,
                        average_confidence
                    ) VALUES (
                        :artist_id, 1,
                        :current_time, :play_duration,
                        :confidence
                    )
                    ON CONFLICT (artist_id) DO UPDATE SET
                        total_plays = artist_stats.total_plays + 1,
                        last_detected = :current_time,
                        total_play_time = COALESCE(artist_stats.total_play_time,
                                                  '0 seconds'::interval) + :play_duration,
                        average_confidence = (
                            artist_stats.average_confidence * artist_stats.total_plays + :confidence
                        ) / (artist_stats.total_plays + 1)
                    RETURNING total_plays, average_confidence
                ),
                -- Update station-track stats
                station_update AS (
                    INSERT INTO station_track_stats (
                        station_id, track_id, play_count,
                        total_play_time, last_played, average_confidence
                    ) VALUES (
                        :station_id, :track_id, 1,
                        :play_duration, :current_time, :confidence
                    )
                    ON CONFLICT (station_id, track_id) DO UPDATE SET
                        play_count = station_track_stats.play_count + 1,
                        total_play_time = COALESCE(station_track_stats.total_play_time,
                                                  '0 seconds'::interval) + :play_duration,
                        last_played = :current_time,
                        average_confidence = (
                            station_track_stats.average_confidence * station_track_stats.play_count
                            + :confidence
                        ) / (station_track_stats.play_count + 1)
                    RETURNING play_count, average_confidence
                )
                SELECT
                    (SELECT total_plays FROM track_update) as track_count,
                    (SELECT total_plays FROM artist_update) as artist_play_count;
            """
                ),
                {
                    "station_id": station_id,
                    "track_id": track_id,
                    "artist_id": artist_id,
                    "confidence": confidence,
                    "play_duration": play_duration,
                    "current_time": current_time,
                },
            )

            stats = result.fetchone()
            self.logger.info(
                "Stats update completed",
                extra={
                    "track_detections": stats.track_count,
                    "artist_detections": stats.artist_play_count,
                    "update_time": current_time.isoformat(),
                },
            )

        except Exception as e:
            self.logger.error(f"Error updating detection stats: {str(e)}", exc_info=True)
            raise

    def _update_temporal_aggregates_efficient(
        self,
        station_id: int,
        track_id: int,
        artist_id: int,
        current_time: datetime,
        play_duration: timedelta,
    ):
        """Update all temporal aggregates using batch updates.

        This method updates hourly, daily, and monthly aggregates for detections,
        tracks, and artists in a single database transaction.

        Args:
            station_id: The ID of the station where the track was detected
            track_id: The ID of the detected track
            artist_id: The ID of the track's artist
            current_time: The current timestamp
            play_duration: How long the track was played
        """
        try:
            hour_start = current_time.replace(minute=0, second=0, microsecond=0)
            day_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            self.db_session.execute(
                text(
                    """
                -- Hourly detections
                INSERT INTO detection_hourly (hour, count)
                VALUES (:hour_start, 1)
                ON CONFLICT (hour) DO UPDATE SET
                    count = detection_hourly.count + 1;

                -- Daily detections
                INSERT INTO detection_daily (date, count)
                VALUES (:day_start, 1)
                ON CONFLICT (date) DO UPDATE SET
                    count = detection_daily.count + 1;

                -- Monthly detections
                INSERT INTO detection_monthly (month, count)
                VALUES (:month_start, 1)
                ON CONFLICT (month) DO UPDATE SET
                    count = detection_monthly.count + 1;

                -- Daily track stats
                INSERT INTO track_daily (track_id, date, count)
                VALUES (:track_id, :day_start, 1)
                ON CONFLICT (track_id, date) DO UPDATE SET
                    count = track_daily.count + 1;

                -- Monthly track stats
                INSERT INTO track_monthly (track_id, month, count)
                VALUES (:track_id, :month_start, 1)
                ON CONFLICT (track_id, month) DO UPDATE SET
                    count = track_monthly.count + 1;

                -- Daily artist stats
                INSERT INTO artist_daily (artist_id, date, count, total_play_time)
                VALUES (:artist_id, :day_start, 1, :play_duration)
                ON CONFLICT (artist_id, date) DO UPDATE SET
                    count = artist_daily.count + 1,
                    total_play_time = COALESCE(artist_daily.total_play_time,
                                              '0 seconds'::interval) + :play_duration;

                -- Monthly artist stats
                INSERT INTO artist_monthly (artist_id, month, count, total_play_time)
                VALUES (:artist_id, :month_start, 1, :play_duration)
                ON CONFLICT (artist_id, month) DO UPDATE SET
                    count = artist_monthly.count + 1,
                    total_play_time = COALESCE(artist_monthly.total_play_time,
                                              '0 seconds'::interval) + :play_duration;
            """
                ),
                {
                    "hour_start": hour_start,
                    "day_start": day_start,
                    "month_start": month_start,
                    "track_id": track_id,
                    "artist_id": artist_id,
                    "play_duration": play_duration,
                },
            )

        except Exception as e:
            self.logger.error(f"Error updating temporal aggregates: {str(e)}", exc_info=True)
            raise

    def _update_analytics_data_efficient(self, confidence: float, current_time: datetime):
        """Update analytics data using window functions.

        This method updates global analytics data including detection counts,
        rates, and active stations.

        Args:
            confidence: The detection confidence score
            current_time: The current timestamp
        """
        try:
            hour_ago = current_time - timedelta(hours=1)

            # Créer l'enregistrement horaire même s'il n'y a pas de détections
            self.db_session.execute(
                text(
                    """
                INSERT INTO detection_hourly (hour, count)
                VALUES (date_trunc('hour', :current_time), 0)
                ON CONFLICT (hour) DO UPDATE SET
                    count = detection_hourly.count;

                -- Créer ou mettre à jour les statistiques artiste
                INSERT INTO artist_stats (
                    artist_id, total_plays, average_confidence,
                    last_detected, total_play_time
                )
                SELECT
                    a.id,
                    COALESCE(COUNT(td.id), 0),
                    COALESCE(AVG(td.confidence), 0),
                    MAX(td.detected_at),
                    COALESCE(SUM(td.play_duration), interval '0')
                FROM artists a
                LEFT JOIN tracks t ON t.artist_id = a.id
                LEFT JOIN track_detections td ON td.track_id = t.id
                WHERE td.detected_at >= :hour_ago OR td.detected_at IS NULL
                GROUP BY a.id
                ON CONFLICT (artist_id) DO UPDATE SET
                    total_plays = EXCLUDED.total_plays,
                    last_detected = EXCLUDED.last_detected,
                    total_play_time = EXCLUDED.total_play_time,
                    average_confidence = EXCLUDED.average_confidence;

                -- Créer ou mettre à jour les statistiques de pistes
                INSERT INTO track_stats (
                    track_id, total_plays, average_confidence,
                    last_detected, total_play_time
                )
                SELECT
                    t.id,
                    0 as total_plays,
                    0.0 as average_confidence,
                    NULL as last_detected,
                    interval '0' as total_play_time
                FROM tracks t
                WHERE NOT EXISTS (
                    SELECT 1 FROM track_stats ts WHERE ts.track_id = t.id
                );

                -- Mettre à jour les données analytics globales
                INSERT INTO analytics_data (
                    detection_count,
                    detection_rate,
                    active_stations,
                    average_confidence,
                    timestamp
                )
                SELECT
                    COALESCE(COUNT(td.id), 0) as total_detections,
                    COALESCE(COUNT(td.id)::float / NULLIF(COUNT(DISTINCT rs.id), 0), 0)
                        as detection_rate,
                    COUNT(DISTINCT CASE WHEN td.detected_at >= :hour_ago THEN rs.id END)
                        as active_stations,
                    COALESCE(AVG(td.confidence), 0) as avg_confidence,
                    :current_time as timestamp
                FROM radio_stations rs
                LEFT JOIN track_detections td ON td.station_id = rs.id
                    AND td.detected_at >= :hour_ago;
            """
                ),
                {"hour_ago": hour_ago, "current_time": current_time},
            )

            self.logger.info(
                "Analytics data updated successfully",
                extra={"timestamp": current_time.isoformat(), "update_type": "analytics"},
            )

        except Exception as e:
            self.logger.error(f"Error updating analytics data: {str(e)}", exc_info=True)
            raise

    def _update_station_status_efficient(self, station_id: int, current_time: datetime):
        """Update station status based on recent detections.

        This method updates the status of a radio station based on its recent
        detection activity.

        Args:
            station_id: The ID of the station to update
            current_time: The current timestamp
        """
        try:
            self.db_session.execute(
                text(
                    """
                UPDATE radio_stations
                SET
                    last_checked = :current_time,
                    status = CASE
                        WHEN status = 'INACTIVE' THEN 'ACTIVE'::station_status
                        ELSE status
                    END
                WHERE id = :station_id
            """
                ),
                {"station_id": station_id, "current_time": current_time},
            )

            self.logger.info(
                "Station status updated",
                extra={"station_id": station_id, "timestamp": current_time.isoformat()},
            )

        except Exception as e:
            self.logger.error(f"Error updating station status: {str(e)}", exc_info=True)
            raise

    async def verify_and_init_stats(self):
        """Verify and initialize statistics for all entities.

        This method checks for missing statistics records and initializes them
        for all tracks, artists, and stations.
        """
        try:
            self.logger.info("Verifying and initializing statistics")

            # Initialize track stats
            self.db_session.execute(
                text(
                    """
                INSERT INTO track_stats (
                    track_id, total_plays, average_confidence,
                    last_detected, total_play_time
                )
                SELECT
                    t.id as track_id,
                    COALESCE(COUNT(td.id), 0) as total_plays,
                    COALESCE(AVG(td.confidence), 0) as average_confidence,
                    MAX(td.detected_at) as last_detected,
                    COALESCE(SUM(td.play_duration), interval '0') as total_play_time
                FROM tracks t
                LEFT JOIN track_detections td ON td.track_id = t.id
                WHERE NOT EXISTS (
                    SELECT 1 FROM track_stats ts WHERE ts.track_id = t.id
                )
                GROUP BY t.id;
            """
                )
            )

            # Initialize artist stats
            self.db_session.execute(
                text(
                    """
                INSERT INTO artist_stats (
                    artist_id, total_plays, average_confidence,
                    last_detected, total_play_time
                )
                SELECT
                    a.id as artist_id,
                    COALESCE(COUNT(td.id), 0) as total_plays,
                    COALESCE(AVG(td.confidence), 0) as average_confidence,
                    MAX(td.detected_at) as last_detected,
                    COALESCE(SUM(td.play_duration), interval '0') as total_play_time
                FROM artists a
                LEFT JOIN tracks t ON t.artist_id = a.id
                LEFT JOIN track_detections td ON td.track_id = t.id
                WHERE NOT EXISTS (
                    SELECT 1 FROM artist_stats ast WHERE ast.artist_id = a.id
                )
                GROUP BY a.id;
            """
                )
            )

            # Mettre à jour les compteurs globaux
            self.db_session.execute(
                text(
                    """
                INSERT INTO analytics_data (
                    detection_count,
                    detection_rate,
                    active_stations,
                    average_confidence,
                    timestamp
                )
                SELECT
                    COALESCE(COUNT(td.id), 0) as total_detections,
                    COALESCE(COUNT(td.id)::float / NULLIF(COUNT(DISTINCT rs.id), 0), 0) as detection_rate,
                    COUNT(DISTINCT CASE WHEN td.detected_at >= now() - interval '1 hour' THEN rs.id END) as active_stations,
                    COALESCE(AVG(td.confidence), 0) as avg_confidence,
                    now() as timestamp
                FROM radio_stations rs
                LEFT JOIN track_detections td ON td.station_id = rs.id
                    AND td.detected_at >= now() - interval '1 hour';
            """
                )
            )

            self.db_session.commit()
            self.logger.info("Statistics initialization completed successfully")

        except Exception as e:
            self.logger.error(f"Error initializing statistics: {str(e)}")
            self.db_session.rollback()
            raise

    async def monitor_stats_health(self):
        """Monitor the health of statistics.

        Checks for missing statistics and initializes them if needed.

        Returns:
            Dict containing health status information
        """
        try:
            results = self.db_session.execute(
                text(
                    """
                SELECT
                    (SELECT COUNT(*) FROM artists
                     WHERE id NOT IN (SELECT artist_id FROM artist_stats)) as missing_artist_stats,
                    (SELECT COUNT(*) FROM tracks
                     WHERE id NOT IN (SELECT track_id FROM track_stats)) as missing_track_stats,
                    (SELECT COUNT(*) FROM detection_hourly
                     WHERE hour >= now() - interval '24 hours') as hourly_records_24h
            """
                )
            ).fetchone()

            if results.missing_artist_stats > 0 or results.missing_track_stats > 0:
                self.logger.warning(
                    "Missing statistics detected",
                    extra={
                        "missing_artist_stats": results.missing_artist_stats,
                        "missing_track_stats": results.missing_track_stats,
                        "hourly_records_24h": results.hourly_records_24h,
                    },
                )
                await self.verify_and_init_stats()

            return {
                "status": "healthy" if all(x == 0 for x in results) else "needs_attention",
                "missing_artist_stats": results.missing_artist_stats,
                "missing_track_stats": results.missing_track_stats,
                "hourly_records_24h": results.hourly_records_24h,
            }

        except Exception as e:
            self.logger.error(f"Error monitoring stats health: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def initialize_missing_stats(self):
        """Initialize missing statistics records.

        Creates statistics records for any tracks, artists, or stations
        that don't have associated statistics.
        """
        try:
            logger.info("Initializing missing statistics")

            # Initialize track stats
            self.db_session.execute(
                text(
                    """
                INSERT INTO track_stats (
                    track_id, total_plays, average_confidence,
                    last_detected, total_play_time
                )
                SELECT
                    id as track_id,
                    0 as total_plays,
                    0.0 as average_confidence,
                    NULL as last_detected,
                    interval '0' as total_play_time
                FROM tracks t
                WHERE NOT EXISTS (
                    SELECT 1 FROM track_stats ts WHERE ts.track_id = t.id
                );
            """
                )
            )

            # Initialize artist stats
            self.db_session.execute(
                text(
                    """
                INSERT INTO artist_stats (
                    artist_id, total_plays, average_confidence,
                    last_detected, total_play_time
                )
                SELECT
                    id as artist_id,
                    0 as total_plays,
                    0.0 as average_confidence,
                    NULL as last_detected,
                    interval '0' as total_play_time
                FROM artists a
                WHERE NOT EXISTS (
                    SELECT 1 FROM artist_stats ast WHERE ast.artist_id = a.id
                );
            """
                )
            )

            # Initialize station stats
            self.db_session.execute(
                text(
                    """
                INSERT INTO station_stats (
                    station_id, detection_count, last_detected,
                    average_confidence
                )
                SELECT
                    id as station_id,
                    0 as detection_count,
                    NULL as last_detected,
                    0.0 as average_confidence
                FROM radio_stations rs
                WHERE NOT EXISTS (
                    SELECT 1 FROM station_stats ss WHERE ss.station_id = rs.id
                );
            """
                )
            )

            self.db_session.commit()
            logger.info("Successfully initialized missing statistics")

        except Exception as e:
            logger.error(f"Error initializing statistics: {str(e)}")
            self.db_session.rollback()
            raise

    def update_track_stats(self, track_id: int) -> None:
        """Update statistics for a specific track.

        Args:
            track_id: ID of the track to update statistics for
        """
        try:
            # Get track detections from the last 24 hours
            now = datetime.utcnow()
            last_24h = now - timedelta(hours=24)

            detections = (
                self.db_session.query(TrackDetection)
                .filter(TrackDetection.track_id == track_id, TrackDetection.detected_at >= last_24h)
                .all()
            )

            # Calculate statistics
            total_plays = len(detections)
            total_play_time = sum(
                (d.play_duration.total_seconds() for d in detections if d.play_duration), start=0
            )
            avg_confidence = (
                sum(d.confidence for d in detections) / total_plays if total_plays > 0 else 0
            )

            # Update or create track stats
            track_stats = (
                self.db_session.query(TrackStats).filter(TrackStats.track_id == track_id).first()
            )

            if track_stats:
                track_stats.total_plays = total_plays
                track_stats.total_play_time = timedelta(seconds=total_play_time)
                track_stats.average_confidence = avg_confidence
                track_stats.last_detected = (
                    max(d.detected_at for d in detections) if detections else None
                )
            else:
                track_stats = TrackStats(
                    track_id=track_id,
                    total_plays=total_plays,
                    total_play_time=timedelta(seconds=total_play_time),
                    average_confidence=avg_confidence,
                    last_detected=max(d.detected_at for d in detections) if detections else None,
                )
                self.db_session.add(track_stats)

            self.db_session.commit()

        except Exception as e:
            logger.error(f"Error updating track stats: {str(e)}")
            self.db_session.rollback()
            raise
