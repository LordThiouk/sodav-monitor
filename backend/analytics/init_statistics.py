from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
import logging
from datetime import datetime, timedelta
import sys
sys.path.append('.')
from backend.models.database import get_database_url
from backend.models.models import (
    Artist, Track, TrackDetection, RadioStation,
    ArtistStats, TrackStats, StationTrackStats,
    DetectionHourly, DetectionDaily, DetectionMonthly,
    ArtistDaily, ArtistMonthly, TrackDaily, TrackMonthly,
    AnalyticsData
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StatisticsInitializer:
    """Class to initialize statistics tables based on existing detections"""
    
    def __init__(self, db_session: Session = None):
        """Initialize with an optional session, or create a new one if not provided"""
        self.session = db_session
        self._own_session = False
        
        if self.session is None:
            # Create a new session if none was provided
            database_url = get_database_url()
            engine = create_engine(database_url)
            Session = sessionmaker(bind=engine)
            self.session = Session()
            self._own_session = True
    
    def __del__(self):
        """Clean up resources if we created our own session"""
        if self._own_session and self.session:
            self.session.close()
    
    def initialize_all(self):
        """Initialize all statistics tables based on existing detections"""
        try:
            self._initialize_artist_stats()
            self._initialize_track_stats()
            self._initialize_station_track_stats()
            self._initialize_time_based_stats()
            self._initialize_analytics_data()
            
            self.session.commit()
            logger.info("\n✅ All statistics initialized successfully!")
            return True
        except Exception as e:
            logger.error(f"Error initializing statistics: {str(e)}")
            self.session.rollback()
            raise
    
    def _initialize_artist_stats(self):
        """Initialize artist statistics"""
        logger.info("Initializing artist statistics...")
        artists = self.session.query(Artist).all()
        for artist in artists:
            # Get all tracks for this artist
            tracks = self.session.query(Track).filter(Track.artist_id == artist.id).all()
            track_ids = [t.id for t in tracks]
            
            if track_ids:
                # Calculate statistics from detections
                stats = self.session.query(
                    func.count(TrackDetection.id).label('detection_count'),
                    func.max(TrackDetection.detected_at).label('last_detected'),
                    func.sum(TrackDetection.play_duration).label('total_play_time'),
                    func.avg(TrackDetection.confidence).label('average_confidence')
                ).filter(
                    TrackDetection.track_id.in_(track_ids)
                ).first()
                
                # Create or update artist stats
                artist_stats = ArtistStats(
                    artist_id=artist.id,
                    detection_count=stats.detection_count or 0,
                    last_detected=stats.last_detected,
                    total_play_time=stats.total_play_time or timedelta(0),
                    average_confidence=stats.average_confidence or 0.0
                )
                self.session.add(artist_stats)
                
                # Update artist totals
                artist.total_plays = stats.detection_count or 0
                artist.total_play_time = stats.total_play_time or timedelta(0)
                artist.updated_at = datetime.utcnow()
                
                logger.info(
                    f"Artist {artist.name}:\n"
                    f"  - Detections: {stats.detection_count}\n"
                    f"  - Total play time: {stats.total_play_time}\n"
                    f"  - Average confidence: {stats.average_confidence:.2f}%"
                )
    
    def _initialize_track_stats(self):
        """Initialize track statistics"""
        logger.info("\nInitializing track statistics...")
        tracks = self.session.query(Track).all()
        for track in tracks:
            # Calculate statistics from detections
            stats = self.session.query(
                func.count(TrackDetection.id).label('detection_count'),
                func.max(TrackDetection.detected_at).label('last_detected'),
                func.sum(TrackDetection.play_duration).label('total_play_time'),
                func.avg(TrackDetection.confidence).label('average_confidence')
            ).filter(
                TrackDetection.track_id == track.id
            ).first()
            
            # Create track stats
            track_stats = TrackStats(
                track_id=track.id,
                detection_count=stats.detection_count or 0,
                last_detected=stats.last_detected,
                total_play_time=stats.total_play_time or timedelta(0),
                average_confidence=stats.average_confidence or 0.0
            )
            self.session.add(track_stats)
            
            logger.info(
                f"Track {track.title}:\n"
                f"  - Detections: {stats.detection_count}\n"
                f"  - Total play time: {stats.total_play_time}\n"
                f"  - Average confidence: {stats.average_confidence:.2f}%"
            )
    
    def _initialize_station_track_stats(self):
        """Initialize station track statistics"""
        logger.info("\nInitializing station track statistics...")
        stations = self.session.query(RadioStation).all()
        for station in stations:
            # Get all detections for this station
            detections = self.session.query(
                TrackDetection.track_id,
                func.count(TrackDetection.id).label('play_count'),
                func.max(TrackDetection.detected_at).label('last_played'),
                func.sum(TrackDetection.play_duration).label('total_play_time'),
                func.avg(TrackDetection.confidence).label('average_confidence')
            ).filter(
                TrackDetection.station_id == station.id
            ).group_by(
                TrackDetection.track_id
            ).all()
            
            for track_id, count, last_played, play_time, confidence in detections:
                stats = StationTrackStats(
                    station_id=station.id,
                    track_id=track_id,
                    play_count=count,
                    last_played=last_played,
                    total_play_time=play_time or timedelta(0),
                    average_confidence=confidence or 0.0
                )
                self.session.add(stats)
                
                logger.info(
                    f"Station {station.name} - Track {track_id}:\n"
                    f"  - Plays: {count}\n"
                    f"  - Total play time: {play_time}\n"
                    f"  - Average confidence: {confidence:.2f}%"
                )
    
    def _initialize_time_based_stats(self):
        """Initialize time-based statistics"""
        logger.info("\nInitializing time-based statistics...")
        
        # Get all detection dates
        dates = self.session.query(
            func.date_trunc('hour', TrackDetection.detected_at).label('hour'),
            func.date_trunc('day', TrackDetection.detected_at).label('day'),
            func.date_trunc('month', TrackDetection.detected_at).label('month'),
            func.count(TrackDetection.id).label('count')
        ).group_by(
            'hour', 'day', 'month'
        ).all()
        
        for date in dates:
            # Hourly stats
            hourly = DetectionHourly(
                hour=date.hour,
                count=date.count
            )
            self.session.add(hourly)
            
            # Daily stats
            daily = DetectionDaily(
                date=date.day,
                count=date.count
            )
            self.session.add(daily)
            
            # Monthly stats
            monthly = DetectionMonthly(
                month=date.month,
                count=date.count
            )
            self.session.add(monthly)
        
        logger.info(f"Added time-based statistics for {len(dates)} time periods")
    
    def _initialize_analytics_data(self):
        """Initialize analytics data"""
        logger.info("\nInitializing analytics data...")
        
        # Calculate current analytics
        total_detections = self.session.query(func.count(TrackDetection.id)).scalar()
        active_stations = self.session.query(func.count(RadioStation.id)).filter(
            RadioStation.is_active == True
        ).scalar()
        avg_confidence = self.session.query(
            func.avg(TrackDetection.confidence)
        ).scalar()
        
        # Ensure avg_confidence is a valid float (not None)
        avg_confidence = float(avg_confidence) if avg_confidence is not None else 0.0
        
        # Calculate detection rate (per hour)
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        hourly_detections = self.session.query(
            func.count(TrackDetection.id)
        ).filter(
            TrackDetection.detected_at >= hour_ago
        ).scalar()
        
        analytics = AnalyticsData(
            detection_count=total_detections,
            detection_rate=hourly_detections,
            active_stations=active_stations,
            average_confidence=avg_confidence,
            timestamp=datetime.utcnow()
        )
        self.session.add(analytics)
        
        logger.info(
            f"Analytics Data:\n"
            f"  - Total detections: {total_detections}\n"
            f"  - Detection rate: {hourly_detections}/hour\n"
            f"  - Active stations: {active_stations}\n"
            f"  - Average confidence: {avg_confidence:.2f}%"
        )

# Keep the function for backward compatibility
def init_statistics():
    """Initialize all statistics tables based on existing detections"""
    initializer = StatisticsInitializer()
    try:
        return initializer.initialize_all()
    except Exception as e:
        logger.error(f"Failed to initialize statistics: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        init_statistics()
    except Exception as e:
        logger.error("Failed to initialize statistics")
        sys.exit(1) 