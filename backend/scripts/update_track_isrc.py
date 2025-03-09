#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour mettre à jour l'ISRC d'une piste dans la base de données.
Usage: python update_track_isrc.py <track_id> <isrc>
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal
from backend.models.models import Track
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_track_isrc(track_id, isrc):
    """
    Met à jour l'ISRC d'une piste dans la base de données.
    
    Args:
        track_id (int): L'ID de la piste à mettre à jour.
        isrc (str): Le code ISRC à définir.
    """
    # Initialiser la base de données
    init_db()
    
    # Créer une session de base de données
    db_session = SessionLocal()
    
    try:
        # Récupérer la piste de la base de données
        track = db_session.query(Track).filter_by(id=track_id).first()
        
        if not track:
            logger.error(f"Piste avec ID {track_id} non trouvée dans la base de données.")
            return
        
        # Afficher les détails actuels
        logger.info(f"=== Détails actuels de la piste ID {track_id} ===")
        logger.info(f"Titre: {track.title}")
        logger.info(f"ISRC actuel: {track.isrc or 'Non disponible'}")
        
        # Mettre à jour l'ISRC
        track.isrc = isrc
        db_session.commit()
        
        # Vérifier que la mise à jour a été effectuée
        track = db_session.query(Track).filter_by(id=track_id).first()
        
        logger.info(f"\n=== Détails mis à jour de la piste ID {track_id} ===")
        logger.info(f"Titre: {track.title}")
        logger.info(f"Nouvel ISRC: {track.isrc or 'Non disponible'}")
        
        logger.info(f"ISRC mis à jour avec succès pour la piste ID {track_id}.")
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de l'ISRC: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Fermer la session de base de données
        db_session.close()

def main():
    """
    Fonction principale.
    """
    if len(sys.argv) < 3:
        logger.error("Usage: python update_track_isrc.py <track_id> <isrc>")
        sys.exit(1)
    
    try:
        track_id = int(sys.argv[1])
    except ValueError:
        logger.error("L'ID de la piste doit être un nombre entier.")
        sys.exit(1)
    
    isrc = sys.argv[2]
    
    update_track_isrc(track_id, isrc)

if __name__ == "__main__":
    main() 