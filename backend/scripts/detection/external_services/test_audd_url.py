#!/usr/bin/env python
"""
Script pour tester la détection de musique par URL avec l'API AudD.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from detection.audio_processor.external_services import AuddService
from utils.logging_config import setup_logging, log_with_category

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

async def test_audd_url():
    """Teste la détection de musique par URL avec l'API AudD."""
    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path("/Users/cex/Desktop/sodav-monitor/.env")
    log_with_category(logger, "TEST", "info", f"Looking for .env file at: {env_path}")
    
    env_vars = load_env_file(env_path)
    
    if not env_vars:
        log_with_category(logger, "TEST", "error", "Failed to load environment variables")
        return False
    
    audd_api_key = env_vars.get("AUDD_API_KEY")
    log_with_category(logger, "TEST", "info", f"AUDD_API_KEY: {audd_api_key}")
    
    if not audd_api_key:
        log_with_category(logger, "TEST", "error", "AUDD_API_KEY not found in environment variables")
        return False
    
    # Initialiser le service AudD
    audd_service = AuddService(api_key=audd_api_key)
    
    # Liste d'URLs à tester
    test_urls = [
        "https://audd.tech/example1.mp3",  # URL d'exemple fournie par AudD
        "https://audd.tech/example2.mp3",  # URL d'exemple fournie par AudD
        "https://audd.tech/example3.mp3"   # URL d'exemple fournie par AudD
    ]
    
    success_count = 0
    
    for url in test_urls:
        log_with_category(logger, "TEST", "info", f"Testing URL: {url}")
        
        try:
            # Utiliser la méthode de détection par URL
            result = await audd_service.detect_track_with_url(url)
            
            if result:
                log_with_category(logger, "TEST", "info", f"Detection successful: {result}")
                success_count += 1
            else:
                log_with_category(logger, "TEST", "warning", f"No result found for URL: {url}")
                
        except Exception as e:
            log_with_category(logger, "TEST", "error", f"Error detecting music from URL: {str(e)}")
    
    log_with_category(logger, "TEST", "info", f"Test completed: {success_count}/{len(test_urls)} URLs successfully detected")
    
    return success_count > 0

async def main():
    """Fonction principale."""
    log_with_category(logger, "TEST", "info", "Starting AudD URL detection test")
    
    result = await test_audd_url()
    
    if result:
        log_with_category(logger, "TEST", "info", "AudD URL detection test passed successfully")
    else:
        log_with_category(logger, "TEST", "warning", "AudD URL detection test failed")

if __name__ == "__main__":
    asyncio.run(main()) 