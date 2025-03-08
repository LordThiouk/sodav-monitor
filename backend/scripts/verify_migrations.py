"""
Script pour vérifier que les migrations ont été appliquées correctement.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire racine du projet au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from backend.models.database import get_database_url
from backend.utils.logging_config import setup_logging, log_with_category

# Configurer le logging
logger = setup_logging(__name__)

def verify_migrations():
    """Vérifie que les migrations ont été appliquées correctement."""
    try:
        # Obtenir l'URL de la base de données
        db_url = get_database_url()
        
        # Créer le moteur SQLAlchemy
        engine = create_engine(db_url)
        
        # Créer une session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Vérifier les colonnes de la table tracks
        inspector = inspect(engine)
        track_columns = [col['name'] for col in inspector.get_columns('tracks')]
        
        log_with_category(logger, "VERIFICATION", "info", f"Colonnes de la table tracks: {track_columns}")
        
        # Vérifier si les colonnes release_date et genre existent
        if 'release_date' in track_columns:
            log_with_category(logger, "VERIFICATION", "info", "La colonne release_date existe dans la table tracks ✅")
        else:
            log_with_category(logger, "VERIFICATION", "error", "La colonne release_date n'existe pas dans la table tracks ❌")
        
        if 'genre' in track_columns:
            log_with_category(logger, "VERIFICATION", "info", "La colonne genre existe dans la table tracks ✅")
        else:
            log_with_category(logger, "VERIFICATION", "error", "La colonne genre n'existe pas dans la table tracks ❌")
        
        # Vérifier les colonnes de la table track_detections
        detection_columns = [col['name'] for col in inspector.get_columns('track_detections')]
        
        log_with_category(logger, "VERIFICATION", "info", f"Colonnes de la table track_detections: {detection_columns}")
        
        # Vérifier si la colonne detection_method existe
        if 'detection_method' in detection_columns:
            log_with_category(logger, "VERIFICATION", "info", "La colonne detection_method existe dans la table track_detections ✅")
        else:
            log_with_category(logger, "VERIFICATION", "error", "La colonne detection_method n'existe pas dans la table track_detections ❌")
        
        # Vérifier si les tables existent
        tables = inspector.get_table_names()
        log_with_category(logger, "VERIFICATION", "info", f"Tables dans la base de données: {tables}")
        
        return True
    except Exception as e:
        log_with_category(logger, "VERIFICATION", "error", f"Erreur lors de la vérification: {str(e)}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    log_with_category(logger, "VERIFICATION", "info", "Démarrage de la vérification des migrations")
    success = verify_migrations()
    
    if success:
        log_with_category(logger, "VERIFICATION", "info", "Vérification réussie")
        sys.exit(0)
    else:
        log_with_category(logger, "VERIFICATION", "error", "Échec de la vérification")
        sys.exit(1) 