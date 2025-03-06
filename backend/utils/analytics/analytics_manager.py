from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, text
import logging
from models.models import (
    Track, TrackDetection, TrackStats, ArtistStats, StationTrackStats,
    RadioStation, StationStatus, AnalyticsData, DetectionHourly,
    DetectionDaily, DetectionMonthly, TrackDaily, TrackMonthly,
    ArtistDaily, ArtistMonthly, Artist
)

logger = logging.getLogger(__name__)

class AnalyticsManager:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logger

    async def update_all_analytics(self, detection_data: Dict) -> None:
        """Update all analytics tables in a single transaction"""
        in_transaction = False
        try:
            # Use PostgreSQL's SERIALIZABLE isolation level for analytics
            await self.db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            
            async with self.db.begin():
                in_transaction = True
                current_time = datetime.now()
                
                # Extract and validate data
                station_id = detection_data['station_id']
                track_id = detection_data['track_id']
                confidence = detection_data['confidence']
                play_duration = detection_data['play_duration']
                
                # Validate data types
                if not isinstance(station_id, int):
                    raise ValueError(f"station_id must be an integer, got {type(station_id)}")
                if not isinstance(track_id, (int, type(None))):
                    raise ValueError(f"track_id must be an integer or None, got {type(track_id)}")
                if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                    raise ValueError(f"confidence must be a float between 0 and 1, got {confidence}")
                if not isinstance(play_duration, timedelta):
                    raise ValueError(f"play_duration must be a timedelta, got {type(play_duration)}")
                
                # Use a single query to get all required data
                base_data = await self.db.execute(text("""
                    SELECT 
                        t.id as track_id,
                        t.artist,
                        t.title,
                        ts.detection_count,
                        ts.total_play_time,
                        a.detection_count as artist_count,
                        a.total_play_time as artist_play_time,
                        sts.play_count,
                        sts.total_play_time as station_play_time
                    FROM tracks t
                    LEFT JOIN track_stats ts ON t.id = ts.track_id
                    LEFT JOIN artist_stats a ON t.artist = a.artist_name
                    LEFT JOIN station_track_stats sts ON 
                        t.id = sts.track_id AND 
                        sts.station_id = :station_id
                    WHERE t.id = :track_id
                """), {
                    'station_id': station_id,
                    'track_id': track_id
                })
                
                base_data = await base_data.first()
                
                # 1. Update detection counts and stats using efficient upsert
                await self._update_detection_stats_efficient(
                    station_id, track_id, confidence,
                    play_duration, current_time, base_data
                )
                
                # 2. Update analytics data with window functions
                await self._update_analytics_data_efficient(confidence, current_time)
                
                # 3. Update temporal aggregates using batch upsert
                await self._update_temporal_aggregates_efficient(
                    station_id, track_id,
                    base_data['artist'] if base_data else None,
                    current_time, play_duration
                )
                
                # 4. Update station status efficiently
                await self._update_station_status_efficient(station_id, current_time)
                
                # Update materialized views if they exist
                await self.db.execute(text("""
                    REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS detection_stats_mv;
                    REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS artist_stats_mv;
                    REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS station_stats_mv;
                """))
                
                self.logger.info(
                    "Analytics update completed successfully",
                    extra={
                        'station_id': station_id,
                        'track_id': track_id,
                        'timestamp': current_time.isoformat()
                    }
                )
                
        except Exception as e:
            self.logger.error(
                f"Error updating analytics: {str(e)}",
                exc_info=True,
                extra={'detection_data': detection_data}
            )
            # Only call rollback if we're not in a transaction context
            if not in_transaction:
                await self.db.rollback()
            raise

    async def _update_detection_stats_efficient(
        self, station_id: int, track_id: int,
        confidence: float, play_duration: timedelta,
        current_time: datetime, base_data: Dict
    ) -> None:
        """Update detection statistics using PostgreSQL-specific features"""
        try:
            # Use upsert (INSERT ... ON CONFLICT) for track stats
            await self.db.execute(text("""
                INSERT INTO track_stats (
                    track_id, detection_count, average_confidence,
                    last_detected, total_play_time
                ) VALUES (
                    :track_id, 1, :confidence,
                    :current_time, :play_duration
                )
                ON CONFLICT (track_id) DO UPDATE SET
                    detection_count = track_stats.detection_count + 1,
                    average_confidence = (
                        track_stats.average_confidence * track_stats.detection_count + :confidence
                    ) / (track_stats.detection_count + 1),
                    last_detected = :current_time,
                    total_play_time = track_stats.total_play_time + :play_duration
            """), {
                'track_id': track_id,
                'confidence': confidence,
                'current_time': current_time,
                'play_duration': play_duration
            })
            
            # Update artist and artist stats
            if base_data and base_data['artist_id']:
                # Update artist totals
                await self.db.execute(text("""
                    UPDATE artists
                    SET 
                        total_plays = total_plays + 1,
                        total_play_time = COALESCE(total_play_time, '0 seconds'::interval) + :play_duration,
                        updated_at = :current_time
                    WHERE id = :artist_id
                """), {
                    'artist_id': base_data['artist_id'],
                    'play_duration': play_duration,
                    'current_time': current_time
                })
                
                # Update artist stats
                await self.db.execute(text("""
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
                        total_play_time = COALESCE(artist_stats.total_play_time, '0 seconds'::interval) + :play_duration,
                        average_confidence = (
                            artist_stats.average_confidence * artist_stats.total_plays + :confidence
                        ) / (artist_stats.total_plays + 1)
                """), {
                    'artist_id': base_data['artist_id'],
                    'current_time': current_time,
                    'play_duration': play_duration,
                    'confidence': confidence
                })
            
            # Use upsert for station-track stats
            await self.db.execute(text("""
                INSERT INTO station_track_stats (
                    station_id, track_id, play_count,
                    total_play_time, last_played, average_confidence
                ) VALUES (
                    :station_id, :track_id, 1,
                    :play_duration, :current_time, :confidence
                )
                ON CONFLICT (station_id, track_id) DO UPDATE SET
                    play_count = station_track_stats.play_count + 1,
                    total_play_time = COALESCE(station_track_stats.total_play_time, '0 seconds'::interval) + :play_duration,
                    last_played = :current_time,
                    average_confidence = (
                        station_track_stats.average_confidence * station_track_stats.play_count + :confidence
                    ) / (station_track_stats.play_count + 1)
            """), {
                'station_id': station_id,
                'track_id': track_id,
                'play_duration': play_duration,
                'current_time': current_time,
                'confidence': confidence
            })
            
        except Exception as e:
            self.logger.error(f"Error updating detection stats: {str(e)}", exc_info=True)
            raise

    async def _update_analytics_data_efficient(
        self, confidence: float,
        current_time: datetime
    ) -> None:
        """Update analytics data using window functions"""
        try:
            # Use window functions for efficient calculations
            await self.db.execute(text("""
                WITH hourly_stats AS (
                    SELECT 
                        COUNT(*) as hourly_count,
                        COUNT(DISTINCT station_id) as active_stations
                    FROM track_detections
                    WHERE detected_at >= :hour_ago
                ),
                confidence_stats AS (
                    SELECT 
                        AVG(confidence) as avg_confidence,
                        COUNT(*) as total_detections
                    FROM track_detections
                )
                INSERT INTO analytics_data (
                    detection_count, detection_rate,
                    active_stations, average_confidence, timestamp
                )
                SELECT 
                    cs.total_detections,
                    hs.hourly_count::float / 60.0,
                    hs.active_stations,
                    cs.avg_confidence,
                    :current_time
                FROM hourly_stats hs, confidence_stats cs
            """), {
                'hour_ago': current_time - timedelta(hours=1),
                'current_time': current_time
            })
            
        except Exception as e:
            self.logger.error(f"Error updating analytics data: {str(e)}", exc_info=True)
            raise

    async def _update_temporal_aggregates_efficient(
        self, station_id: int, track_id: int,
        artist_id: int, current_time: datetime,
        play_duration: timedelta
    ) -> None:
        """Update temporal aggregates using batch upsert"""
        try:
            hour_start = current_time.replace(minute=0, second=0, microsecond=0)
            day_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Batch update all temporal aggregates
            await self.db.execute(text("""
                -- Hourly detections
                INSERT INTO detection_hourly (hour, count)
                VALUES (:hour_start, 1)
                ON CONFLICT (hour) DO UPDATE SET
                    count = detection_hourly.count + 1;
                
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
                INSERT INTO artist_daily (
                    artist_id, date, count, total_play_time
                )
                VALUES (
                    :artist_id, :day_start, 1, :play_duration
                )
                ON CONFLICT (artist_id, date) DO UPDATE SET
                    count = artist_daily.count + 1,
                    total_play_time = COALESCE(artist_daily.total_play_time, '0 seconds'::interval) + :play_duration;
                
                -- Monthly artist stats
                INSERT INTO artist_monthly (
                    artist_id, month, count, total_play_time
                )
                VALUES (
                    :artist_id, :month_start, 1, :play_duration
                )
                ON CONFLICT (artist_id, month) DO UPDATE SET
                    count = artist_monthly.count + 1,
                    total_play_time = COALESCE(artist_monthly.total_play_time, '0 seconds'::interval) + :play_duration;
            """), {
                'hour_start': hour_start,
                'day_start': day_start,
                'month_start': month_start,
                'track_id': track_id,
                'artist_id': artist_id,
                'play_duration': play_duration
            })
            
        except Exception as e:
            self.logger.error(f"Error updating temporal aggregates: {str(e)}", exc_info=True)
            raise

    async def _update_station_status_efficient(
        self, station_id: int,
        current_time: datetime
    ) -> None:
        """Update station status using efficient batch updates"""
        try:
            hour_ago = current_time - timedelta(hours=1)
            
            # Update all station statuses in a single query
            await self.db.execute(text("""
                WITH station_updates AS (
                    SELECT 
                        id,
                        CASE 
                            WHEN id = :station_id THEN true
                            WHEN last_detection_time < :hour_ago THEN false
                            ELSE is_active
                        END as new_is_active,
                        CASE 
                            WHEN id = :station_id THEN 'active'
                            WHEN last_detection_time < :hour_ago THEN 'inactive'
                            ELSE status
                        END as new_status,
                        CASE 
                            WHEN id = :station_id THEN :current_time
                            ELSE last_detection_time
                        END as new_last_detection
                    FROM radio_stations
                    WHERE is_active = true OR id = :station_id
                )
                UPDATE radio_stations
                SET 
                    is_active = su.new_is_active,
                    status = su.new_status::station_status,
                    last_detection_time = su.new_last_detection
                FROM station_updates su
                WHERE radio_stations.id = su.id
            """), {
                'station_id': station_id,
                'current_time': current_time,
                'hour_ago': hour_ago
            })
            
        except Exception as e:
            self.logger.error(f"Error updating station status: {str(e)}", exc_info=True)
            raise 