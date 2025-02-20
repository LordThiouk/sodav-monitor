from sqlalchemy import create_engine, inspect, func
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime, timedelta
import sys
sys.path.append('.')
from database import get_database_url
from models import (
    Artist, Track, TrackDetection, RadioStation,
    ArtistStats, TrackStats, StationTrackStats,
    DetectionHourly, DetectionDaily, DetectionMonthly,
    ArtistDaily, ArtistMonthly, TrackDaily, TrackMonthly,
    AnalyticsData
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_all_tables():
    """Check data in all database tables"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Get inspector
            inspector = inspect(engine)
            
            # List all tables
            tables = inspector.get_table_names()
            logger.info(f"\nDatabase tables: {', '.join(tables)}")

            # 1. Check Artists
            artists = session.query(Artist).all()
            logger.info(f"\n=== Artists ({len(artists)}) ===")
            for artist in artists:
                logger.info(
                    f"Artist: {artist.name}\n"
                    f"  - Country: {artist.country or 'N/A'}\n"
                    f"  - Region: {artist.region or 'N/A'}\n"
                    f"  - Label: {artist.label or 'N/A'}\n"
                    f"  - Total plays: {artist.total_plays}\n"
                    f"  - Total play time: {artist.total_play_time}"
                )

            # 2. Check Tracks
            tracks = session.query(Track).all()
            logger.info(f"\n=== Tracks ({len(tracks)}) ===")
            for track in tracks:
                logger.info(
                    f"Track: {track.title}\n"
                    f"  - Artist ID: {track.artist_id}\n"
                    f"  - Play count: {track.play_count}\n"
                    f"  - Total play time: {track.total_play_time}\n"
                    f"  - Last played: {track.last_played}\n"
                    f"  - Created at: {track.created_at}"
                )

            # 3. Check Radio Stations
            stations = session.query(RadioStation).all()
            logger.info(f"\n=== Radio Stations ({len(stations)}) ===")
            for station in stations:
                logger.info(
                    f"Station: {station.name}\n"
                    f"  - URL: {station.stream_url}\n"
                    f"  - Status: {station.status}\n"
                    f"  - Region: {station.region}\n"
                    f"  - Language: {station.language}\n"
                    f"  - Last detection: {station.last_detection_time}\n"
                    f"  - Total play time: {station.total_play_time}"
                )

            # 4. Check Track Detections
            detections = session.query(TrackDetection).all()
            logger.info(f"\n=== Track Detections ({len(detections)}) ===")
            for detection in detections:
                logger.info(
                    f"Detection at {detection.detected_at}\n"
                    f"  - Track ID: {detection.track_id}\n"
                    f"  - Station ID: {detection.station_id}\n"
                    f"  - Confidence: {detection.confidence}%\n"
                    f"  - Duration: {detection.play_duration}"
                )

            # 5. Check Artist Stats
            artist_stats = session.query(ArtistStats).all()
            logger.info(f"\n=== Artist Statistics ({len(artist_stats)}) ===")
            for stat in artist_stats:
                logger.info(
                    f"Artist Stats (ID: {stat.artist_id})\n"
                    f"  - Detection count: {stat.detection_count}\n"
                    f"  - Last detected: {stat.last_detected}\n"
                    f"  - Total play time: {stat.total_play_time}\n"
                    f"  - Average confidence: {stat.average_confidence}%"
                )

            # 6. Check Track Stats
            track_stats = session.query(TrackStats).all()
            logger.info(f"\n=== Track Statistics ({len(track_stats)}) ===")
            for stat in track_stats:
                logger.info(
                    f"Track Stats (ID: {stat.track_id})\n"
                    f"  - Detection count: {stat.detection_count}\n"
                    f"  - Last detected: {stat.last_detected}\n"
                    f"  - Total play time: {stat.total_play_time}\n"
                    f"  - Average confidence: {stat.average_confidence}%"
                )

            # 7. Check Station Track Stats
            station_track_stats = session.query(StationTrackStats).all()
            logger.info(f"\n=== Station Track Statistics ({len(station_track_stats)}) ===")
            for stat in station_track_stats:
                logger.info(
                    f"Station-Track Stats (Station: {stat.station_id}, Track: {stat.track_id})\n"
                    f"  - Play count: {stat.play_count}\n"
                    f"  - Last played: {stat.last_played}\n"
                    f"  - Total play time: {stat.total_play_time}\n"
                    f"  - Average confidence: {stat.average_confidence}%"
                )

            # 8. Check Detection Hourly/Daily/Monthly
            hourly = session.query(func.count(DetectionHourly.id)).scalar()
            daily = session.query(func.count(DetectionDaily.id)).scalar()
            monthly = session.query(func.count(DetectionMonthly.id)).scalar()
            logger.info(
                f"\n=== Detection Time Aggregates ===\n"
                f"  - Hourly records: {hourly}\n"
                f"  - Daily records: {daily}\n"
                f"  - Monthly records: {monthly}"
            )

            # 9. Check Artist Daily/Monthly
            artist_daily = session.query(func.count(ArtistDaily.id)).scalar()
            artist_monthly = session.query(func.count(ArtistMonthly.id)).scalar()
            logger.info(
                f"\n=== Artist Time Aggregates ===\n"
                f"  - Daily records: {artist_daily}\n"
                f"  - Monthly records: {artist_monthly}"
            )

            # 10. Check Track Daily/Monthly
            track_daily = session.query(func.count(TrackDaily.id)).scalar()
            track_monthly = session.query(func.count(TrackMonthly.id)).scalar()
            logger.info(
                f"\n=== Track Time Aggregates ===\n"
                f"  - Daily records: {track_daily}\n"
                f"  - Monthly records: {track_monthly}"
            )

            # 11. Check Analytics Data
            analytics = session.query(AnalyticsData).order_by(
                AnalyticsData.timestamp.desc()
            ).first()
            if analytics:
                logger.info(
                    f"\n=== Latest Analytics Data ===\n"
                    f"  - Timestamp: {analytics.timestamp}\n"
                    f"  - Detection count: {analytics.detection_count}\n"
                    f"  - Detection rate: {analytics.detection_rate}/hour\n"
                    f"  - Active stations: {analytics.active_stations}\n"
                    f"  - Average confidence: {analytics.average_confidence}%"
                )

            logger.info("\nDatabase check completed successfully!")

        except Exception as e:
            logger.error(f"Error checking tables: {str(e)}")
            raise
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        check_all_tables()
    except Exception as e:
        logger.error("Failed to check database tables")
        sys.exit(1) 