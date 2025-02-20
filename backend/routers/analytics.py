from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, distinct
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel

from ..database import get_db
from ..models import Track, TrackDetection, RadioStation, ArtistStats, TrackStats, DetectionHourly, AnalyticsData, Artist, StationStatus

router = APIRouter(
    tags=["analytics"],
    responses={404: {"description": "Not found"}}
)

logger = logging.getLogger(__name__)

class ChartDataPoint(BaseModel):
    hour: str
    count: int

class TopTrack(BaseModel):
    rank: int
    title: str
    artist: str
    plays: int
    duration: str

class TopArtist(BaseModel):
    rank: int
    name: str
    plays: int

class TopLabel(BaseModel):
    rank: int
    name: str
    plays: int

class TopChannel(BaseModel):
    rank: int
    name: str
    country: str
    language: str
    plays: int

class SystemHealth(BaseModel):
    status: str
    uptime: float
    lastError: Optional[str] = None

class AnalyticsResponse(BaseModel):
    totalChannels: int
    activeStations: int
    totalPlays: int
    totalPlayTime: str
    playsData: List[ChartDataPoint]
    topTracks: List[TopTrack]
    topArtists: List[TopArtist]
    topLabels: List[TopLabel]
    topChannels: List[TopChannel]
    systemHealth: SystemHealth

@router.get(
    "/overview",
    response_model=AnalyticsResponse,
    summary="Get Analytics Overview",
    description="Returns an overview of system analytics including detection stats, top artists, tracks, labels, and channels"
)
def get_analytics_overview(db: Session = Depends(get_db)):
    try:
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        # Get fresh counts of total and active stations
        total_stations = db.query(func.count(RadioStation.id)).scalar() or 0
        
        # Get active stations (those marked as active)
        active_stations = db.query(func.count(RadioStation.id))\
            .filter(
                RadioStation.is_active == True,
                RadioStation.status == StationStatus.active
            ).scalar() or 0
            
        # Get or create analytics data
        analytics = db.query(AnalyticsData).order_by(desc(AnalyticsData.timestamp)).first()
        if not analytics:
            analytics = AnalyticsData(
                timestamp=now,
                detection_count=0,
                detection_rate=0.0,
                active_stations=0,
                average_confidence=0.0
            )
            db.add(analytics)
        
        # Update analytics with current active stations
        analytics.active_stations = active_stations
        analytics.timestamp = now
        db.commit()
        
        # Get hourly detections for the last 24 hours
        hourly_detections = db.query(DetectionHourly)\
            .filter(DetectionHourly.hour >= last_24h)\
            .order_by(DetectionHourly.hour)\
            .all()
            
        # If no hourly data exists, create empty data points
        if not hourly_detections:
            logger.info("No hourly detection data found, creating empty data points")
            hourly_detections = []
            for i in range(24):
                hour = now - timedelta(hours=23-i)
                hourly_detections.append(DetectionHourly(
                    hour=hour.replace(minute=0, second=0, microsecond=0),
                    count=0
                ))
        
        # Get top artists
        top_artists = db.query(Artist, ArtistStats)\
            .join(ArtistStats, Artist.id == ArtistStats.artist_id)\
            .order_by(desc(ArtistStats.detection_count))\
            .limit(10)\
            .all()
            
        if not top_artists:
            logger.info("No artist stats found")
            top_artists = []
        
        # Get top tracks
        top_tracks = db.query(Track, TrackStats)\
            .join(TrackStats)\
            .order_by(desc(TrackStats.detection_count))\
            .limit(10)\
            .all()
            
        if not top_tracks:
            logger.info("No track stats found")
            top_tracks = []
            
        # Get top labels
        top_labels = db.query(
            Track.label,
            func.count(TrackDetection.id).label('detection_count')
        ).join(
            TrackDetection,
            Track.id == TrackDetection.track_id
        ).filter(
            Track.label.isnot(None),
            TrackDetection.detected_at >= last_24h
        ).group_by(
            Track.label
        ).order_by(
            desc('detection_count')
        ).limit(10).all()
        
        # Get top channels
        top_channels = db.query(
            RadioStation,
            func.count(TrackDetection.id).label('detection_count')
        ).join(
            TrackDetection,
            RadioStation.id == TrackDetection.station_id
        ).filter(
            TrackDetection.detected_at >= last_24h
        ).group_by(
            RadioStation.id
        ).order_by(
            desc('detection_count')
        ).limit(10).all()
        
        # Get system health
        try:
            system_health = {
                "status": "healthy" if active_stations > 0 else "warning",
                "uptime": 100.0 * (active_stations / total_stations if total_stations > 0 else 0),
                "lastError": None
            }
        except Exception as e:
            logger.error(f"Error getting system health: {str(e)}")
            system_health = {
                "status": "error",
                "uptime": 0,
                "lastError": str(e)
            }
        
        # Get total play time from all detections
        total_play_time = db.query(func.coalesce(func.sum(TrackDetection.play_duration), timedelta(0))).scalar() or timedelta(0)
        
        # Format response
        response = {
            "totalChannels": total_stations,
            "activeStations": active_stations,
            "totalPlays": analytics.detection_count,
            "totalPlayTime": f"{int(total_play_time.total_seconds() // 3600):01d}:{int((total_play_time.total_seconds() % 3600) // 60):02d}:{int(total_play_time.total_seconds() % 60):02d}",
            "playsData": [
                ChartDataPoint(
                    hour=detection.hour.isoformat(),
                    count=detection.count
                ).dict()
                for detection in hourly_detections
            ],
            "topArtists": [
                {
                    "rank": i + 1,
                    "name": artist.name,
                    "plays": stats.detection_count or 0
                }
                for i, (artist, stats) in enumerate(top_artists)
                if artist is not None
            ],
            "topTracks": [
                TopTrack(
                    rank=idx + 1,
                    title=track.title,
                    artist=track.artist.name,
                    plays=stats.detection_count,
                    duration=f"{int(stats.total_play_time.total_seconds() // 3600):01d}:{int((stats.total_play_time.total_seconds() % 3600) // 60):02d}:{int(stats.total_play_time.total_seconds() % 60):02d}" if stats.total_play_time else "0:00:00"
                ).dict()
                for idx, (track, stats) in enumerate(top_tracks)
            ],
            "topLabels": [
                TopLabel(
                    rank=idx + 1,
                    name=label or "Unknown",
                    plays=count
                ).dict()
                for idx, (label, count) in enumerate(top_labels)
            ],
            "topChannels": [
                TopChannel(
                    rank=idx + 1,
                    name=station.name,
                    country=station.country or "Unknown",
                    language=station.language or "Unknown",
                    plays=count
                ).dict()
                for idx, (station, count) in enumerate(top_channels)
            ],
            "systemHealth": SystemHealth(
                status="healthy" if active_stations > 0 else "warning",
                uptime=100.0 * (active_stations / total_stations if total_stations > 0 else 0),
                lastError=None
            ).dict()
        }
        
        logger.info("Successfully retrieved analytics overview")
        return response
        
    except Exception as e:
        logger.error(f"Error in analytics overview: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving analytics data: {str(e)}"
        )

@router.get(
    "/stations",
    response_model=List[Dict],
    summary="Get Station Analytics",
    description="Returns analytics data for all radio stations"
)
async def get_station_analytics(db: Session = Depends(get_db)):
    """
    Get analytics data for radio stations including:
    - Station status
    - Detection counts
    - Last check and detection times
    """
    try:
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        
        logger.info("Fetching station analytics data")
        
        # Get station analytics with error handling
        try:
            stations = db.query(
                RadioStation,
                func.count(TrackDetection.id).label('detection_count')
            ).outerjoin(
                TrackDetection,
                TrackDetection.detected_at > yesterday
            ).group_by(RadioStation.id).all()
        except Exception as e:
            logger.error(f"Error getting station analytics: {str(e)}")
            stations = []
        
        return [
            {
                "id": station.id,
                "name": station.name,
                "status": station.status.value if station.status else "inactive",
                "country": station.country or "Unknown",
                "language": station.language or "Unknown",
                "detections24h": detection_count,
                "lastCheckTime": station.last_checked.isoformat() if station.last_checked else None
            }
            for station, detection_count in stations
        ]
        
    except Exception as e:
        logger.error(f"Error in station analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving station analytics: {str(e)}"
        )

@router.get(
    "/artists",
    response_model=List[Dict],
    summary="Get Artist Analytics",
    description="Returns detailed analytics data for all artists"
)
async def get_artist_analytics(db: Session = Depends(get_db)):
    """
    Get detailed artist analytics including:
    - Detection counts
    - Total play time
    - Unique tracks, albums, labels, and stations
    """
    try:
        logger.info("Fetching artist analytics data")
        
        # Get artist analytics with error handling
        try:
            artist_stats = db.query(
                Artist,
                ArtistStats,
                func.count(distinct(Track.id)).label('unique_tracks'),
                func.count(distinct(Track.album)).label('unique_albums'),
                func.count(distinct(Track.label)).label('unique_labels'),
                func.count(distinct(TrackDetection.station_id)).label('unique_stations'),
                func.sum(TrackDetection.play_duration).label('total_play_time')
            ).join(
                ArtistStats,
                Artist.id == ArtistStats.artist_id
            ).join(
                Track,
                Artist.id == Track.artist_id
            ).join(
                TrackDetection,
                Track.id == TrackDetection.track_id
            ).group_by(
                Artist.id,
                ArtistStats.id
            ).order_by(
                desc(ArtistStats.detection_count)
            ).all()
        except Exception as e:
            logger.error(f"Error getting artist analytics: {str(e)}")
            artist_stats = []
        
        return [
            {
                "artist": artist.name,
                "detection_count": stats.detection_count,
                "total_play_time": f"{int(total_play_time.total_seconds() // 3600):01d}:{int((total_play_time.total_seconds() % 3600) // 60):02d}:{int(total_play_time.total_seconds() % 60):02d}" if total_play_time else "0:00:00",
                "unique_tracks": unique_tracks,
                "unique_albums": unique_albums,
                "unique_labels": unique_labels,
                "unique_stations": unique_stations
            }
            for artist, stats, unique_tracks, unique_albums, unique_labels, unique_stations, total_play_time in artist_stats
        ]
        
    except Exception as e:
        logger.error(f"Error in artist analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving artist analytics: {str(e)}"
        )

@router.get(
    "/tracks",
    response_model=List[Dict],
    summary="Get Track Analytics",
    description="Returns detailed analytics data for all tracks"
)
async def get_track_analytics(db: Session = Depends(get_db)):
    """
    Get detailed track analytics including:
    - Play counts
    - Average confidence
    - Last detection time
    """
    try:
        logger.info("Fetching track analytics data")
        
        # Get track analytics with error handling
        try:
            track_stats = db.query(Track, TrackStats).join(
                TrackStats
            ).order_by(
                TrackStats.detection_count.desc()
            ).all()
        except Exception as e:
            logger.error(f"Error getting track analytics: {str(e)}")
            track_stats = []
        
        return [
            {
                "id": track.id,
                "title": track.title,
                "artist": track.artist.name if track.artist else "Unknown",
                "album": track.album or "-",
                "label": track.label or "-",
                "isrc": track.isrc or "-",
                "detection_count": stats.detection_count,
                "total_play_time": f"{int(stats.total_play_time.total_seconds() // 3600):01d}:{int((stats.total_play_time.total_seconds() % 3600) // 60):02d}:{int(stats.total_play_time.total_seconds() % 60):02d}" if stats.total_play_time else "0:00:00",
                "unique_stations": len(set(d.station_id for d in track.detections))
            }
            for track, stats in track_stats
        ]
        
    except Exception as e:
        logger.error(f"Error in track analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving track analytics: {str(e)}"
        )

def update_hourly_stats(db: Session):
    """Update hourly detection statistics"""
    try:
        now = datetime.utcnow()
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        
        # Get detections for the current hour
        try:
            detections = db.query(TrackDetection).filter(
                TrackDetection.detected_at >= current_hour
            ).count()
        except Exception as e:
            logger.error(f"Error getting hourly detections: {str(e)}")
            detections = 0
        
        # Update or create hourly record
        try:
            hourly_stat = db.query(DetectionHourly).filter(
                DetectionHourly.hour == current_hour
            ).first()
            
            if hourly_stat:
                hourly_stat.count = detections
            else:
                hourly_stat = DetectionHourly(hour=current_hour, count=detections)
                db.add(hourly_stat)
        except Exception as e:
            logger.error(f"Error updating hourly stats: {str(e)}")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error in hourly stats update: {str(e)}", exc_info=True)

def update_artist_stats(db: Session):
    """Update artist detection statistics"""
    try:
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        
        # Get recent detections grouped by artist
        try:
            artist_detections = db.query(
                Track.artist_id,
                func.count(TrackDetection.id).label('detection_count'),
                func.max(TrackDetection.detected_at).label('last_detected')
            ).join(TrackDetection).filter(
                TrackDetection.detected_at >= yesterday
            ).group_by(Track.artist_id).all()
        except Exception as e:
            logger.error(f"Error getting artist detections: {str(e)}")
            artist_detections = []
        
        # Update artist stats
        for artist_id, count, last_detected in artist_detections:
            try:
                artist_stat = db.query(ArtistStats).filter(
                    ArtistStats.artist_id == artist_id
                ).first()
                
                if artist_stat:
                    artist_stat.detection_count = count
                    artist_stat.last_detected = last_detected
                else:
                    artist_stat = ArtistStats(
                        artist_id=artist_id,
                        detection_count=count,
                        last_detected=last_detected
                    )
                    db.add(artist_stat)
            except Exception as e:
                logger.error(f"Error updating artist stats: {str(e)}")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error in artist stats update: {str(e)}", exc_info=True)

def update_track_stats(db: Session):
    """Update track detection statistics"""
    try:
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        
        # Get recent detections grouped by track
        try:
            track_detections = db.query(
                Track.id,
                func.count(TrackDetection.id).label('detection_count'),
                func.max(TrackDetection.detected_at).label('last_detected'),
                func.avg(TrackDetection.confidence).label('average_confidence')
            ).join(TrackDetection).filter(
                TrackDetection.detected_at >= yesterday
            ).group_by(Track.id).all()
        except Exception as e:
            logger.error(f"Error getting track detections: {str(e)}")
            track_detections = []
        
        # Update track stats
        for track_id, count, last_detected, avg_confidence in track_detections:
            try:
                track_stat = db.query(TrackStats).filter(
                    TrackStats.track_id == track_id
                ).first()
                
                if track_stat:
                    track_stat.detection_count = count
                    track_stat.last_detected = last_detected
                    track_stat.average_confidence = avg_confidence
                else:
                    track_stat = TrackStats(
                        track_id=track_id,
                        detection_count=count,
                        last_detected=last_detected,
                        average_confidence=avg_confidence
                    )
                    db.add(track_stat)
            except Exception as e:
                logger.error(f"Error updating track stats: {str(e)}")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error in track stats update: {str(e)}", exc_info=True)
