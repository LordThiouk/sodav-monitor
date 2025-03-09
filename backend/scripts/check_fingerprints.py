#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier les empreintes digitales des pistes.
Usage: python check_fingerprints.py
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal
from backend.models.models import Track, Fingerprint
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def check_fingerprints():
    """Vérifie les empreintes digitales des pistes."""
    try:
        # Initialiser la base de données
        init_db()
        
        # Créer une session
        session = SessionLocal()
        
        # Récupérer toutes les pistes
        tracks = session.query(Track).all()
        logger.info(f"Nombre de pistes: {len(tracks)}")
        
        # Afficher les détails de chaque piste
        for track in tracks:
            logger.info(f"=== Piste ID {track.id} ===")
            logger.info(f"Titre: {track.title}")
            logger.info(f"Artiste ID: {track.artist_id}")
            logger.info(f"ISRC: {track.isrc}")
            logger.info(f"Fingerprint: {track.fingerprint[:20]}..." if track.fingerprint else "Non disponible")
            logger.info(f"Chromaprint: {track.chromaprint[:20]}..." if track.chromaprint else "Non disponible")
            
            # Afficher les empreintes digitales
            fingerprints = track.fingerprints
            logger.info(f"Nombre d'empreintes: {len(fingerprints)}")
            
            for i, fp in enumerate(fingerprints):
                logger.info(f"  Empreinte {i+1}:")
                logger.info(f"    ID: {fp.id}")
                logger.info(f"    Hash: {fp.hash[:20]}..." if fp.hash else "Non disponible")
                logger.info(f"    Algorithme: {fp.algorithm}")
                logger.info(f"    Offset: {fp.offset}")
                logger.info(f"    Créée le: {fp.created_at}")
        
        # Récupérer toutes les empreintes
        fingerprints = session.query(Fingerprint).all()
        logger.info(f"\nNombre total d'empreintes: {len(fingerprints)}")
        
        for fp in fingerprints:
            logger.info(f"Empreinte ID {fp.id} pour la piste ID {fp.track_id}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des empreintes: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Fermer la session
        session.close()

def main():
    """Fonction principale."""
    check_fingerprints()

if __name__ == "__main__":
    main() 