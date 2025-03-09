from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import logging
from models import Track, TrackDetection, Artist, RadioStation
from database import get_database_url

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_database():
    """Clean the database by removing non-Senegalese tracks and fixing duplicates"""
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # List of non-Senegalese tracks to remove
        non_senegalese_tracks = [
            "Show Me Who You Are",
            "Carinha de Safada",
            "Madrid City",
            "The Look in Your Eyes"
        ]

        # First get the IDs of non-Senegalese tracks
        track_ids = [t.id for t in session.query(Track.id).filter(Track.title.in_(non_senegalese_tracks)).all()]
        
        # Delete detections for these tracks
        if track_ids:
            detections_deleted = session.query(TrackDetection).filter(
                TrackDetection.track_id.in_(track_ids)
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {detections_deleted} detections for non-Senegalese tracks")

            # Delete the tracks themselves
            tracks_deleted = session.query(Track).filter(
                Track.id.in_(track_ids)
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {tracks_deleted} non-Senegalese tracks")

        # Remove non-Senegalese artists
        non_senegalese_artists = ["Mark Nevin", "Eo Mc Dolle Ta", "Ana Mena", "JR"]
        
        # First get tracks for these artists to delete their detections
        artist_track_ids = [t.id for t in session.query(Track.id).join(Artist).filter(
            Artist.name.in_(non_senegalese_artists)
        ).all()]
        
        if artist_track_ids:
            # Delete detections for these tracks
            detections_deleted = session.query(TrackDetection).filter(
                TrackDetection.track_id.in_(artist_track_ids)
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {detections_deleted} detections for tracks of non-Senegalese artists")
            
            # Delete the tracks
            tracks_deleted = session.query(Track).filter(
                Track.id.in_(artist_track_ids)
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {tracks_deleted} tracks of non-Senegalese artists")

        # Now delete the artists
        artists_deleted = session.query(Artist).filter(
            Artist.name.in_(non_senegalese_artists)
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {artists_deleted} non-Senegalese artists")

        # Find duplicate tracks
        duplicate_tracks = session.query(Track.title, Artist.id, func.count(Track.id).label('count'))\
            .group_by(Track.title, Artist.id)\
            .having(func.count(Track.id) > 1)\
            .all()

        for title, artist_id, count in duplicate_tracks:
            # Keep the oldest track and delete others
            tracks = session.query(Track)\
                .filter(Track.title == title, Track.artist_id == artist_id)\
                .order_by(Track.created_at)\
                .all()
            
            if len(tracks) > 1:
                # Get IDs of tracks to delete (all except the oldest)
                track_ids_to_delete = [t.id for t in tracks[1:]]
                
                # Delete detections for duplicate tracks
                detections_deleted = session.query(TrackDetection).filter(
                    TrackDetection.track_id.in_(track_ids_to_delete)
                ).delete(synchronize_session=False)
                logger.info(f"Deleted {detections_deleted} detections for duplicate track: {title}")
                
                # Delete duplicate tracks
                tracks_deleted = session.query(Track).filter(
                    Track.id.in_(track_ids_to_delete)
                ).delete(synchronize_session=False)
                logger.info(f"Deleted {tracks_deleted} duplicate tracks for: {title}")

        session.commit()
        logger.info("Database cleaned successfully")

    except Exception as e:
        session.rollback()
        logger.error(f"Error cleaning database: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    clean_database() 