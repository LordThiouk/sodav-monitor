import logging
import sys
from datetime import datetime, timedelta

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

sys.path.append("..")
from database import get_database_url
from models import Artist, ArtistDaily, ArtistMonthly, ArtistStats, Base, Track

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def table_exists(engine, table_name):
    """Check if a table exists in the database"""
    return inspect(engine).has_table(table_name)


def column_exists(engine, table_name, column_name):
    """Check if a column exists in a table"""
    for col in inspect(engine).get_columns(table_name):
        if col["name"] == column_name:
            return True
    return False


def create_artists_table(engine, session):
    """Create the artists table if it doesn't exist"""
    try:
        if not table_exists(engine, "artists"):
            logger.info("Creating artists table...")
            Base.metadata.tables["artists"].create(engine)
            logger.info("Artists table created successfully")
            return True
        else:
            logger.info("Artists table already exists")
            # Add label column if it doesn't exist
            if not column_exists(engine, "artists", "label"):
                logger.info("Adding label column to artists table...")
                session.execute(
                    text(
                        """
                    ALTER TABLE artists
                    ADD COLUMN IF NOT EXISTS label VARCHAR;
                    CREATE INDEX IF NOT EXISTS idx_artist_label ON artists (label);
                """
                    )
                )
                session.commit()
                logger.info("Label column added successfully")
            return True
    except Exception as e:
        logger.error(f"Error creating artists table: {str(e)}")
        session.rollback()
        return False


def prepare_artist_stats_table(session):
    """Prepare the artist_stats table for PostgreSQL"""
    try:
        # Drop existing table if it exists
        session.execute(text("DROP TABLE IF EXISTS artist_stats CASCADE"))
        session.commit()

        logger.info("Creating artist_stats table...")
        # Create new table with correct structure
        session.execute(
            text(
                """
            CREATE TABLE artist_stats (
                id SERIAL PRIMARY KEY,
                artist_id INTEGER,
                detection_count INTEGER DEFAULT 0,
                last_detected TIMESTAMP,
                total_play_time INTERVAL DEFAULT '0 seconds',
                average_confidence FLOAT DEFAULT 0.0
            )
        """
            )
        )

        # Add foreign key constraint
        session.execute(
            text(
                """
            ALTER TABLE artist_stats
            ADD CONSTRAINT fk_artist_stats_artist
            FOREIGN KEY (artist_id)
            REFERENCES artists(id);

            ALTER TABLE artist_stats
            ADD CONSTRAINT unique_artist_id
            UNIQUE (artist_id);

            CREATE INDEX idx_artist_stats_artist_id
            ON artist_stats(artist_id);
        """
            )
        )

        session.commit()
        logger.info("Artist stats table created successfully")
        return True
    except Exception as e:
        logger.error(f"Error preparing artist_stats table: {str(e)}")
        session.rollback()
        return False


def prepare_tracks_table(session):
    """Prepare the tracks table for migration"""
    try:
        # Add artist_id column
        session.execute(
            text(
                """
            ALTER TABLE tracks
            ADD COLUMN IF NOT EXISTS artist_id INTEGER REFERENCES artists(id);
        """
            )
        )

        # Add temporary column
        session.execute(
            text(
                """
            ALTER TABLE tracks
            ADD COLUMN IF NOT EXISTS temp_artist_name VARCHAR;
        """
            )
        )

        # Copy artist names
        session.execute(
            text(
                """
            UPDATE tracks
            SET temp_artist_name = artist
            WHERE artist IS NOT NULL
            AND temp_artist_name IS NULL;
        """
            )
        )

        session.commit()
        logger.info("Tracks table prepared successfully")
        return True
    except Exception as e:
        logger.error(f"Error preparing tracks table: {str(e)}")
        session.rollback()
        return False


def create_artists(session):
    """Create artist entries from unique artist names"""
    try:
        # Get unique artists and their labels from tracks
        unique_artists = session.execute(
            text(
                """
                SELECT DISTINCT artist, label
                FROM tracks
                WHERE artist IS NOT NULL
                GROUP BY artist, label
            """
            )
        ).fetchall()

        artist_mapping = {}

        for artist_row in tqdm(unique_artists, desc="Creating artists"):
            artist_name = artist_row[0]
            artist_label = artist_row[1]

            # Check if artist exists
            existing_artist = session.execute(
                text("SELECT id FROM artists WHERE name = :name"), {"name": artist_name}
            ).first()

            if existing_artist:
                artist_mapping[artist_name] = existing_artist[0]
                # Update label if not set
                if artist_label:
                    session.execute(
                        text(
                            """
                            UPDATE artists
                            SET label = :label
                            WHERE id = :id AND label IS NULL
                        """
                        ),
                        {"id": existing_artist[0], "label": artist_label},
                    )
                continue

            # Create new artist
            artist = Artist(
                name=artist_name,
                label=artist_label,
                created_at=datetime.utcnow(),
                total_play_time=timedelta(0),
                total_plays=0,
            )
            session.add(artist)
            session.flush()
            artist_mapping[artist_name] = artist.id

        session.commit()
        logger.info(f"Created {len(artist_mapping)} artists")
        return artist_mapping
    except Exception as e:
        logger.error(f"Error creating artists: {str(e)}")
        session.rollback()
        return None


def update_track_references(session, artist_mapping):
    """Update track references to use artist_id"""
    try:
        for artist_name, artist_id in tqdm(artist_mapping.items(), desc="Updating tracks"):
            session.execute(
                text("UPDATE tracks SET artist_id = :artist_id WHERE artist = :artist_name"),
                {"artist_id": artist_id, "artist_name": artist_name},
            )

        session.commit()
        logger.info("Track references updated successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating track references: {str(e)}")
        session.rollback()
        return False


def update_artist_statistics(session, artist_mapping):
    """Update artist statistics"""
    try:
        # Get artist totals
        artist_totals = session.execute(
            text(
                """
            SELECT
                artist,
                COUNT(*) as play_count,
                SUM(COALESCE(total_play_time, '0 seconds'::interval)) as total_play_time
            FROM tracks
            WHERE artist IS NOT NULL
            GROUP BY artist
        """
            )
        ).fetchall()

        for artist_name, play_count, total_play_time in tqdm(
            artist_totals, desc="Updating statistics"
        ):
            artist_id = artist_mapping.get(artist_name)
            if artist_id:
                session.execute(
                    text(
                        """
                        UPDATE artists
                        SET total_plays = :play_count,
                            total_play_time = :total_play_time
                        WHERE id = :artist_id
                    """
                    ),
                    {
                        "artist_id": artist_id,
                        "play_count": play_count,
                        "total_play_time": total_play_time,
                    },
                )

        session.commit()
        logger.info("Artist statistics updated successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating artist statistics: {str(e)}")
        session.rollback()
        return False


def verify_migration(session):
    """Verify the migration was successful"""
    try:
        # Check for invalid tracks
        invalid_tracks = session.execute(
            text("SELECT COUNT(*) FROM tracks WHERE artist IS NOT NULL AND artist_id IS NULL")
        ).scalar()

        if invalid_tracks > 0:
            logger.warning(f"Found {invalid_tracks} tracks with NULL artist_id")
            return False

        # Check statistics consistency
        stats_check = session.execute(
            text(
                """
            SELECT
                a.id,
                a.name,
                a.total_plays,
                COUNT(t.id) as track_count
            FROM artists a
            LEFT JOIN tracks t ON a.id = t.artist_id
            GROUP BY a.id, a.name, a.total_plays
            HAVING a.total_plays != COUNT(t.id)
        """
            )
        ).fetchall()

        if stats_check:
            logger.warning(f"Found {len(stats_check)} artists with inconsistent statistics")
            return False

        logger.info("Migration verification passed")
        return True
    except Exception as e:
        logger.error(f"Error verifying migration: {str(e)}")
        return False


def cleanup(session):
    """Clean up temporary columns"""
    try:
        session.execute(
            text(
                """
            ALTER TABLE tracks
            DROP COLUMN IF EXISTS temp_artist_name,
            DROP COLUMN IF EXISTS artist;
        """
            )
        )
        session.commit()
        logger.info("Cleanup completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        session.rollback()
        return False


def migrate_to_artists():
    """Main migration function"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        logger.info("Starting migration to artists table structure...")

        # Step 1: Create artists table
        if not create_artists_table(engine, session):
            raise Exception("Failed to create artists table")

        # Step 2: Prepare artist_stats table
        if not prepare_artist_stats_table(session):
            raise Exception("Failed to prepare artist_stats table")

        # Step 3: Prepare tracks table
        if not prepare_tracks_table(session):
            raise Exception("Failed to prepare tracks table")

        # Step 4: Create artists
        artist_mapping = create_artists(session)
        if not artist_mapping:
            raise Exception("Failed to create artists")

        # Step 5: Update track references
        if not update_track_references(session, artist_mapping):
            raise Exception("Failed to update track references")

        # Step 6: Update artist statistics
        if not update_artist_statistics(session, artist_mapping):
            raise Exception("Failed to update artist statistics")

        # Step 7: Verify migration
        if not verify_migration(session):
            raise Exception("Migration verification failed")

        # Step 8: Cleanup
        if not cleanup(session):
            raise Exception("Failed to clean up temporary data")

        logger.info("✅ Migration completed successfully!")

    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    migrate_to_artists()
