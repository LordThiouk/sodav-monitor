from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime, timedelta
import sys
sys.path.append('..')
from database import get_database_url
from models import Base, Track, Artist, ArtistStats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_database_state():
    """Verify the state of the database after migration"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # 1. Check artists table
            artist_count = session.execute(text("SELECT COUNT(*) FROM artists")).scalar()
            logger.info(f"Found {artist_count} artists in database")
            
            # 2. Check tracks with artist_id
            tracks_with_artist = session.execute(text("""
                SELECT COUNT(*) 
                FROM tracks 
                WHERE artist_id IS NOT NULL
            """)).scalar()
            logger.info(f"Found {tracks_with_artist} tracks with artist_id")
            
            # 3. Check for tracks without artist_id
            tracks_without_artist = session.execute(text("""
                SELECT COUNT(*) 
                FROM tracks 
                WHERE artist_id IS NULL
            """)).scalar()
            if tracks_without_artist > 0:
                logger.warning(f"Found {tracks_without_artist} tracks without artist_id")
            
            # 4. Check artist statistics
            artist_stats = session.execute(text("""
                SELECT 
                    a.id,
                    a.name,
                    a.total_plays,
                    COUNT(t.id) as track_count,
                    a.total_play_time,
                    SUM(t.total_play_time) as actual_play_time
                FROM artists a
                LEFT JOIN tracks t ON a.id = t.artist_id
                GROUP BY a.id, a.name, a.total_plays, a.total_play_time
                ORDER BY track_count DESC
                LIMIT 10
            """)).fetchall()
            
            logger.info("\nTop 10 artists by track count:")
            for artist in artist_stats:
                logger.info(
                    f"Artist: {artist[1]}\n"
                    f"  - Tracks: {artist[3]}\n"
                    f"  - Total plays: {artist[2]}\n"
                    f"  - Total play time: {artist[4]}\n"
                )
            
            # 5. Check for temporary columns
            temp_columns = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tracks' 
                AND (column_name = 'temp_artist_name' OR column_name = 'artist')
            """)).fetchall()
            
            if temp_columns:
                logger.warning(f"Found temporary columns: {[col[0] for col in temp_columns]}")
            
            # 6. Check foreign key constraints
            fk_violations = session.execute(text("""
                SELECT COUNT(*) 
                FROM tracks t
                LEFT JOIN artists a ON t.artist_id = a.id
                WHERE t.artist_id IS NOT NULL 
                AND a.id IS NULL
            """)).scalar()
            
            if fk_violations > 0:
                logger.error(f"Found {fk_violations} tracks with invalid artist_id references")
            else:
                logger.info("No foreign key violations found")
            
            # 7. Check artist stats consistency
            stats_inconsistencies = session.execute(text("""
                SELECT 
                    a.id,
                    a.name,
                    a.total_plays,
                    COUNT(t.id) as actual_count
                FROM artists a
                LEFT JOIN tracks t ON a.id = t.artist_id
                GROUP BY a.id, a.name, a.total_plays
                HAVING a.total_plays != COUNT(t.id)
            """)).fetchall()
            
            if stats_inconsistencies:
                logger.warning(f"Found {len(stats_inconsistencies)} artists with inconsistent statistics:")
                for artist in stats_inconsistencies:
                    logger.warning(
                        f"Artist {artist[1]} (ID: {artist[0]}):\n"
                        f"  - Stored plays: {artist[2]}\n"
                        f"  - Actual tracks: {artist[3]}"
                    )
            else:
                logger.info("Artist statistics are consistent")
            
            logger.info("\nVerification completed!")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}")
        raise

if __name__ == "__main__":
    verify_database_state() 