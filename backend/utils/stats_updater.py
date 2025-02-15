from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from models import (
    RadioStation, Track, TrackDetection, StationTrackStats,
    TrackStats, ArtistStats, AnalyticsData, DetectionHourly,
    DetectionDaily, DetectionMonthly, StationStats, ArtistDaily,
    ArtistMonthly, TrackDaily, TrackMonthly
)
from utils.logging_config import setup_logging

logger = setup_logging(__name__)

class StatsUpdater:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logger

    def update_all_stats(self, detection_result: dict, station_id: int, track: Track, play_duration: timedelta):
        """Update all statistics after a successful detection"""
        success_stats = []
        try:
            self.logger.info("Starting stats update", extra={
                'station_id': station_id,
                'track_id': track.id if track else None,
                'duration': str(play_duration)
            })

            # 1. Update radio_station stats
            try:
                self._update_radio_station_stats(station_id, play_duration)
                success_stats.append('radio_station')
            except Exception as e:
                self.logger.error(f"Error updating radio station stats: {str(e)}", exc_info=True)
            
            # 2. Update track stats
            if track:
                try:
                    self._update_track_stats(track, detection_result, play_duration)
                    success_stats.append('track')
                except Exception as e:
                    self.logger.error(f"Error updating track stats: {str(e)}", exc_info=True)
                
                # 3. Update station_track_stats
                try:
                    self._update_station_track_stats(station_id, track.id, play_duration)
                    success_stats.append('station_track')
                except Exception as e:
                    self.logger.error(f"Error updating station track stats: {str(e)}", exc_info=True)
                
                # 4. Update track_stats
                try:
                    self._update_track_global_stats(track.id, detection_result['confidence'], play_duration)
                    success_stats.append('track_global')
                except Exception as e:
                    self.logger.error(f"Error updating track global stats: {str(e)}", exc_info=True)
                
                # 5. Update artist_stats
                try:
                    self._update_artist_stats(track.artist, play_duration)
                    success_stats.append('artist')
                except Exception as e:
                    self.logger.error(f"Error updating artist stats: {str(e)}", exc_info=True)
            
            # 6. Update analytics_data
            try:
                self._update_analytics_data(detection_result['confidence'])
                success_stats.append('analytics')
            except Exception as e:
                self.logger.error(f"Error updating analytics data: {str(e)}", exc_info=True)
            
            # 7. Update time-based detection stats
            try:
                self._update_time_based_stats()
                success_stats.append('time_based')
            except Exception as e:
                self.logger.error(f"Error updating time-based stats: {str(e)}", exc_info=True)
            
            # 8. Update station_stats
            try:
                self._update_station_stats(station_id, detection_result['confidence'])
                success_stats.append('station')
            except Exception as e:
                self.logger.error(f"Error updating station stats: {str(e)}", exc_info=True)
            
            # 9. Update daily and monthly stats
            if track:
                try:
                    self._update_periodic_stats(station_id, track)
                    success_stats.append('periodic')
                except Exception as e:
                    self.logger.error(f"Error updating periodic stats: {str(e)}", exc_info=True)
            
            self.db_session.commit()
            self.logger.info("Stats update completed", extra={
                'successful_updates': success_stats,
                'total_updates': len(success_stats)
            })
            
        except Exception as e:
            self.logger.error("Error in stats update", extra={
                'error': str(e),
                'successful_updates': success_stats
            }, exc_info=True)
            self.db_session.rollback()
            raise

    def _update_radio_station_stats(self, station_id: int, play_duration: timedelta):
        """Update radio station total play time"""
        try:
            station = self.db_session.query(RadioStation).get(station_id)
            if station:
                if not station.total_play_time:
                    station.total_play_time = timedelta(0)
                station.total_play_time += play_duration
                station.last_detection_time = datetime.now()
                self.logger.debug(f"Updated station {station_id} play time: +{play_duration}")
        except Exception as e:
            self.logger.error(f"Error updating radio station stats: {str(e)}")
            raise

    def _update_track_stats(self, track: Track, detection_result: dict, play_duration: timedelta):
        """Update track metadata and statistics"""
        try:
            # Update basic stats
            track.play_count += 1
            if not track.total_play_time:
                track.total_play_time = timedelta(0)
            track.total_play_time += play_duration
            track.last_played = datetime.now()
            
            # Update metadata if available
            updated_fields = []
            if 'isrc' in detection_result and not track.isrc:
                track.isrc = detection_result['isrc']
                updated_fields.append(f"ISRC: {track.isrc}")
                self.logger.info(f"Updated ISRC for track {track.title}: {track.isrc}")
            
            if 'label' in detection_result and not track.label:
                track.label = detection_result['label']
                updated_fields.append(f"Label: {track.label}")
                self.logger.info(f"Updated label for track {track.title}: {track.label}")
            
            # Update fingerprint if available
            if 'fingerprint' in detection_result and not track.fingerprint:
                track.fingerprint = detection_result['fingerprint']
                track.fingerprint_raw = detection_result.get('fingerprint_raw')
                updated_fields.append("Fingerprint")
            
            self.logger.info(
                f"Updated track {track.id} ({track.title}): "
                f"plays={track.play_count}, "
                f"duration={track.total_play_time}"
                + (f", Updated fields: {', '.join(updated_fields)}" if updated_fields else "")
            )
            
        except Exception as e:
            self.logger.error(f"Error updating track stats: {str(e)}", exc_info=True)
            raise

    def _update_station_track_stats(self, station_id: int, track_id: int, play_duration: timedelta):
        """Update station-specific track statistics"""
        try:
            stats = self.db_session.query(StationTrackStats).filter(
                StationTrackStats.station_id == station_id,
                StationTrackStats.track_id == track_id
            ).first()
            
            if not stats:
                stats = StationTrackStats(
                    station_id=station_id,
                    track_id=track_id,
                    play_count=1,
                    total_play_time=play_duration,
                    last_played=datetime.now()
                )
                self.db_session.add(stats)
            else:
                stats.play_count += 1
                if not stats.total_play_time:
                    stats.total_play_time = timedelta(0)
                stats.total_play_time += play_duration
                stats.last_played = datetime.now()
            
            self.logger.debug(f"Updated station-track stats: station={station_id}, track={track_id}")
        except Exception as e:
            self.logger.error(f"Error updating station track stats: {str(e)}")
            raise

    def _update_track_global_stats(self, track_id: int, confidence: float, play_duration: timedelta):
        """Update global track statistics"""
        try:
            stats = self.db_session.query(TrackStats).filter(
                TrackStats.track_id == track_id
            ).first()
            
            if not stats:
                self.logger.info(f"Creating new TrackStats for track_id {track_id}")
                stats = TrackStats(
                    track_id=track_id,
                    detection_count=1,
                    average_confidence=confidence,
                    last_detected=datetime.now(),
                    total_play_time=play_duration
                )
                self.db_session.add(stats)
            else:
                self.logger.info(f"Updating existing TrackStats for track_id {track_id}")
                stats.detection_count += 1
                stats.total_play_time = (stats.total_play_time or timedelta(0)) + play_duration
                # Update average confidence
                stats.average_confidence = (
                    (stats.average_confidence * (stats.detection_count - 1) + confidence)
                    / stats.detection_count
                )
                stats.last_detected = datetime.now()
            
            self.logger.debug(
                f"Track stats updated: track={track_id}, "
                f"detection_count={stats.detection_count}, "
                f"total_play_time={stats.total_play_time}, "
                f"confidence={stats.average_confidence:.2f}"
            )
            
        except Exception as e:
            self.logger.error(f"Error updating track global stats: {str(e)}", exc_info=True)
            raise

    def _update_artist_stats(self, artist: str, play_duration: timedelta):
        """Update artist statistics"""
        try:
            stats = self.db_session.query(ArtistStats).filter(
                ArtistStats.artist_name == artist
            ).first()
            
            if not stats:
                stats = ArtistStats(
                    artist_name=artist,
                    detection_count=1,
                    total_play_time=play_duration,
                    last_detected=datetime.now()
                )
                self.db_session.add(stats)
            else:
                stats.detection_count += 1
                if not stats.total_play_time:
                    stats.total_play_time = timedelta(0)
                stats.total_play_time += play_duration
                stats.last_detected = datetime.now()
            
            self.logger.debug(f"Updated artist stats: artist={artist}")
        except Exception as e:
            self.logger.error(f"Error updating artist stats: {str(e)}")
            raise

    def _update_analytics_data(self, confidence: float):
        """Update global analytics data"""
        try:
            analytics = self.db_session.query(AnalyticsData).first()
            if not analytics:
                analytics = AnalyticsData(
                    detection_count=1,
                    detection_rate=1.0,
                    active_stations=1,
                    average_confidence=confidence
                )
                self.db_session.add(analytics)
            else:
                analytics.detection_count += 1
                # Update active stations count
                active_stations = self.db_session.query(func.count(RadioStation.id)).filter(
                    RadioStation.is_active == True
                ).scalar()
                analytics.active_stations = active_stations
                # Update average confidence
                analytics.average_confidence = (
                    (analytics.average_confidence * (analytics.detection_count - 1) + confidence)
                    / analytics.detection_count
                )
                # Update detection rate (detections per hour)
                hour_ago = datetime.now() - timedelta(hours=1)
                hourly_detections = self.db_session.query(func.count(TrackDetection.id)).filter(
                    TrackDetection.detected_at >= hour_ago
                ).scalar()
                analytics.detection_rate = hourly_detections
            
            self.logger.debug("Updated analytics data")
        except Exception as e:
            self.logger.error(f"Error updating analytics data: {str(e)}")
            raise

    def _update_time_based_stats(self):
        """Update hourly, daily, and monthly detection statistics"""
        try:
            now = datetime.now()
            
            # Update hourly stats
            hour_start = now.replace(minute=0, second=0, microsecond=0)
            hourly = self.db_session.query(DetectionHourly).filter(
                DetectionHourly.hour == hour_start
            ).first()
            if not hourly:
                hourly = DetectionHourly(hour=hour_start, count=1)
                self.db_session.add(hourly)
            else:
                hourly.count += 1
            
            # Update daily stats
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            daily = self.db_session.query(DetectionDaily).filter(
                DetectionDaily.date == day_start
            ).first()
            if not daily:
                daily = DetectionDaily(date=day_start, count=1)
                self.db_session.add(daily)
            else:
                daily.count += 1
            
            # Update monthly stats
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly = self.db_session.query(DetectionMonthly).filter(
                DetectionMonthly.month == month_start
            ).first()
            if not monthly:
                monthly = DetectionMonthly(month=month_start, count=1)
                self.db_session.add(monthly)
            else:
                monthly.count += 1
            
            self.logger.debug("Updated time-based stats")
        except Exception as e:
            self.logger.error(f"Error updating time-based stats: {str(e)}")
            raise

    def _update_station_stats(self, station_id: int, confidence: float):
        """Update station statistics"""
        try:
            stats = self.db_session.query(StationStats).filter(
                StationStats.station_id == station_id
            ).first()
            
            if not stats:
                stats = StationStats(
                    station_id=station_id,
                    detection_count=1,
                    last_detected=datetime.now(),
                    average_confidence=confidence
                )
                self.db_session.add(stats)
            else:
                stats.detection_count += 1
                stats.last_detected = datetime.now()
                stats.average_confidence = (
                    (stats.average_confidence * (stats.detection_count - 1) + confidence)
                    / stats.detection_count
                )
            
            self.logger.debug(f"Updated station stats: station={station_id}")
        except Exception as e:
            self.logger.error(f"Error updating station stats: {str(e)}")
            raise

    def _update_periodic_stats(self, station_id: int, track: Track):
        """Update daily and monthly statistics for artists and tracks"""
        try:
            now = datetime.now()
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Update artist daily stats
            artist_daily = self.db_session.query(ArtistDaily).filter(
                ArtistDaily.artist_name == track.artist,
                ArtistDaily.date == day_start
            ).first()
            if not artist_daily:
                artist_daily = ArtistDaily(
                    artist_name=track.artist,
                    date=day_start,
                    count=1
                )
                self.db_session.add(artist_daily)
            else:
                artist_daily.count += 1
            
            # Update artist monthly stats
            artist_monthly = self.db_session.query(ArtistMonthly).filter(
                ArtistMonthly.artist_name == track.artist,
                ArtistMonthly.month == month_start
            ).first()
            if not artist_monthly:
                artist_monthly = ArtistMonthly(
                    artist_name=track.artist,
                    month=month_start,
                    count=1
                )
                self.db_session.add(artist_monthly)
            else:
                artist_monthly.count += 1
            
            # Update track daily stats
            track_daily = self.db_session.query(TrackDaily).filter(
                TrackDaily.track_id == track.id,
                TrackDaily.date == day_start
            ).first()
            if not track_daily:
                track_daily = TrackDaily(
                    track_id=track.id,
                    date=day_start,
                    count=1
                )
                self.db_session.add(track_daily)
            else:
                track_daily.count += 1
            
            # Update track monthly stats
            track_monthly = self.db_session.query(TrackMonthly).filter(
                TrackMonthly.track_id == track.id,
                TrackMonthly.month == month_start
            ).first()
            if not track_monthly:
                track_monthly = TrackMonthly(
                    track_id=track.id,
                    month=month_start,
                    count=1
                )
                self.db_session.add(track_monthly)
            else:
                track_monthly.count += 1
            
            self.logger.debug(f"Updated periodic stats for track={track.id}, artist={track.artist}")
        except Exception as e:
            self.logger.error(f"Error updating periodic stats: {str(e)}")
            raise 