#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour mettre à jour le schéma de la base de données afin de prendre en charge
les empreintes Chromaprint et les empreintes multiples par piste.

Usage: python update_db_schema_for_fingerprints.py [--apply]

Sans l'option --apply, le script affiche uniquement les modifications qui seraient apportées.
Avec l'option --apply, le script applique les modifications à la base de données.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary, Float, DateTime, func

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal, engine
from backend.models.models import Base, Track

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Définition de la nouvelle table pour les empreintes multiples
class Fingerprint(Base):
    __tablename__ = 'fingerprints'
    
    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.id', ondelete='CASCADE'), index=True)
    hash = Column(String(255), index=True)
    raw_data = Column(LargeBinary)
    offset = Column(Float)  # Position dans la piste en secondes
    algorithm = Column(String(50))  # 'md5', 'chromaprint', etc.
    created_at = Column(DateTime, default=func.now())
    
    # Relation avec Track
    track = relationship("Track", back_populates="fingerprints")

# Ajouter la relation à la classe Track
def add_fingerprints_relationship_to_track():
    """Ajoute la relation fingerprints à la classe Track."""
    if not hasattr(Track, 'fingerprints'):
        Track.fingerprints = relationship("Fingerprint", back_populates="track", cascade="all, delete-orphan")
        logger.info("Relation 'fingerprints' ajoutée à la classe Track")

def add_chromaprint_column_to_track():
    """Ajoute la colonne chromaprint à la table tracks."""
    inspector = sa.inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('tracks')]
    
    if 'chromaprint' not in columns:
        logger.info("Ajout de la colonne 'chromaprint' à la table tracks")
        return True
    else:
        logger.info("La colonne 'chromaprint' existe déjà dans la table tracks")
        return False

def migrate_existing_fingerprints(session):
    """Migre les empreintes existantes vers la nouvelle table."""
    tracks = session.query(Track).filter(Track.fingerprint.isnot(None)).all()
    logger.info(f"Migration des empreintes pour {len(tracks)} pistes")
    
    for track in tracks:
        # Créer une empreinte MD5
        if track.fingerprint and track.fingerprint_raw:
            fingerprint = Fingerprint(
                track_id=track.id,
                hash=track.fingerprint,
                raw_data=track.fingerprint_raw,
                offset=0.0,
                algorithm='md5'
            )
            session.add(fingerprint)
            logger.info(f"Empreinte MD5 migrée pour la piste {track.id}")
    
    session.commit()
    logger.info("Migration des empreintes terminée")

def update_db_schema(apply=False):
    """Met à jour le schéma de la base de données."""
    try:
        # Initialiser la base de données
        init_db()
        session = SessionLocal()
        
        logger.info("Vérification du schéma de la base de données")
        
        # Ajouter la relation fingerprints à la classe Track
        add_fingerprints_relationship_to_track()
        
        # Vérifier si la colonne chromaprint doit être ajoutée
        add_chromaprint = add_chromaprint_column_to_track()
        
        if apply:
            logger.info("Application des modifications au schéma de la base de données")
            
            # Créer la table fingerprints si elle n'existe pas
            if not engine.dialect.has_table(engine.connect(), "fingerprints"):
                logger.info("Création de la table 'fingerprints'")
                Fingerprint.__table__.create(engine)
            else:
                logger.info("La table 'fingerprints' existe déjà")
            
            # Ajouter la colonne chromaprint à la table tracks
            if add_chromaprint:
                with engine.connect() as conn:
                    conn.execute(sa.text("ALTER TABLE tracks ADD COLUMN chromaprint TEXT"))
                logger.info("Colonne 'chromaprint' ajoutée à la table tracks")
            
            # Migrer les empreintes existantes
            migrate_existing_fingerprints(session)
            
            logger.info("Mise à jour du schéma terminée avec succès")
        else:
            logger.info("Mode simulation: aucune modification n'a été appliquée")
            logger.info("Pour appliquer les modifications, utilisez l'option --apply")
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du schéma: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        session.close()

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Mise à jour du schéma de la base de données pour les empreintes")
    parser.add_argument("--apply", action="store_true", help="Appliquer les modifications")
    args = parser.parse_args()
    
    update_db_schema(apply=args.apply)

if __name__ == "__main__":
    main() 