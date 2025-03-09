#!/usr/bin/env python
"""
Script pour tester le format de la requête AcoustID en suivant la documentation officielle.
Documentation: https://acoustid.org/webservice
"""

import os
import sys
import asyncio
import aiohttp
import logging
import json
import tempfile
import subprocess
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

async def generate_fingerprint(audio_file_path):
    """
    Génère une empreinte digitale à partir d'un fichier audio en utilisant fpcalc.
    
    Note: Nécessite que fpcalc soit installé (inclus dans le package Chromaprint).
    Installation:
    - macOS: brew install chromaprint
    - Ubuntu: apt-get install libchromaprint-tools
    - Windows: Télécharger depuis https://acoustid.org/chromaprint
    """
    try:
        # Utiliser le fpcalc du projet
        fpcalc_path = "/Users/cex/Desktop/sodav-monitor/backend/bin/fpcalc"
        if not os.path.exists(fpcalc_path):
            logger.error("fpcalc not found in the project bin directory.")
            return None, None
        
        # Exécuter fpcalc pour générer l'empreinte
        result = subprocess.run(
            [fpcalc_path, "-json", str(audio_file_path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Error generating fingerprint: {result.stderr}")
            return None, None
        
        # Analyser la sortie JSON
        output = json.loads(result.stdout)
        return output.get("fingerprint"), output.get("duration")
        
    except Exception as e:
        logger.error(f"Error generating fingerprint: {str(e)}")
        return None, None

async def test_acoustid_api_with_fingerprint(api_key, fingerprint, duration):
    """Teste l'API AcoustID avec une empreinte digitale générée par fpcalc."""
    if not api_key:
        logger.error("ACOUSTID_API_KEY not provided")
        return False
    
    if not fingerprint or not duration:
        logger.error("Fingerprint or duration not provided")
        return False
    
    logger.info(f"Testing AcoustID API key: {api_key}")
    logger.info(f"Fingerprint: {fingerprint[:50]}...")
    logger.info(f"Duration: {duration}")
    
    try:
        # Préparer les paramètres pour l'API AcoustID
        params = {
            'client': api_key,
            'format': 'json',
            'meta': 'recordings',
            'fingerprint': fingerprint,
            'duration': str(int(duration))
        }
        
        logger.info("Sending request to AcoustID API")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.acoustid.org/v2/lookup",
                params=params,
                timeout=30
            ) as response:
                if response.status != 200:
                    logger.error(f"AcoustID API error: {response.status}")
                    return False
                
                result = await response.json()
                logger.info(f"AcoustID API response: {result}")
                
                if result.get("status") != "ok":
                    error_msg = result.get("error", {}).get("message", "Unknown error")
                    logger.error(f"AcoustID API error: {error_msg}")
                    return False
                
                if not result.get("results"):
                    logger.warning("No results found in AcoustID response")
                    return False
                
                logger.info("AcoustID API test successful")
                return True
                
    except Exception as e:
        logger.error(f"AcoustID API test failed with error: {str(e)}")
        return False

async def main():
    """Fonction principale."""
    logger.info("Starting AcoustID API test with correct format")
    
    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path("/Users/cex/Desktop/sodav-monitor/.env")
    logger.info(f"Looking for .env file at: {env_path}")
    
    env_vars = load_env_file(env_path)
    
    if not env_vars:
        logger.error("Failed to load environment variables")
        return
    
    acoustid_api_key = env_vars.get("ACOUSTID_API_KEY")
    logger.info(f"ACOUSTID_API_KEY: {acoustid_api_key}")
    
    # Utiliser un fichier audio de test
    test_file_path = Path("/Users/cex/Desktop/sodav-monitor/backend/tests/data/audio/sample1.mp3")
    if not test_file_path.exists():
        logger.error(f"Test audio file not found at {test_file_path}")
        return
    
    # Générer l'empreinte digitale
    fingerprint, duration = await generate_fingerprint(test_file_path)
    if not fingerprint or not duration:
        logger.error("Failed to generate fingerprint")
        return
    
    # Tester l'API AcoustID avec l'empreinte digitale
    result = await test_acoustid_api_with_fingerprint(acoustid_api_key, fingerprint, duration)
    
    if result:
        logger.info("AcoustID API test passed successfully")
    else:
        logger.warning("AcoustID API test failed")

if __name__ == "__main__":
    asyncio.run(main()) 