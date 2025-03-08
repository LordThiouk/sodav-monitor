#!/usr/bin/env python
"""
Script pour tester la détection locale avec les empreintes digitales stockées.
"""

import os
import sys
import asyncio
import logging
import numpy as np
from pathlib import Path
import librosa
import hashlib
from datetime import timedelta

# Ajouter le répertoire racine du projet au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# Ajouter également le répertoire backend au chemin
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from backend.models.database import SessionLocal
from backend.detection.audio_processor.track_manager import TrackManager
from backend.utils.logging_config import setup_logging, log_with_category
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.models.models import Track, Artist

# Configurer le logging
logger = setup_logging(__name__)

def load_env_file(env_path):
    """Charge les variables d'environnement depuis un fichier .env."""
    if not env_path.exists():
        return False
    
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            key, value = line.split("=", 1)
            os.environ[key] = value
    
    return True

async def test_local_detection():
    """Teste la détection locale avec les empreintes digitales stockées."""
    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path("/Users/cex/Desktop/sodav-monitor/.env")
    log_with_category(logger, "GENERAL", "info", f"Looking for .env file at: {env_path}")
    
    env_vars = load_env_file(env_path)
    
    if not env_vars:
        log_with_category(logger, "GENERAL", "error", "Failed to load environment variables")
        return False
    
    # Créer une session de base de données
    db = SessionLocal()
    
    try:
        # Initialiser le gestionnaire de pistes et l'extracteur de caractéristiques
        feature_extractor = FeatureExtractor()
        track_manager = TrackManager(db_session=db, feature_extractor=feature_extractor)
        
        # Utiliser un fichier audio de test
        test_file_path = Path(project_root) / "backend" / "tests" / "data" / "audio" / "sample1.mp3"
        if not test_file_path.exists():
            log_with_category(logger, "GENERAL", "error", f"Test audio file not found at {test_file_path}")
            return False
        
        log_with_category(logger, "GENERAL", "info", f"Using test audio file: {test_file_path}")
        
        # Charger le fichier audio avec librosa
        try:
            audio_data, sample_rate = librosa.load(test_file_path, sr=None)
            log_with_category(logger, "GENERAL", "info", f"Loaded audio file: {len(audio_data)} samples, {sample_rate} Hz")
            
            # Créer un dictionnaire de features
            play_duration = len(audio_data) / sample_rate
            
            # Générer un fingerprint de test
            fingerprint = hashlib.md5(audio_data.tobytes()[:1000]).hexdigest()
            
            audio_features = {
                "play_duration": play_duration,
                "mfcc_mean": np.random.rand(20),  # Simuler des caractéristiques MFCC
                "chroma_mean": np.random.rand(12),  # Simuler des caractéristiques chroma
                "spectral_centroid_mean": 1000.0,  # Simuler le centroïde spectral
                "tempo": 120.0,  # Simuler le tempo
                "rhythm_strength": 0.8,  # Simuler la force du rythme
                "fingerprint": fingerprint,  # Utiliser un fingerprint généré
                "is_music": True,  # Indiquer que c'est de la musique
                "confidence": 0.9  # Simuler un score de confiance
            }
            
            log_with_category(logger, "GENERAL", "info", f"Created audio features with play_duration: {audio_features['play_duration']} seconds")
            log_with_category(logger, "GENERAL", "info", f"Generated fingerprint: {fingerprint[:20]}...")
            
        except Exception as e:
            log_with_category(logger, "GENERAL", "error", f"Error loading audio file: {str(e)}")
            return False
        
        # Étape 1 : Créer une piste de test avec l'empreinte digitale
        log_with_category(logger, "GENERAL", "info", "Step 1: Creating test track with fingerprint")
        
        # Vérifier si l'artiste existe
        artist_name = "Test Artist"
        artist = db.query(Artist).filter(Artist.name == artist_name).first()
        if not artist:
            artist = Artist(name=artist_name)
            db.add(artist)
            db.flush()
            log_with_category(logger, "GENERAL", "info", f"Created test artist: {artist_name}")
        
        # Vérifier si la piste existe avec cette empreinte digitale
        existing_track = db.query(Track).filter(Track.fingerprint == fingerprint).first()
        
        if existing_track:
            log_with_category(logger, "GENERAL", "info", f"Found existing track with fingerprint: {fingerprint[:20]}...")
            track = existing_track
        else:
            # Vérifier si la piste existe par titre et artiste
            track_title = "Test Track"
            track = db.query(Track).filter(
                Track.title == track_title,
                Track.artist_id == artist.id
            ).first()
            
            if not track:
                track = Track(
                    title=track_title,
                    artist_id=artist.id,
                    fingerprint=fingerprint,
                    duration=timedelta(seconds=play_duration)
                )
                db.add(track)
                try:
                    db.commit()
                    log_with_category(logger, "GENERAL", "info", f"Created test track: {track_title} with fingerprint: {fingerprint[:20]}...")
                except Exception as e:
                    db.rollback()
                    log_with_category(logger, "GENERAL", "warning", f"Error creating track: {str(e)}")
                    # Essayer de récupérer la piste existante avec cette empreinte
                    track = db.query(Track).filter(Track.fingerprint == fingerprint).first()
                    if track:
                        log_with_category(logger, "GENERAL", "info", f"Using existing track with fingerprint: {fingerprint[:20]}...")
                    else:
                        log_with_category(logger, "GENERAL", "error", "Could not find or create track with fingerprint")
                        return False
            else:
                # Mettre à jour l'empreinte digitale
                try:
                    track.fingerprint = fingerprint
                    track.duration = timedelta(seconds=play_duration)
                    db.commit()
                    log_with_category(logger, "GENERAL", "info", f"Updated test track: {track_title} with fingerprint: {fingerprint[:20]}...")
                except Exception as e:
                    db.rollback()
                    log_with_category(logger, "GENERAL", "warning", f"Error updating track: {str(e)}")
                    # Essayer de récupérer la piste existante avec cette empreinte
                    track = db.query(Track).filter(Track.fingerprint == fingerprint).first()
                    if track:
                        log_with_category(logger, "GENERAL", "info", f"Using existing track with fingerprint: {fingerprint[:20]}...")
                    else:
                        log_with_category(logger, "GENERAL", "error", "Could not find or update track with fingerprint")
                        return False
        
        # Étape 2 : Tester la détection locale
        log_with_category(logger, "GENERAL", "info", "Step 2: Testing local detection")
        
        # Appeler directement la méthode find_local_match
        local_result = await track_manager.find_local_match(audio_features)
        
        if local_result:
            log_with_category(logger, "GENERAL", "info", "Local detection successful!")
            log_with_category(logger, "GENERAL", "info", f"Detected track: {local_result.get('title')} by {local_result.get('artist')}")
            log_with_category(logger, "GENERAL", "info", f"Confidence: {local_result.get('confidence')}")
            log_with_category(logger, "GENERAL", "info", f"Fingerprint: {local_result.get('fingerprint')[:20]}...")
            return True
        else:
            log_with_category(logger, "GENERAL", "warning", "Local detection failed")
            return False
            
    except Exception as e:
        log_with_category(logger, "GENERAL", "error", f"Error testing local detection: {e}")
        import traceback
        log_with_category(logger, "GENERAL", "error", f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        db.close()

async def main():
    """Fonction principale."""
    log_with_category(logger, "GENERAL", "info", "Starting local detection test")
    
    result = await test_local_detection()
    
    if result:
        log_with_category(logger, "GENERAL", "info", "Local detection test passed successfully")
    else:
        log_with_category(logger, "GENERAL", "warning", "Local detection test failed")

if __name__ == "__main__":
    asyncio.run(main()) 