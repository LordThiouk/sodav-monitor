from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from ..models.models import Track, Artist, TrackDetection, RadioStation, StationTrackStats, ArtistStats, TrackStats
import logging

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
                    detection_count=0,
                    total_play_time=timedelta(),
                    average_confidence=0.0,
                    last_detected=detection.detected_at
                )
                self.db_session.add(track_stats)
            
            track_stats.detection_count += 1
            track_stats.total_play_time += detection.play_duration
            track_stats.last_detected = detection.detected_at
            track_stats.average_confidence = (
                (track_stats.average_confidence * (track_stats.detection_count - 1) + detection.confidence)
                / track_stats.detection_count
            )

            # Mise à jour des stats de l'artiste
            if detection.track.artist_id:
                artist_stats = self.db_session.query(ArtistStats).filter_by(artist_id=detection.track.artist_id).first()
                if not artist_stats:
                    artist_stats = ArtistStats(
                        artist_id=detection.track.artist_id,
                        detection_count=0,
                        total_play_time=timedelta(),
                        last_detected=detection.detected_at
                    )
                    self.db_session.add(artist_stats)
                
                artist_stats.detection_count += 1
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
            # Statistiques globales
            total_detections = self.db_session.query(func.count(TrackDetection.id)).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).scalar()

            total_play_time = self.db_session.query(func.sum(TrackDetection.play_duration)).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).scalar()

            # Top morceaux
            top_tracks = self.db_session.query(
                Track,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(TrackDetection.play_duration).label('total_play_time')
            ).join(TrackDetection).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).group_by(Track.id).order_by(desc('detection_count')).limit(10).all()

            # Top artistes
            top_artists = self.db_session.query(
                Artist,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(TrackDetection.play_duration).label('total_play_time')
            ).join(Track).join(TrackDetection).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).group_by(Artist.id).order_by(desc('detection_count')).limit(10).all()

            # Statistiques par station
            station_stats = self.db_session.query(
                RadioStation,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(TrackDetection.play_duration).label('total_play_time')
            ).join(TrackDetection).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).group_by(RadioStation.id).all()

            return {
                "date": start_date.date().isoformat(),
                "total_detections": total_detections,
                "total_play_time": str(total_play_time) if total_play_time else "0:00:00",
                "top_tracks": [{
                    "title": track.title,
                    "artist": track.artist.name if track.artist else "Unknown",
                    "detections": count,
                    "play_time": str(play_time)
                } for track, count, play_time in top_tracks],
                "top_artists": [{
                    "name": artist.name,
                    "detections": count,
                    "play_time": str(play_time)
                } for artist, count, play_time in top_artists],
                "station_stats": [{
                    "name": station.name,
                    "detections": count,
                    "play_time": str(play_time)
                } for station, count, play_time in station_stats]
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
            ).join(TrackDetection).filter(
                TrackDetection.detected_at.between(start_date, end_date)
            ).group_by(Track.id).order_by(desc('detection_count')).limit(20).all()

            # Tendances des artistes
            artist_trends = self.db_session.query(
                Artist,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(TrackDetection.play_duration).label('total_play_time')
            ).join(Track).join(TrackDetection).filter(
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