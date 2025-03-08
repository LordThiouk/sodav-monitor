"""
Script de migration pour ajouter les champs release_date et genre au modèle Track.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire racine du projet au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, Column, String, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.models.database import get_database_url
from backend.utils.logging_config import setup_logging, log_with_category

# Configurer le logging
logger = setup_logging(__name__)

def add_track_fields():
    """Ajoute les champs release_date et genre au modèle Track."""
    try:
        # Obtenir l'URL de la base de données
        db_url = get_database_url()
        
        # Créer le moteur SQLAlchemy
        engine = create_engine(db_url)
        
        # Créer une session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Vérifier si les colonnes existent déjà
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('tracks')]
        
        # Ajouter la colonne release_date si elle n'existe pas
        if 'release_date' not in columns:
            log_with_category(logger, "MIGRATION", "info", "Ajout de la colonne release_date à la table tracks")
            session.execute(text('ALTER TABLE tracks ADD COLUMN release_date VARCHAR'))
        else:
            log_with_category(logger, "MIGRATION", "info", "La colonne release_date existe déjà dans la table tracks")
        
        # Ajouter la colonne genre si elle n'existe pas
        if 'genre' not in columns:
            log_with_category(logger, "MIGRATION", "info", "Ajout de la colonne genre à la table tracks")
            session.execute(text('ALTER TABLE tracks ADD COLUMN genre VARCHAR'))
        else:
            log_with_category(logger, "MIGRATION", "info", "La colonne genre existe déjà dans la table tracks")
        
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
    log_with_category(logger, "MIGRATION", "info", "Démarrage de la migration pour ajouter les champs release_date et genre au modèle Track")
    success = add_track_fields()
    
    if success:
        log_with_category(logger, "MIGRATION", "info", "Migration réussie")
        sys.exit(0)
    else:
        log_with_category(logger, "MIGRATION", "error", "Échec de la migration")
        sys.exit(1) 