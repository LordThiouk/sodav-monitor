#!/usr/bin/env python
"""
Script pour lister toutes les pistes dans la base de données.
"""

import os
import sys
import logging

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, backend_dir)

from backend.models.database import get_db
from backend.models.models import Track, Artist
from backend.logs.log_manager import LogManager

# Configurer le logging
log_manager = LogManager()
logger = log_manager.get_logger("list_tracks")

def list_tracks():
    """Liste toutes les pistes dans la base de données."""
    # Obtenir une session de base de données
    db = next(get_db())
    
    try:
        # Récupérer toutes les pistes
        tracks = db.query(Track).all()
        
        print(f"Nombre de pistes: {len(tracks)}")
        print("=" * 80)
        
        for track in tracks:
            # Récupérer l'artiste
            artist = db.query(Artist).filter(Artist.id == track.artist_id).first()
            artist_name = artist.name if artist else "Unknown Artist"
            
            print(f"ID: {track.id}")
            print(f"Titre: {track.title}")
            print(f"Artiste: {artist_name}")
            print(f"ISRC: {track.isrc}")
            print(f"Album: {track.album}")
            print(f"Label: {track.label}")
            print("-" * 40)
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des pistes: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    list_tracks() 