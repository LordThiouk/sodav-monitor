#!/usr/bin/env python
"""
Script pour tester la nouvelle implémentation d'AcoustID avec fpcalc.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Ajouter le répertoire racine du projet au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Ajouter également le répertoire backend au chemin
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from backend.detection.audio_processor.external_services import AcoustIDService
from backend.utils.logging_config import setup_logging, log_with_category

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
                env_vars[key] = value
    
    return env_vars

async def test_acoustid_fpcalc():
    """Teste la détection de musique avec AcoustID en utilisant fpcalc."""
    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path("/Users/cex/Desktop/sodav-monitor/.env")
    log_with_category(logger, "TEST", "info", f"Looking for .env file at: {env_path}")
    
    env_vars = load_env_file(env_path)
    
    if not env_vars:
        log_with_category(logger, "TEST", "error", "Failed to load environment variables")
        return False
    
    acoustid_api_key = env_vars.get("ACOUSTID_API_KEY")
    log_with_category(logger, "TEST", "info", f"ACOUSTID_API_KEY: {acoustid_api_key}")
    
    if not acoustid_api_key:
        log_with_category(logger, "TEST", "error", "ACOUSTID_API_KEY not found in environment variables")
        return False
    
    # Initialiser le service AcoustID
    acoustid_service = AcoustIDService(api_key=acoustid_api_key)
    
    # Utiliser un fichier audio de test
    test_file_path = Path(project_root) / "backend" / "tests" / "data" / "audio" / "sample1.mp3"
    if not test_file_path.exists():
        log_with_category(logger, "TEST", "error", f"Test audio file not found at {test_file_path}")
        return False
    
    log_with_category(logger, "TEST", "info", f"Using test audio file: {test_file_path}")
    
    try:
        # Lire le fichier audio
        with open(test_file_path, "rb") as f:
            audio_data = f.read()
        
        log_with_category(logger, "TEST", "info", f"Read {len(audio_data)} bytes from audio file")
        
        # Utiliser la méthode de détection avec fpcalc
        log_with_category(logger, "TEST", "info", "Detecting track with AcoustID using fpcalc...")
        result = await acoustid_service.detect_track(audio_data)
        
        if result:
            log_with_category(logger, "TEST", "info", f"Detection successful: {result}")
            return True
        else:
            log_with_category(logger, "TEST", "warning", "No result found for audio file")
            return False
            
    except Exception as e:
        log_with_category(logger, "TEST", "error", f"Error detecting music with AcoustID: {str(e)}")
        return False

async def main():
    """Fonction principale."""
    log_with_category(logger, "TEST", "info", "Starting AcoustID fpcalc test")
    
    result = await test_acoustid_fpcalc()
    
    if result:
        log_with_category(logger, "TEST", "info", "AcoustID fpcalc test passed successfully")
    else:
        log_with_category(logger, "TEST", "warning", "AcoustID fpcalc test failed")

if __name__ == "__main__":
    asyncio.run(main()) 