#!/usr/bin/env python
"""
Script pour créer des pistes de test avec des codes ISRC dans la base de données.

Ce script crée plusieurs pistes avec des codes ISRC valides et invalides,
ainsi que des pistes dupliquées avec le même ISRC pour tester les scripts
de validation et de fusion.
"""

import os
import sys
import argparse
import logging
from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, backend_dir)

from backend.models.database import get_db
from backend.models.models import Track, Artist, TrackStats
from backend.logs.log_manager import LogManager

# Configurer le logging
log_manager = LogManager()
logger = log_manager.get_logger("create_test_tracks")

def create_artist(db_session: Session, name: str) -> int:
    """
    Crée un artiste dans la base de données.
    
    Args:
        db_session: Session de base de données
        name: Nom de l'artiste
        
    Returns:
        ID de l'artiste créé
    """
    # Vérifier si l'artiste existe déjà
    existing_artist = db_session.query(Artist).filter(Artist.name == name).first()
    if existing_artist:
        logger.info(f"Artiste existant: {name} (ID: {existing_artist.id})")
        return existing_artist.id
    
    # Créer un nouvel artiste
    artist = Artist(
        name=name,
        country="FR",
        region="Europe",
        type="Person",
        label="Test Label",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        total_play_time=timedelta(0),
        total_plays=0
    )
    db_session.add(artist)
    db_session.flush()
    
    logger.info(f"Nouvel artiste créé: {name} (ID: {artist.id})")
    return artist.id

def create_track(db_session: Session, title: str, artist_id: int, isrc: str = None) -> int:
    """
    Crée une piste dans la base de données.
    
    Args:
        db_session: Session de base de données
        title: Titre de la piste
        artist_id: ID de l'artiste
        isrc: Code ISRC (optionnel)
        
    Returns:
        ID de la piste créée
    """
    # Vérifier si la piste existe déjà
    existing_track = db_session.query(Track).filter(
        Track.title == title,
        Track.artist_id == artist_id
    ).first()
    
    if existing_track:
        logger.info(f"Piste existante: {title} (ID: {existing_track.id})")
        
        # Mettre à jour l'ISRC si nécessaire
        if isrc and not existing_track.isrc:
            existing_track.isrc = isrc
            db_session.flush()
            logger.info(f"ISRC ajouté à la piste existante: {isrc}")
        
        return existing_track.id
    
    # Créer une nouvelle piste
    track = Track(
        title=title,
        artist_id=artist_id,
        isrc=isrc,
        label="Test Label",
        album="Test Album",
        duration=timedelta(minutes=3, seconds=30),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(track)
    db_session.flush()
    
    # Créer les statistiques de piste
    track_stats = TrackStats(
        track_id=track.id,
        total_plays=0,
        average_confidence=0.0,
        last_detected=None,
        total_play_time=timedelta(0)
    )
    db_session.add(track_stats)
    db_session.flush()
    
    logger.info(f"Nouvelle piste créée: {title} (ID: {track.id}, ISRC: {isrc})")
    return track.id

def create_test_data(db_session: Session) -> Dict[str, int]:
    """
    Crée des données de test dans la base de données.
    
    Args:
        db_session: Session de base de données
        
    Returns:
        Dictionnaire contenant les statistiques de création
    """
    stats = {
        "artists": 0,
        "tracks": 0,
        "valid_isrc": 0,
        "invalid_isrc": 0,
        "duplicate_isrc": 0
    }
    
    # Créer des artistes
    try:
        artist1_id = create_artist(db_session, "Test Artist 1")
        artist2_id = create_artist(db_session, "Test Artist 2")
        artist3_id = create_artist(db_session, "Test Artist 3")
        db_session.commit()
        stats["artists"] = 3
    except Exception as e:
        logger.error(f"Erreur lors de la création des artistes: {e}")
        db_session.rollback()
        return stats
    
    # Créer des pistes avec des ISRC valides
    try:
        create_track(db_session, "Test Track 1", artist1_id, "FR1234567890")
        create_track(db_session, "Test Track 2", artist1_id, "US1234567890")
        create_track(db_session, "Test Track 3", artist2_id, "GB1234567890")
        db_session.commit()
        stats["tracks"] += 3
        stats["valid_isrc"] += 3
    except Exception as e:
        logger.error(f"Erreur lors de la création des pistes avec ISRC valides: {e}")
        db_session.rollback()
    
    # Créer des pistes avec des ISRC invalides
    try:
        create_track(db_session, "Test Track 4", artist2_id, "FR123456")  # Trop court
        create_track(db_session, "Test Track 5", artist2_id, "XX1234567890")  # Code pays invalide
        create_track(db_session, "Test Track 6", artist3_id, "FR12345678901234")  # Trop long
        db_session.commit()
        stats["tracks"] += 3
        stats["invalid_isrc"] += 3
    except Exception as e:
        logger.error(f"Erreur lors de la création des pistes avec ISRC invalides: {e}")
        db_session.rollback()
    
    # Créer des pistes avec des ISRC dupliqués (ces créations échoueront à cause de la contrainte d'unicité)
    try:
        create_track(db_session, "Test Track 7", artist3_id, "FR1234567890")  # Dupliqué avec Track 1
        db_session.commit()
        stats["tracks"] += 1
        stats["duplicate_isrc"] += 1
    except Exception as e:
        logger.warning(f"Erreur attendue lors de la création d'une piste avec ISRC dupliqué (FR1234567890): {e}")
        db_session.rollback()
    
    try:
        create_track(db_session, "Test Track 8", artist3_id, "US1234567890")  # Dupliqué avec Track 2
        db_session.commit()
        stats["tracks"] += 1
        stats["duplicate_isrc"] += 1
    except Exception as e:
        logger.warning(f"Erreur attendue lors de la création d'une piste avec ISRC dupliqué (US1234567890): {e}")
        db_session.rollback()
    
    # Créer des pistes sans ISRC
    try:
        create_track(db_session, "Test Track 9", artist1_id)
        create_track(db_session, "Test Track 10", artist2_id)
        db_session.commit()
        stats["tracks"] += 2
    except Exception as e:
        logger.error(f"Erreur lors de la création des pistes sans ISRC: {e}")
        db_session.rollback()
    
    logger.info("Données de test créées avec succès")
    return stats

def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(description="Crée des pistes de test avec des codes ISRC dans la base de données.")
    args = parser.parse_args()
    
    logger.info("Démarrage du script de création de pistes de test")
    
    # Obtenir une session de base de données
    db = next(get_db())
    
    try:
        # Créer les données de test
        stats = create_test_data(db)
        
        # Afficher les statistiques
        logger.info("Statistiques de création:")
        logger.info(f"  Artistes créés: {stats['artists']}")
        logger.info(f"  Pistes créées: {stats['tracks']}")
        logger.info(f"  ISRC valides: {stats['valid_isrc']}")
        logger.info(f"  ISRC invalides: {stats['invalid_isrc']}")
        logger.info(f"  ISRC dupliqués: {stats['duplicate_isrc']}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du script: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    logger.info("Script terminé avec succès")

if __name__ == "__main__":
    main() 