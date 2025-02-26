"""Module de mise à jour des statistiques."""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, text
from models import (
    RadioStation, Track, TrackDetection, StationTrackStats,
    TrackStats, ArtistStats, AnalyticsData, DetectionHourly,
    DetectionDaily, DetectionMonthly, StationStats, ArtistDaily,
    ArtistMonthly, TrackDaily, TrackMonthly, StationStatus
)
from utils.logging_config import setup_logging

logger = setup_logging(__name__)

class StatsUpdater:
    """Gestionnaire des statistiques."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logger

    def _validate_duration(self, duration: timedelta) -> timedelta:
        """Validate and normalize duration values"""
        try:
            if not isinstance(duration, timedelta):
                self.logger.warning(f"Invalid duration type: {type(duration)}, converting to timedelta")
                if isinstance(duration, (int, float)):
                    duration = timedelta(seconds=float(duration))
                elif isinstance(duration, str):
                    try:
                        hours, minutes, seconds = map(float, duration.split(':'))
                        duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
                    except:
                        self.logger.error(f"Could not parse duration string: {duration}")
                        return timedelta(seconds=15)
                        
            if duration.total_seconds() <= 0:
                self.logger.warning("Duration is zero or negative, using default")
                return timedelta(seconds=15)
            if duration.total_seconds() > 3600:
                self.logger.warning("Duration exceeds maximum, capping at 1 hour")
                return timedelta(hours=1)
                
            return duration
            
        except Exception as e:
            self.logger.error(f"Error validating duration: {str(e)}", exc_info=True)
            return timedelta(seconds=15)

    def update_all_stats(self, detection_result: dict, station_id: int, track: Track, play_duration: timedelta):
        """Update all statistics after a successful detection using efficient batch updates"""
        play_duration = self._validate_duration(play_duration)
        current_time = datetime.now()
        
        try:
            self.logger.info("Starting efficient stats update", extra={
                'station_id': station_id,
                'track_id': track.id if track else None,
                'duration': str(play_duration)
            })

            # 1. Update all detection-related stats in a single transaction
            if track:
                self._update_detection_stats_efficient(
                    station_id=station_id,
                    track_id=track.id,
                    artist_id=track.artist_id,
                    confidence=detection_result['confidence'],
                    play_duration=play_duration,
                    current_time=current_time
                )

            # 2. Update temporal aggregates
            self._update_temporal_aggregates_efficient(
                station_id=station_id,
                track_id=track.id if track else None,
                artist_id=track.artist_id if track else None,
                current_time=current_time,
                play_duration=play_duration
            )

            # 3. Update analytics data
            self._update_analytics_data_efficient(
                confidence=detection_result['confidence'],
                current_time=current_time
            )

            # 4. Update station status
            self._update_station_status_efficient(
                station_id=station_id,
                current_time=current_time
            )

            self.db_session.commit()
            self.logger.info("Efficient stats update completed successfully")
            
        except Exception as e:
            self.logger.error("Error in stats update", extra={'error': str(e)}, exc_info=True)
            self.db_session.rollback()
            raise

    def _update_detection_stats_efficient(self, station_id: int, track_id: int, artist_id: int,
                                        confidence: float, play_duration: timedelta, current_time: datetime):
        """Update all detection-related statistics using efficient batch updates"""
        try:
            self.logger.info("Starting stats update", extra={
                'station_id': station_id,
                'track_id': track_id,
                'artist_id': artist_id,
                'confidence': confidence,
                'play_duration': str(play_duration)
            })

            # Use a single transaction for all updates
            result = self.db_session.execute(text("""
                -- Update track stats
                WITH track_update AS (
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
                        total_play_time = COALESCE(track_stats.total_play_time, '0 seconds'::interval) + :play_duration
                    RETURNING detection_count, average_confidence
                ),
                -- Update artist stats
                artist_update AS (
                    INSERT INTO artist_stats (
                        artist_id, detection_count,
                        last_detected, total_play_time,
                        average_confidence
                    ) VALUES (
                        :artist_id, 1,
                        :current_time, :play_duration,
                        :confidence
                    )
                    ON CONFLICT (artist_id) DO UPDATE SET
                        detection_count = artist_stats.detection_count + 1,
                        last_detected = :current_time,
                        total_play_time = COALESCE(artist_stats.total_play_time, '0 seconds'::interval) + :play_duration,
                        average_confidence = (
                            artist_stats.average_confidence * artist_stats.detection_count + :confidence
                        ) / (artist_stats.detection_count + 1)
                    RETURNING detection_count, average_confidence
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
                        total_play_time = COALESCE(station_track_stats.total_play_time, '0 seconds'::interval) + :play_duration,
                        last_played = :current_time,
                        average_confidence = (
                            station_track_stats.average_confidence * station_track_stats.play_count + :confidence
                        ) / (station_track_stats.play_count + 1)
                    RETURNING play_count, average_confidence
                )
                SELECT 
                    (SELECT detection_count FROM track_update) as track_count,
                    (SELECT detection_count FROM artist_update) as artist_count,
                    (SELECT play_count FROM station_update) as station_play_count;
            """), {
                'station_id': station_id,
                'track_id': track_id,
                'artist_id': artist_id,
                'confidence': confidence,
                'play_duration': play_duration,
                'current_time': current_time
            })

            stats = result.fetchone()
            self.logger.info("Stats update completed", extra={
                'track_detections': stats.track_count,
                'artist_detections': stats.artist_count,
                'station_plays': stats.station_play_count,
                'update_time': current_time.isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error updating detection stats: {str(e)}", exc_info=True)
            raise

    def _update_temporal_aggregates_efficient(self, station_id: int, track_id: int,
                                            artist_id: int, current_time: datetime,
                                            play_duration: timedelta):
        """Update all temporal aggregates using batch updates"""
        try:
            hour_start = current_time.replace(minute=0, second=0, microsecond=0)
            day_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            self.db_session.execute(text("""
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
                    total_play_time = COALESCE(artist_daily.total_play_time, '0 seconds'::interval) + :play_duration;
                
                -- Monthly artist stats
                INSERT INTO artist_monthly (artist_id, month, count, total_play_time)
                VALUES (:artist_id, :month_start, 1, :play_duration)
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

    def _update_analytics_data_efficient(self, confidence: float, current_time: datetime):
        """Update analytics data using window functions"""
        try:
            hour_ago = current_time - timedelta(hours=1)
            
            # Créer l'enregistrement horaire même s'il n'y a pas de détections
            self.db_session.execute(text("""
                INSERT INTO detection_hourly (hour, count)
                VALUES (date_trunc('hour', :current_time), 0)
                ON CONFLICT (hour) DO UPDATE SET
                    count = detection_hourly.count;
                    
                -- Créer ou mettre à jour les statistiques artiste
                INSERT INTO artist_stats (artist_id, detection_count, last_detected, total_play_time, average_confidence)
                SELECT 
                    a.id,
                    COALESCE(COUNT(td.id), 0),
                    MAX(td.detected_at),
                    COALESCE(SUM(td.play_duration), interval '0'),
                    COALESCE(AVG(td.confidence), 0)
                FROM artists a
                LEFT JOIN tracks t ON t.artist_id = a.id
                LEFT JOIN track_detections td ON td.track_id = t.id
                WHERE td.detected_at >= :hour_ago OR td.detected_at IS NULL
                GROUP BY a.id
                ON CONFLICT (artist_id) DO UPDATE SET
                    detection_count = EXCLUDED.detection_count,
                    last_detected = EXCLUDED.last_detected,
                    total_play_time = EXCLUDED.total_play_time,
                    average_confidence = EXCLUDED.average_confidence;
                    
                -- Créer ou mettre à jour les statistiques de pistes
                INSERT INTO track_stats (track_id, detection_count, average_confidence, last_detected, total_play_time)
                SELECT 
                    t.id,
                    COALESCE(COUNT(td.id), 0),
                    COALESCE(AVG(td.confidence), 0),
                    MAX(td.detected_at),
                    COALESCE(SUM(td.play_duration), interval '0')
                FROM tracks t
                LEFT JOIN track_detections td ON td.track_id = t.id
                WHERE td.detected_at >= :hour_ago OR td.detected_at IS NULL
                GROUP BY t.id
                ON CONFLICT (track_id) DO UPDATE SET
                    detection_count = EXCLUDED.detection_count,
                    average_confidence = EXCLUDED.average_confidence,
                    last_detected = EXCLUDED.last_detected,
                    total_play_time = EXCLUDED.total_play_time;
                    
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
                    COALESCE(COUNT(td.id)::float / NULLIF(COUNT(DISTINCT rs.id), 0), 0) as detection_rate,
                    COUNT(DISTINCT CASE WHEN td.detected_at >= :hour_ago THEN rs.id END) as active_stations,
                    COALESCE(AVG(td.confidence), 0) as avg_confidence,
                    :current_time as timestamp
                FROM radio_stations rs
                LEFT JOIN track_detections td ON td.station_id = rs.id AND td.detected_at >= :hour_ago;
            """), {
                'hour_ago': hour_ago,
                'current_time': current_time
            })
            
            self.logger.info("Analytics data updated successfully", extra={
                'timestamp': current_time.isoformat(),
                'update_type': 'analytics'
            })
            
        except Exception as e:
            self.logger.error(f"Error updating analytics data: {str(e)}", exc_info=True)
            raise

    def _update_station_status_efficient(self, station_id: int, current_time: datetime):
        """Update station status using efficient batch updates"""
        try:
            hour_ago = current_time - timedelta(hours=1)
            
            self.db_session.execute(text("""
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
                WHERE radio_stations.id = su.id;
            """), {
                'station_id': station_id,
                'current_time': current_time,
                'hour_ago': hour_ago
            })
            
        except Exception as e:
            self.logger.error(f"Error updating station status: {str(e)}", exc_info=True)
            raise

    async def verify_and_init_stats(self):
        """Vérifier et initialiser les données statistiques manquantes"""
        try:
            # Initialiser les détections horaires pour les dernières 24h
            self.db_session.execute(text("""
                INSERT INTO detection_hourly (hour, count)
                SELECT 
                    hour,
                    0 as count
                FROM generate_series(
                    date_trunc('hour', now() - interval '24 hours'),
                    date_trunc('hour', now()),
                    '1 hour'
                ) as hour
                ON CONFLICT (hour) DO NOTHING;
            """))

            # Initialiser les stats artistes manquantes
            self.db_session.execute(text("""
                INSERT INTO artist_stats (
                    artist_id, detection_count, average_confidence,
                    last_detected, total_play_time
                )
                SELECT 
                    a.id,
                    0,
                    0.0,
                    NULL,
                    interval '0'
                FROM artists a
                LEFT JOIN artist_stats ast ON ast.artist_id = a.id
                WHERE ast.artist_id IS NULL;
            """))

            # Initialiser les stats pistes manquantes
            self.db_session.execute(text("""
                INSERT INTO track_stats (
                    track_id, detection_count, average_confidence,
                    last_detected, total_play_time
                )
                SELECT 
                    t.id,
                    0,
                    0.0,
                    NULL,
                    interval '0'
                FROM tracks t
                LEFT JOIN track_stats ts ON ts.track_id = t.id
                WHERE ts.track_id IS NULL;
            """))

            # Mettre à jour les compteurs globaux
            self.db_session.execute(text("""
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
            """))

            self.db_session.commit()
            self.logger.info("Statistics initialization completed successfully")

        except Exception as e:
            self.logger.error(f"Error initializing statistics: {str(e)}")
            self.db_session.rollback()
            raise

    async def monitor_stats_health(self):
        """Surveiller la santé des statistiques"""
        try:
            results = self.db_session.execute(text("""
                SELECT
                    (SELECT COUNT(*) FROM artists WHERE id NOT IN (SELECT artist_id FROM artist_stats)) as missing_artist_stats,
                    (SELECT COUNT(*) FROM tracks WHERE id NOT IN (SELECT track_id FROM track_stats)) as missing_track_stats,
                    (SELECT COUNT(*) FROM detection_hourly WHERE hour >= now() - interval '24 hours') as hourly_records_24h
            """)).fetchone()

            if results.missing_artist_stats > 0 or results.missing_track_stats > 0:
                self.logger.warning("Missing statistics detected", extra={
                    'missing_artist_stats': results.missing_artist_stats,
                    'missing_track_stats': results.missing_track_stats,
                    'hourly_records_24h': results.hourly_records_24h
                })
                await self.verify_and_init_stats()
            
            return {
                'status': 'healthy' if all(x == 0 for x in results) else 'needs_attention',
                'missing_artist_stats': results.missing_artist_stats,
                'missing_track_stats': results.missing_track_stats,
                'hourly_records_24h': results.hourly_records_24h
            }

        except Exception as e:
            self.logger.error(f"Error monitoring stats health: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def initialize_missing_stats(self):
        """Initialize missing statistics data"""
        try:
            logger.info("Initializing missing statistics...")
            
            # Initialize hourly detection records for the last 24 hours
            self.db_session.execute(text("""
                INSERT INTO detection_hourly (hour, count)
                SELECT 
                    generate_series(
                        date_trunc('hour', now()) - interval '24 hours',
                        date_trunc('hour', now()),
                        '1 hour'
                    ) as hour,
                    0 as count
                ON CONFLICT (hour) DO NOTHING;
            """))

            # Initialize artist stats for all artists
            self.db_session.execute(text("""
                INSERT INTO artist_stats (
                    artist_id, detection_count, average_confidence,
                    last_detected, total_play_time
                )
                SELECT 
                    id as artist_id,
                    0 as detection_count,
                    0.0 as average_confidence,
                    NULL as last_detected,
                    interval '0' as total_play_time
                FROM artists a
                WHERE NOT EXISTS (
                    SELECT 1 FROM artist_stats ast WHERE ast.artist_id = a.id
                );
            """))

            # Initialize track stats for all tracks
            self.db_session.execute(text("""
                INSERT INTO track_stats (
                    track_id, detection_count, average_confidence,
                    last_detected, total_play_time
                )
                SELECT 
                    id as track_id,
                    0 as detection_count,
                    0.0 as average_confidence,
                    NULL as last_detected,
                    interval '0' as total_play_time
                FROM tracks t
                WHERE NOT EXISTS (
                    SELECT 1 FROM track_stats ts WHERE ts.track_id = t.id
                );
            """))

            # Initialize station stats
            self.db_session.execute(text("""
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
            """))

            self.db_session.commit()
            logger.info("Successfully initialized missing statistics")
            
        except Exception as e:
            logger.error(f"Error initializing statistics: {str(e)}")
            self.db_session.rollback()
            raise