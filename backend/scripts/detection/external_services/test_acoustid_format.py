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
import pytest
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
project_root = os.path.dirname(parent_dir)  # Racine du projet
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from backend.utils.logging_config import setup_logging, log_with_category
from backend.detection.audio_processor.external_services import get_fpcalc_path

# Configuration du logging
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
                # Supprimer les guillemets autour des valeurs
                env_vars[key] = value.strip('"').strip("'")
    
    return env_vars

def generate_fingerprint(audio_file_path):
    """
    Génère une empreinte digitale à partir d'un fichier audio en utilisant fpcalc.
    
    Note: Nécessite que fpcalc soit installé (inclus dans le package Chromaprint).
    Installation:
    - macOS: brew install chromaprint
    - Ubuntu: apt-get install libchromaprint-tools
    - Windows: Télécharger depuis https://acoustid.org/chromaprint
    """
    try:
        # Utiliser la fonction get_fpcalc_path pour obtenir le chemin de fpcalc
        fpcalc_path = get_fpcalc_path()
        logger.info(f"Using fpcalc at: {fpcalc_path}")
        
        if not fpcalc_path:
            logger.error("fpcalc not found. Please make sure it's installed and available in the PATH or in the project's bin directory.")
            return None, None
        
        # Vérifier que le fichier audio existe
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return None, None
            
        logger.info(f"Generating fingerprint for: {audio_file_path}")
        
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
        logger.info(f"Fingerprint generated successfully. Duration: {output.get('duration')}")
        return output.get("fingerprint"), output.get("duration")
        
    except Exception as e:
        logger.error(f"Error generating fingerprint: {str(e)}")
        return None, None

async def acoustid_api_request(api_key, fingerprint, duration):
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
            'duration': str(int(float(duration)))
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
                
                # Pour un fichier audio synthétique, il est normal de ne pas avoir de résultats
                # Nous vérifions seulement que l'API répond correctement
                logger.info("AcoustID API request successful")
                return True
                
    except Exception as e:
        logger.error(f"AcoustID API test failed with error: {str(e)}")
        return False

# Fixtures pour pytest
@pytest.fixture
def env_vars():
    """Fixture pour charger les variables d'environnement."""
    # Trouver le fichier .env dans le répertoire du projet
    env_path = Path(project_root) / ".env"
    
    logger.info(f"Looking for .env file at: {env_path}")
    env_vars = load_env_file(env_path)
    logger.info(f"Loaded environment variables: {list(env_vars.keys())}")
    return env_vars

@pytest.fixture
def api_key(env_vars):
    """Fixture pour obtenir la clé API AcoustID."""
    api_key = env_vars.get("ACOUSTID_API_KEY")
    logger.info(f"AcoustID API key: {api_key[:5]}..." if api_key else "AcoustID API key not found")
    if not api_key:
        pytest.skip("ACOUSTID_API_KEY not found in .env file")
    return api_key

@pytest.fixture
def test_audio_file():
    """Fixture pour obtenir le chemin du fichier audio de test."""
    # Chercher un fichier audio de test dans le répertoire de tests
    test_dirs = [
        Path(project_root) / "backend" / "tests" / "data" / "audio",
        Path(project_root) / "tests" / "data" / "audio",
        Path(project_root) / "backend" / "tests" / "resources",
        Path(project_root) / "tests" / "resources"
    ]
    
    for test_dir in test_dirs:
        logger.info(f"Looking for test audio files in: {test_dir}")
        if test_dir.exists():
            for file in test_dir.glob("*.mp3"):
                logger.info(f"Found test audio file: {file}")
                return file
    
    # Si aucun fichier n'est trouvé, ignorer le test
    logger.error("No test audio file found")
    pytest.skip("No test audio file found")

@pytest.fixture
def fingerprint_data(test_audio_file):
    """Fixture pour générer l'empreinte digitale."""
    if not test_audio_file:
        logger.error("No test audio file provided")
        pytest.skip("No test audio file provided")
        
    fingerprint, duration = generate_fingerprint(test_audio_file)
    if not fingerprint or not duration:
        logger.error("Failed to generate fingerprint")
        pytest.skip("Failed to generate fingerprint")
    return fingerprint, duration

@pytest.mark.asyncio
async def test_acoustid_api_with_fingerprint(api_key, fingerprint_data):
    """Test de l'API AcoustID avec une empreinte digitale."""
    fingerprint, duration = fingerprint_data
    result = await acoustid_api_request(api_key, fingerprint, duration)
    assert result is True, "AcoustID API test failed"

# Pour exécution en tant que script autonome
async def main():
    """Fonction principale pour l'exécution en tant que script."""
    logger.info("Starting AcoustID API test with correct format")
    
    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path(project_root) / ".env"
    logger.info(f"Looking for .env file at: {env_path}")
    
    env_vars = load_env_file(env_path)
    
    if not env_vars:
        logger.error("Failed to load environment variables")
        return
    
    acoustid_api_key = env_vars.get("ACOUSTID_API_KEY")
    if not acoustid_api_key:
        logger.error("ACOUSTID_API_KEY not found in .env file")
        return
    
    logger.info(f"ACOUSTID_API_KEY: {acoustid_api_key[:5]}...")
    
    # Chercher un fichier audio de test
    test_dirs = [
        Path(project_root) / "backend" / "tests" / "data" / "audio",
        Path(project_root) / "tests" / "data" / "audio",
        Path(project_root) / "backend" / "tests" / "resources",
        Path(project_root) / "tests" / "resources"
    ]
    
    test_file_path = None
    for test_dir in test_dirs:
        if test_dir.exists():
            for file in test_dir.glob("*.mp3"):
                test_file_path = file
                break
        if test_file_path:
            break
    
    if not test_file_path:
        logger.error("No test audio file found")
        return
    
    logger.info(f"Using test audio file: {test_file_path}")
    
    # Générer l'empreinte digitale
    fingerprint, duration = generate_fingerprint(test_file_path)
    if not fingerprint or not duration:
        logger.error("Failed to generate fingerprint")
        return
    
    # Tester l'API AcoustID avec l'empreinte digitale
    result = await acoustid_api_request(acoustid_api_key, fingerprint, duration)
    
    if result:
        logger.info("AcoustID API test passed successfully")
    else:
        logger.warning("AcoustID API test failed")

if __name__ == "__main__":
    asyncio.run(main()) 