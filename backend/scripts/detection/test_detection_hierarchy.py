#!/usr/bin/env python
"""
Script pour tester l'ensemble du processus de détection hiérarchique.
"""

import os
import sys
import asyncio
import logging
import numpy as np
from pathlib import Path
import librosa

# Ajouter le répertoire racine du projet au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# Ajouter également le répertoire backend au chemin
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from detection.audio_processor.core import AudioProcessor
    from models.database import SessionLocal
    from utils.logging_config import setup_logging, log_with_category
except ImportError as e:
    print(f"Erreur d'importation: {e}. Assurez-vous que le chemin est correct.")
    print(f"Chemins d'importation: {sys.path}")
    sys.exit(1)

logger = setup_logging(__name__)

def load_env_file(env_path):
    """Charge les variables d'environnement depuis un fichier .env."""
    if not env_path.exists():
        logger.error(f"Environment file not found: {env_path}")
        return {}
    
    env_vars = {}
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value
                env_vars[key] = value
    
    return env_vars

async def test_detection_hierarchy():
    """Teste l'ensemble du processus de détection hiérarchique."""
    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path("/Users/cex/Desktop/sodav-monitor/.env")
    log_with_category(logger, "TEST", "info", f"Looking for .env file at: {env_path}")
    
    env_vars = load_env_file(env_path)
    
    if not env_vars:
        log_with_category(logger, "TEST", "error", "Failed to load environment variables")
        return False
    
    # Vérifier les clés API
    acoustid_api_key = os.environ.get("ACOUSTID_API_KEY")
    audd_api_key = os.environ.get("AUDD_API_KEY")
    
    log_with_category(logger, "TEST", "info", f"ACOUSTID_API_KEY: {acoustid_api_key}")
    log_with_category(logger, "TEST", "info", f"AUDD_API_KEY: {audd_api_key}")
    
    # Créer une session de base de données
    db = SessionLocal()
    
    try:
        # Initialiser le processeur audio
        audio_processor = AudioProcessor(db_session=db)
        
        # Utiliser un fichier audio de test
        test_file_path = Path(project_root) / "backend" / "tests" / "data" / "audio" / "sample1.mp3"
        if not test_file_path.exists():
            log_with_category(logger, "TEST", "error", f"Test audio file not found at {test_file_path}")
            return False
        
        log_with_category(logger, "TEST", "info", f"Using test audio file: {test_file_path}")
        
        # Charger le fichier audio avec librosa
        try:
            audio_data, sample_rate = librosa.load(test_file_path, sr=None)
            log_with_category(logger, "TEST", "info", f"Loaded audio file: {len(audio_data)} samples, {sample_rate} Hz")
            
            # Créer un dictionnaire de métadonnées séparé au lieu d'essayer de l'ajouter à l'objet numpy.ndarray
            metadata = {
                "artist": "Michael Jackson",
                "title": "Thriller"
            }
            log_with_category(logger, "TEST", "info", f"Using metadata: {metadata}")
            
        except Exception as e:
            log_with_category(logger, "TEST", "error", f"Error loading audio file: {str(e)}")
            return False
        
        # Traiter le segment audio
        log_with_category(logger, "TEST", "info", "Processing audio stream...")
        # Passer les métadonnées comme paramètre supplémentaire si nécessaire
        # Si le processeur audio n'accepte pas de métadonnées, commentez cette ligne
        # result = await audio_processor.process_stream(audio_data, metadata=metadata)
        result = await audio_processor.process_stream(audio_data)
        
        log_with_category(logger, "TEST", "info", f"Detection result: {result}")
        
        # Vérifier le résultat
        if result.get("type") == "music":
            log_with_category(logger, "TEST", "info", f"Music detected with source: {result.get('source')}")
            log_with_category(logger, "TEST", "info", f"Track: {result.get('track', {})}")
            log_with_category(logger, "TEST", "info", f"Confidence: {result.get('confidence')}")
            return True
        else:
            log_with_category(logger, "TEST", "warning", f"No music detected: {result}")
            return False
            
    except Exception as e:
        log_with_category(logger, "TEST", "error", f"Error testing detection hierarchy: {str(e)}")
        import traceback
        log_with_category(logger, "TEST", "error", f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        db.close()

async def main():
    """Fonction principale."""
    log_with_category(logger, "TEST", "info", "Starting detection hierarchy test")
    
    result = await test_detection_hierarchy()
    
    if result:
        log_with_category(logger, "TEST", "info", "Detection hierarchy test passed successfully")
    else:
        log_with_category(logger, "TEST", "warning", "Detection hierarchy test failed")

if __name__ == "__main__":
    asyncio.run(main()) 