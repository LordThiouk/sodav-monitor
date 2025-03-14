"""
Script de migration pour ajouter le champ detection_method à la table track_detections.
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire racine du projet au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import Column, String, create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from backend.models.database import get_database_url
from backend.utils.logging_config import log_with_category, setup_logging

# Configurer le logging
logger = setup_logging(__name__)


def add_detection_method():
    """Ajoute le champ detection_method à la table track_detections."""
    try:
        # Obtenir l'URL de la base de données
        db_url = get_database_url()

        # Créer le moteur SQLAlchemy
        engine = create_engine(db_url)

        # Créer une session
        Session = sessionmaker(bind=engine)
        session = Session()

        # Vérifier si la colonne existe déjà
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("track_detections")]

        # Ajouter la colonne detection_method si elle n'existe pas
        if "detection_method" not in columns:
            log_with_category(
                logger,
                "MIGRATION",
                "info",
                "Ajout de la colonne detection_method à la table track_detections",
            )
            session.execute(
                text("ALTER TABLE track_detections ADD COLUMN detection_method VARCHAR")
            )
        else:
            log_with_category(
                logger,
                "MIGRATION",
                "info",
                "La colonne detection_method existe déjà dans la table track_detections",
            )

        # Valider les changements
        session.commit()
        log_with_category(logger, "MIGRATION", "info", "Migration terminée avec succès")

        return True
    except Exception as e:
        log_with_category(logger, "MIGRATION", "error", f"Erreur lors de la migration: {str(e)}")
        return False
    finally:
        session.close()


if __name__ == "__main__":
    log_with_category(
        logger,
        "MIGRATION",
        "info",
        "Démarrage de la migration pour ajouter le champ detection_method à la table track_detections",
    )
    success = add_detection_method()

    if success:
        log_with_category(logger, "MIGRATION", "info", "Migration réussie")
        sys.exit(0)
    else:
        log_with_category(logger, "MIGRATION", "error", "Échec de la migration")
        sys.exit(1)
