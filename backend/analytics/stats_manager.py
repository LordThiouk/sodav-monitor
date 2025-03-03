from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from ..models.models import (
    Track, Artist, TrackDetection, RadioStation,
    StationTrackStats, ArtistStats, TrackStats, StationStats
)
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class StatsManager:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    async def update_detection_stats(self, detection: TrackDetection) -> None:
        """
        Met à jour les statistiques après chaque détection
        """
        try:
            # Mise à jour des stats du morceau
            track_stats = self.db_session.query(TrackStats).filter_by(track_id=detection.track_id).first()
            if not track_stats:
                track_stats = TrackStats(
                    track_id=detection.track_id,
                    total_plays=0,
                    total_play_time=timedelta(),
                    average_confidence=0.0,
                    last_detected=detection.detected_at
                )
                self.db_session.add(track_stats)
            
            track_stats.total_plays += 1
            track_stats.total_play_time += detection.play_duration
            track_stats.last_detected = detection.detected_at
            track_stats.average_confidence = (
                (track_stats.average_confidence * (track_stats.total_plays - 1) + detection.confidence)
                / track_stats.total_plays
            )

            # Mise à jour des stats de l'artiste
            if detection.track.artist_id:
                artist_stats = self.db_session.query(ArtistStats).filter_by(artist_id=detection.track.artist_id).first()
                if not artist_stats:
                    artist_stats = ArtistStats(
                        artist_id=detection.track.artist_id,
                        total_plays=0,
                        total_play_time=timedelta(),
                        last_detected=detection.detected_at
                    )
                    self.db_session.add(artist_stats)
                
                artist_stats.total_plays += 1
                artist_stats.total_play_time += detection.play_duration
                artist_stats.last_detected = detection.detected_at

            # Mise à jour des stats par station
            station_track_stats = self.db_session.query(StationTrackStats).filter_by(
                station_id=detection.station_id,
                track_id=detection.track_id
            ).first()
            
            if not station_track_stats:
                station_track_stats = StationTrackStats(
                    station_id=detection.station_id,
                    track_id=detection.track_id,
                    play_count=0,
                    total_play_time=timedelta(),
                    last_played=detection.detected_at,
                    average_confidence=0.0
                )
                self.db_session.add(station_track_stats)
            
            station_track_stats.play_count += 1
            station_track_stats.total_play_time += detection.play_duration
            station_track_stats.last_played = detection.detected_at
            station_track_stats.average_confidence = (
                (station_track_stats.average_confidence * (station_track_stats.play_count - 1) + detection.confidence)
                / station_track_stats.play_count
            )

            self.db_session.commit()
            logger.info(f"Updated stats for track {detection.track_id} on station {detection.station_id}")

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating detection stats: {str(e)}")
            raise

    async def generate_daily_report(self, date: Optional[datetime] = None) -> Dict:
        """
        Génère un rapport quotidien des statistiques
        """
        if not date:
            date = datetime.now()

        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)

        try:
            # Get total stations and active stations
            stations = self.db_session.query(
                func.count(RadioStation.id).label('total'),
                func.count(RadioStation.id).filter(RadioStation.status == 'active').label('active')
            ).first()

            # Get total detections and play time
            total_detections = self.db_session.query(func.count(TrackDetection.id)).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).scalar()

            total_play_time = self.db_session.query(func.sum(TrackDetection.play_duration)).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).scalar()

            # Get hourly detections
            hourly_detections = self.db_session.query(
                func.date_trunc('hour', TrackDetection.detected_at).label('hour'),
                func.count(TrackDetection.id).label('count')
            ).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).group_by('hour').order_by('hour').all()

            # Get top tracks
            top_tracks = self.db_session.query(
                Track,
                func.count(TrackDetection.id).label('plays'),
                func.sum(TrackDetection.play_duration).label('duration')
            ).select_from(Track).join(
                TrackDetection, Track.id == TrackDetection.track_id
            ).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).group_by(Track.id).order_by(desc('plays')).limit(10).all()

            # Get top artists
            top_artists = self.db_session.query(
                Artist,
                func.count(TrackDetection.id).label('plays')
            ).select_from(Artist).join(
                Track, Track.artist_id == Artist.id
            ).join(
                TrackDetection, TrackDetection.track_id == Track.id
            ).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).group_by(Artist.id).order_by(desc('plays')).limit(10).all()

            # Get top labels
            top_labels = self.db_session.query(
                Track.label,
                func.count(TrackDetection.id).label('plays')
            ).select_from(Track).join(
                TrackDetection, TrackDetection.track_id == Track.id
            ).filter(
                TrackDetection.detected_at.between(start_date, end_date),
                Track.label.isnot(None)
            ).group_by(Track.label).order_by(desc('plays')).limit(10).all()

            # Get top channels
            top_channels = self.db_session.query(
                RadioStation,
                func.count(TrackDetection.id).label('plays')
            ).select_from(RadioStation).join(
                TrackDetection, TrackDetection.station_id == RadioStation.id
            ).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).group_by(RadioStation.id).order_by(desc('plays')).limit(10).all()

            return {
                "total_stations": stations.total or 0,
                "active_stations": stations.active or 0,
                "total_detections": total_detections or 0,
                "total_play_time": str(total_play_time) if total_play_time else "0:00:00",
                "hourly_detections": [
                    (hour, count) for hour, count in hourly_detections
                ],
                "top_tracks": [
                    {
                        "title": track.title,
                        "artist": track.artist.name if track.artist else "Unknown",
                        "plays": plays,
                        "duration": str(duration) if duration else "0:00:00"
                    }
                    for track, plays, duration in top_tracks
                ],
                "top_artists": [
                    {
                        "name": artist.name,
                        "plays": plays
                    }
                    for artist, plays in top_artists
                ],
                "top_labels": [
                    {
                        "name": label or "Unknown",
                        "plays": plays
                    }
                    for label, plays in top_labels
                ],
                "top_channels": [
                    {
                        "name": station.name,
                        "country": station.country or "Unknown",
                        "language": station.language or "Unknown",
                        "plays": plays
                    }
                    for station, plays in top_channels
                ]
            }

        except Exception as e:
            logger.error(f"Error generating daily report: {str(e)}")
            raise

    async def get_trend_analysis(self, days: int = 7) -> Dict:
        """
        Analyse les tendances sur une période donnée
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        try:
            # Tendances des morceaux
            track_trends = self.db_session.query(
                Track,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(TrackDetection.play_duration).label('total_play_time')
            ).select_from(Track).join(
                TrackDetection, Track.id == TrackDetection.track_id
            ).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).group_by(Track.id).order_by(desc('detection_count')).limit(20).all()

            # Tendances des artistes
            artist_trends = self.db_session.query(
                Artist,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(TrackDetection.play_duration).label('total_play_time')
            ).select_from(Artist).join(
                Track, Track.artist_id == Artist.id
            ).join(
                TrackDetection, TrackDetection.track_id == Track.id
            ).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).group_by(Artist.id).order_by(desc('detection_count')).limit(20).all()

            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days
                },
                "track_trends": [{
                    "title": track.title,
                    "artist": track.artist.name if track.artist else "Unknown",
                    "detections": count,
                    "play_time": str(play_time)
                } for track, count, play_time in track_trends],
                "artist_trends": [{
                    "name": artist.name,
                    "detections": count,
                    "play_time": str(play_time)
                } for artist, count, play_time in artist_trends]
            }

        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            raise

    async def close(self):
        """Close the database session."""
        await self.db_session.close()

    async def get_all_station_stats(self) -> List[Dict]:
        """Get analytics data for all radio stations."""
        try:
            now = datetime.utcnow()
            yesterday = now - timedelta(days=1)
            
            stations = self.db_session.query(
                RadioStation,
                StationStats
            ).select_from(RadioStation).outerjoin(
                StationStats
            ).all()
            
            return [
                {
                    "id": station.id,
                    "name": station.name,
                    "status": station.status,
                    "country": station.country or "Unknown",
                    "language": station.language or "Unknown",
                    "detections24h": stats.detection_count if stats else 0,
                    "lastCheckTime": station.last_check.isoformat() if station.last_check else None
                }
                for station, stats in stations
            ]
        except Exception as e:
            logger.error(f"Error getting station stats: {str(e)}")
            raise

    async def get_all_artist_stats(self) -> List[Dict]:
        """Get analytics data for all artists."""
        try:
            artists = self.db_session.query(
                Artist,
                ArtistStats
            ).select_from(Artist).outerjoin(
                ArtistStats
            ).order_by(
                ArtistStats.total_plays.desc()
            ).all()
            
            return [
                {
                    "id": artist.id,
                    "artist": artist.name,
                    "country": artist.country or "Unknown",
                    "label": artist.label or "Unknown",
                    "detection_count": stats.total_plays if stats else 0,
                    "total_play_time": str(stats.total_play_time) if stats and stats.total_play_time else "0:00:00",
                    "average_confidence": stats.average_confidence if stats else 0.0,
                    "last_detected": stats.last_detected.isoformat() if stats and stats.last_detected else None
                }
                for artist, stats in artists
            ]
        except Exception as e:
            logger.error(f"Error getting artist stats: {str(e)}")
            raise

    async def get_all_track_stats(self) -> List[Dict]:
        """Get analytics data for all tracks."""
        try:
            tracks = self.db_session.query(
                Track,
                TrackStats
            ).select_from(Track).outerjoin(
                TrackStats
            ).order_by(
                TrackStats.total_plays.desc()
            ).all()
            
            return [
                {
                    "id": track.id,
                    "title": track.title,
                    "artist": track.artist.name if track.artist else "Unknown",
                    "detection_count": stats.total_plays if stats else 0,
                    "total_play_time": str(stats.total_play_time) if stats and stats.total_play_time else "0:00:00",
                    "average_confidence": stats.average_confidence if stats else 0.0,
                    "last_detected": stats.last_detected.isoformat() if stats and stats.last_detected else None
                }
                for track, stats in tracks
            ]
        except Exception as e:
            logger.error(f"Error getting track stats: {str(e)}")
            raise

    async def get_dashboard_stats(self, period: int) -> Dict:
        """Get analytics data for the dashboard."""
        try:
            if period <= 0:
                raise ValueError("Period must be positive")

            now = datetime.utcnow()
            start_date = now - timedelta(hours=period)

            # Get total detections
            total_detections = self.db_session.query(
                func.count(TrackDetection.id)
            ).filter(
                TrackDetection.detected_at > start_date
            ).scalar()

            # Get active stations
            active_stations = self.db_session.query(
                func.count(RadioStation.id)
            ).filter(
                RadioStation.status == "active"
            ).scalar()

            # Get average confidence
            avg_confidence = self.db_session.query(
                func.avg(TrackDetection.confidence)
            ).filter(
                TrackDetection.detected_at > start_date
            ).scalar() or 0.0

            # Get detections by hour
            hourly_detections = self.db_session.query(
                func.date_trunc('hour', TrackDetection.detected_at).label('hour'),
                func.count(TrackDetection.id).label('count')
            ).filter(
                TrackDetection.detected_at > start_date
            ).group_by('hour').order_by('hour').all()

            # Get top artists
            top_artists = self.db_session.query(
                Artist,
                func.count(TrackDetection.id).label('detection_count')
            ).select_from(Artist).join(
                Track, Track.artist_id == Artist.id
            ).join(
                TrackDetection, TrackDetection.track_id == Track.id
            ).filter(
                TrackDetection.detected_at > start_date
            ).group_by(Artist.id).order_by(
                desc('detection_count')
            ).limit(10).all()

            return {
                "totalDetections": total_detections,
                "detectionRate": total_detections / period if period > 0 else 0,
                "activeStations": active_stations,
                "averageConfidence": avg_confidence,
                "detectionsByHour": [
                    {
                        "hour": hour.strftime("%Y-%m-%dT%H:%M:%S"),
                        "count": count
                    }
                    for hour, count in hourly_detections
                ],
                "topArtists": [
                    {
                        "name": artist.name,
                        "detections": count
                    }
                    for artist, count in top_artists
                ],
                "systemHealth": {
                    "status": "healthy",
                    "uptime": period,
                    "lastError": None
                }
            }
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {str(e)}")
            raise

    async def get_track_stats(self, track_id: int) -> Dict:
        """Get statistics for a specific track."""
        try:
            track = self.db_session.query(Track).filter(Track.id == track_id).first()
            if not track:
                raise HTTPException(status_code=404, detail="Track not found")

            stats = self.db_session.query(TrackStats).filter(TrackStats.track_id == track_id).first()
            if not stats:
                return {
                    "id": track.id,
                    "title": track.title,
                    "artist": track.artist.name if track.artist else "Unknown",
                    "detection_count": 0,
                    "total_play_time": "0:00:00",
                    "average_confidence": 0.0,
                    "last_detected": None
                }

            return {
                "id": track.id,
                "title": track.title,
                "artist": track.artist.name if track.artist else "Unknown",
                "detection_count": stats.total_plays,
                "total_play_time": str(stats.total_play_time),
                "average_confidence": stats.average_confidence,
                "last_detected": stats.last_detected.isoformat() if stats.last_detected else None
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting track stats: {str(e)}")
            raise

    async def export_analytics(self, format: str = "json") -> List[Dict]:
        """Export analytics data in the specified format."""
        try:
            now = datetime.utcnow()
            yesterday = now - timedelta(days=1)

            # Get detections from the last 24 hours
            detections = self.db_session.query(
                TrackDetection
            ).filter(
                TrackDetection.detected_at > yesterday
            ).all()

            # Format the data
            return [
                {
                    "track_title": detection.track.title,
                    "artist": detection.track.artist.name if detection.track.artist else "Unknown",
                    "station": detection.station.name,
                    "detected_at": detection.detected_at.isoformat(),
                    "confidence": detection.confidence,
                    "play_duration": str(detection.play_duration) if detection.play_duration else "0:00:00"
                }
                for detection in detections
            ]
        except Exception as e:
            logger.error(f"Error exporting analytics: {str(e)}")
            raise 