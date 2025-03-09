#!/usr/bin/env python
"""
Script simple pour tester les clés API d'AudD et AcoustID.
"""

import os
import sys
import asyncio
import aiohttp
import logging
import re
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

async def test_acoustid_api(api_key):
    """Teste la clé API AcoustID."""
    if not api_key:
        logger.error("ACOUSTID_API_KEY not provided")
        return False
    
    logger.info(f"Testing AcoustID API key: {api_key}")
    
    # Utiliser un fichier audio de test
    test_file_path = Path(__file__).parent.parent / "tests" / "data" / "audio" / "sample1.mp3"
    if not test_file_path.exists():
        logger.error(f"Test audio file not found at {test_file_path}")
        return False
    
    try:
        # Préparer les données pour l'API AcoustID
        form_data = aiohttp.FormData()
        form_data.add_field('client', api_key)
        form_data.add_field('format', 'json')
        form_data.add_field('meta', 'recordings')
        
        with open(test_file_path, "rb") as f:
            audio_data = f.read()
            form_data.add_field('fingerprint', audio_data)
        
        logger.info("Sending request to AcoustID API")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.acoustid.org/v2/lookup",
                data=form_data,
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

async def test_audd_api(api_key):
    """Teste la clé API AudD."""
    if not api_key:
        logger.error("AUDD_API_KEY not provided")
        return False
    
    logger.info(f"Testing AudD API key: {api_key}")
    
    # Utiliser un fichier audio de test
    test_file_path = Path(__file__).parent.parent / "tests" / "data" / "audio" / "sample1.mp3"
    if not test_file_path.exists():
        logger.error(f"Test audio file not found at {test_file_path}")
        return False
    
    try:
        # Préparer les données pour l'API AudD
        data = aiohttp.FormData()
        data.add_field("api_token", api_key)
        
        with open(test_file_path, "rb") as f:
            audio_data = f.read()
            data.add_field("file", audio_data)
        
        logger.info("Sending request to AudD API")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.audd.io/",
                data=data,
                timeout=30
            ) as response:
                if response.status != 200:
                    logger.error(f"AudD API error: {response.status}")
                    return False
                
                result = await response.json()
                logger.info(f"AudD API response: {result}")
                
                if result.get("status") == "error":
                    logger.error(f"AudD API error: {result.get('error')}")
                    return False
                
                logger.info("AudD API test successful")
                return True
                
    except Exception as e:
        logger.error(f"AudD API test failed with error: {str(e)}")
        return False

async def main():
    """Fonction principale."""
    logger.info("Starting API key tests")
    
    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path(__file__).parent.parent.parent / ".env"  # Remonter d'un niveau supplémentaire
    
    # Si le chemin n'existe pas, essayer le chemin relatif
    if not env_path.exists():
        env_path = Path("/Users/cex/Desktop/sodav-monitor/.env")
        
    logger.info(f"Looking for .env file at: {env_path}")
    
    env_vars = load_env_file(env_path)
    
    if not env_vars:
        logger.error("Failed to load environment variables")
        return
    
    logger.info(f"Loaded {len(env_vars)} environment variables")
    
    acoustid_api_key = env_vars.get("ACOUSTID_API_KEY")
    audd_api_key = env_vars.get("AUDD_API_KEY")
    
    logger.info(f"ACOUSTID_API_KEY: {acoustid_api_key}")
    logger.info(f"AUDD_API_KEY: {audd_api_key}")
    
    acoustid_result = await test_acoustid_api(acoustid_api_key)
    audd_result = await test_audd_api(audd_api_key)
    
    if acoustid_result and audd_result:
        logger.info("All API key tests passed successfully")
    else:
        logger.warning("Some API key tests failed")
        if not acoustid_result:
            logger.warning("AcoustID API key test failed")
        if not audd_result:
            logger.warning("AudD API key test failed")

if __name__ == "__main__":
    asyncio.run(main())