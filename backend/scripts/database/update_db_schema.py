#!/usr/bin/env python

"""
Script pour mettre à jour le schéma de la base de données.
Ajoute les colonnes manquantes aux tables station_track_stats et analytics_data.
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire racine du projet au PYTHONPATH
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

from datetime import timedelta

from sqlalchemy import create_engine, text

from backend.models.database import get_database_url
from backend.models.models import AnalyticsData, Base, StationTrackStats


def update_schema():
    """Met à jour le schéma de la base de données."""
    print("Mise à jour du schéma de la base de données...")

    # Connexion à la base de données
    engine = create_engine(get_database_url())

    # Créer les tables
    print("Création des tables si elles n'existent pas...")
    Base.metadata.create_all(engine)

    print("Tables créées avec succès.")

    # Vérifier que les colonnes existent
    print("Vérification des colonnes...")
    with engine.connect() as conn:
        # Vérifier les colonnes de StationTrackStats
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'station_track_stats'"
            )
        )
        columns = [row[0] for row in result]
        print(f"Colonnes de station_track_stats: {columns}")

        # Ajouter les colonnes manquantes à station_track_stats
        if "total_play_time" not in columns:
            print("Ajout de la colonne total_play_time à station_track_stats...")
            conn.execute(
                text(
                    "ALTER TABLE station_track_stats ADD COLUMN total_play_time INTERVAL DEFAULT '0 seconds'"
                )
            )

        if "last_played" not in columns:
            print("Ajout de la colonne last_played à station_track_stats...")
            conn.execute(text("ALTER TABLE station_track_stats ADD COLUMN last_played TIMESTAMP"))

        if "average_confidence" not in columns:
            print("Ajout de la colonne average_confidence à station_track_stats...")
            conn.execute(
                text(
                    "ALTER TABLE station_track_stats ADD COLUMN average_confidence FLOAT DEFAULT 0.0"
                )
            )

        # Vérifier les colonnes de AnalyticsData
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'analytics_data'"
            )
        )
        columns = [row[0] for row in result]
        print(f"Colonnes de analytics_data: {columns}")

        # Ajouter les colonnes manquantes à analytics_data
        if "total_tracks" not in columns:
            print("Ajout de la colonne total_tracks à analytics_data...")
            conn.execute(
                text("ALTER TABLE analytics_data ADD COLUMN total_tracks INTEGER DEFAULT 0")
            )

        if "total_artists" not in columns:
            print("Ajout de la colonne total_artists à analytics_data...")
            conn.execute(
                text("ALTER TABLE analytics_data ADD COLUMN total_artists INTEGER DEFAULT 0")
            )

        if "total_stations" not in columns:
            print("Ajout de la colonne total_stations à analytics_data...")
            conn.execute(
                text("ALTER TABLE analytics_data ADD COLUMN total_stations INTEGER DEFAULT 0")
            )

        # Vérifier à nouveau les colonnes après les modifications
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'station_track_stats'"
            )
        )
        columns = [row[0] for row in result]
        print(f"Colonnes de station_track_stats après mise à jour: {columns}")

        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'analytics_data'"
            )
        )
        columns = [row[0] for row in result]
        print(f"Colonnes de analytics_data après mise à jour: {columns}")

        # Commit les changements
        conn.commit()

    print("Mise à jour du schéma terminée avec succès.")


if __name__ == "__main__":
    update_schema()
