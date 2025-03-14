#!/usr/bin/env python

"""
Script pour corriger le schéma de la base de données de test.
Ajoute les colonnes manquantes aux tables station_track_stats et analytics_data.
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire racine du projet au PYTHONPATH
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

import logging

from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_test_db_schema():
    """Corrige le schéma de la base de données de test en ajoutant les colonnes manquantes."""
    # Forcer l'environnement de test
    os.environ["ENV"] = "test"

    # Importer après avoir défini l'environnement
    from backend.models.database import TEST_DATABASE_URL

    logger.info(f"Connexion à la base de données de test: {TEST_DATABASE_URL}")

    # Créer le moteur SQLAlchemy
    engine = create_engine(TEST_DATABASE_URL)

    try:
        # Vérifier si les tables existent
        with engine.connect() as conn:
            # Vérifier si la table station_track_stats existe
            result = conn.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'station_track_stats'
                )
            """
                )
            )

            if not result.scalar():
                logger.info("La table station_track_stats n'existe pas. Création des tables...")
                # Importer les modèles et créer toutes les tables
                from backend.models.models import Base

                Base.metadata.create_all(bind=engine)
                logger.info("Tables créées avec succès.")

            # Ajouter la colonne total_play_time à la table station_track_stats si elle n'existe pas
            logger.info("Vérification de la colonne total_play_time dans station_track_stats...")
            result = conn.execute(
                text(
                    """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'station_track_stats'
                AND column_name = 'total_play_time'
            """
                )
            )

            if not result.fetchone():
                logger.info("Ajout de la colonne total_play_time à station_track_stats...")
                conn.execute(
                    text(
                        """
                    ALTER TABLE station_track_stats
                    ADD COLUMN total_play_time INTERVAL DEFAULT '0 seconds'
                """
                    )
                )
                logger.info("Colonne total_play_time ajoutée avec succès.")
            else:
                logger.info("La colonne total_play_time existe déjà dans station_track_stats.")

            # Ajouter la colonne last_played à la table station_track_stats si elle n'existe pas
            logger.info("Vérification de la colonne last_played dans station_track_stats...")
            result = conn.execute(
                text(
                    """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'station_track_stats'
                AND column_name = 'last_played'
            """
                )
            )

            if not result.fetchone():
                logger.info("Ajout de la colonne last_played à station_track_stats...")
                conn.execute(
                    text(
                        """
                    ALTER TABLE station_track_stats
                    ADD COLUMN last_played TIMESTAMP WITH TIME ZONE
                """
                    )
                )
                logger.info("Colonne last_played ajoutée avec succès.")
            else:
                logger.info("La colonne last_played existe déjà dans station_track_stats.")

            # Ajouter la colonne average_confidence à la table station_track_stats si elle n'existe pas
            logger.info("Vérification de la colonne average_confidence dans station_track_stats...")
            result = conn.execute(
                text(
                    """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'station_track_stats'
                AND column_name = 'average_confidence'
            """
                )
            )

            if not result.fetchone():
                logger.info("Ajout de la colonne average_confidence à station_track_stats...")
                conn.execute(
                    text(
                        """
                    ALTER TABLE station_track_stats
                    ADD COLUMN average_confidence FLOAT DEFAULT 0.0
                """
                    )
                )
                logger.info("Colonne average_confidence ajoutée avec succès.")
            else:
                logger.info("La colonne average_confidence existe déjà dans station_track_stats.")

            # Vérifier si la table analytics_data existe
            result = conn.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'analytics_data'
                )
            """
                )
            )

            if not result.scalar():
                logger.info(
                    "La table analytics_data n'existe pas. Elle sera créée lors de la création des tables."
                )
            else:
                # Ajouter les colonnes manquantes à la table analytics_data
                logger.info("Vérification des colonnes dans analytics_data...")

                # Vérifier total_tracks
                result = conn.execute(
                    text(
                        """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'analytics_data'
                    AND column_name = 'total_tracks'
                """
                    )
                )

                if not result.fetchone():
                    logger.info("Ajout de la colonne total_tracks à analytics_data...")
                    conn.execute(
                        text(
                            """
                        ALTER TABLE analytics_data
                        ADD COLUMN total_tracks INTEGER DEFAULT 0
                    """
                        )
                    )
                    logger.info("Colonne total_tracks ajoutée avec succès.")
                else:
                    logger.info("La colonne total_tracks existe déjà dans analytics_data.")

                # Vérifier total_artists
                result = conn.execute(
                    text(
                        """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'analytics_data'
                    AND column_name = 'total_artists'
                """
                    )
                )

                if not result.fetchone():
                    logger.info("Ajout de la colonne total_artists à analytics_data...")
                    conn.execute(
                        text(
                            """
                        ALTER TABLE analytics_data
                        ADD COLUMN total_artists INTEGER DEFAULT 0
                    """
                        )
                    )
                    logger.info("Colonne total_artists ajoutée avec succès.")
                else:
                    logger.info("La colonne total_artists existe déjà dans analytics_data.")

                # Vérifier total_stations
                result = conn.execute(
                    text(
                        """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'analytics_data'
                    AND column_name = 'total_stations'
                """
                    )
                )

                if not result.fetchone():
                    logger.info("Ajout de la colonne total_stations à analytics_data...")
                    conn.execute(
                        text(
                            """
                        ALTER TABLE analytics_data
                        ADD COLUMN total_stations INTEGER DEFAULT 0
                    """
                        )
                    )
                    logger.info("Colonne total_stations ajoutée avec succès.")
                else:
                    logger.info("La colonne total_stations existe déjà dans analytics_data.")

            # Commit les changements
            conn.commit()

        logger.info("Correction du schéma de la base de données terminée avec succès.")

    except Exception as e:
        logger.error(f"Erreur lors de la correction du schéma: {str(e)}")
        raise


if __name__ == "__main__":
    fix_test_db_schema()
