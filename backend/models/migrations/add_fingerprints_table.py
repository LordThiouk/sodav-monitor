"""
Script de migration pour ajouter la colonne chromaprint à la table tracks
et créer la table fingerprints pour stocker les empreintes multiples.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire racine du projet au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, Float, DateTime, func, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from backend.models.database import get_database_url
from backend.utils.logging_config import setup_logging, log_with_category

# Configurer le logging
logger = setup_logging(__name__)

# Base déclarative pour la définition des modèles
Base = declarative_base()

# Définition de la table fingerprints
class Fingerprint(Base):
    __tablename__ = 'fingerprints'
    
    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.id', ondelete='CASCADE'), index=True)
    hash = Column(String(255), index=True)
    raw_data = Column(LargeBinary)
    offset = Column(Float)  # Position dans la piste en secondes
    algorithm = Column(String(50))  # 'md5', 'chromaprint', etc.
    created_at = Column(DateTime, default=func.now())

def add_fingerprints_table_and_chromaprint():
    """
    Ajoute la colonne chromaprint à la table tracks et crée la table fingerprints
    si elle n'existe pas déjà.
    """
    try:
        # Obtenir l'URL de la base de données
        db_url = get_database_url()
        
        # Créer le moteur SQLAlchemy
        engine = create_engine(db_url)
        
        # Créer une session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Vérifier si la table fingerprints existe déjà
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Créer la table fingerprints si elle n'existe pas
        if 'fingerprints' not in tables:
            log_with_category(logger, "MIGRATION", "info", "Création de la table fingerprints")
            Fingerprint.__table__.create(engine)
        else:
            log_with_category(logger, "MIGRATION", "info", "La table fingerprints existe déjà")
        
        # Vérifier si la colonne chromaprint existe déjà dans la table tracks
        columns = [col['name'] for col in inspector.get_columns('tracks')]
        
        # Ajouter la colonne chromaprint si elle n'existe pas
        if 'chromaprint' not in columns:
            log_with_category(logger, "MIGRATION", "info", "Ajout de la colonne chromaprint à la table tracks")
            session.execute(text('ALTER TABLE tracks ADD COLUMN chromaprint TEXT'))
        else:
            log_with_category(logger, "MIGRATION", "info", "La colonne chromaprint existe déjà dans la table tracks")
        
        # Migrer les empreintes existantes vers la nouvelle table
        if 'fingerprints' in tables:
            # Vérifier si des empreintes ont déjà été migrées
            fingerprint_count = session.execute(text('SELECT COUNT(*) FROM fingerprints')).scalar()
            
            if fingerprint_count == 0:
                log_with_category(logger, "MIGRATION", "info", "Migration des empreintes existantes vers la table fingerprints")
                
                # Récupérer toutes les pistes avec une empreinte
                tracks_with_fingerprint = session.execute(
                    text('SELECT id, fingerprint, fingerprint_raw FROM tracks WHERE fingerprint IS NOT NULL')
                ).fetchall()
                
                log_with_category(logger, "MIGRATION", "info", f"Nombre de pistes avec empreinte: {len(tracks_with_fingerprint)}")
                
                # Migrer chaque empreinte
                for track in tracks_with_fingerprint:
                    track_id, fingerprint, fingerprint_raw = track
                    
                    # Insérer l'empreinte dans la table fingerprints
                    session.execute(
                        text("""
                            INSERT INTO fingerprints (track_id, hash, raw_data, offset, algorithm, created_at)
                            VALUES (:track_id, :hash, :raw_data, :offset, :algorithm, NOW())
                        """),
                        {
                            'track_id': track_id,
                            'hash': fingerprint,
                            'raw_data': fingerprint_raw,
                            'offset': 0.0,
                            'algorithm': 'md5'
                        }
                    )
                    
                    log_with_category(logger, "MIGRATION", "info", f"Empreinte migrée pour la piste {track_id}")
            else:
                log_with_category(logger, "MIGRATION", "info", f"Les empreintes ont déjà été migrées ({fingerprint_count} empreintes trouvées)")
        
        # Valider les changements
        session.commit()
        log_with_category(logger, "MIGRATION", "info", "Migration terminée avec succès")
        
        return True
    except Exception as e:
        log_with_category(logger, "MIGRATION", "error", f"Erreur lors de la migration: {str(e)}")
        import traceback
        log_with_category(logger, "MIGRATION", "error", traceback.format_exc())
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    log_with_category(logger, "MIGRATION", "info", "Démarrage de la migration pour ajouter la table fingerprints et la colonne chromaprint")
    success = add_fingerprints_table_and_chromaprint()
    
    if success:
        log_with_category(logger, "MIGRATION", "info", "Migration réussie")
        sys.exit(0)
    else:
        log_with_category(logger, "MIGRATION", "error", "Échec de la migration")
        sys.exit(1) 