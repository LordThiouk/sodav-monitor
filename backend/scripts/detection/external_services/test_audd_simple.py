#!/usr/bin/env python
"""
Script simplifié pour tester l'API AudD.
Documentation: https://docs.audd.io/
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import aiohttp

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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


async def test_audd_api_simple(api_key):
    """Teste l'API AudD avec une requête simple."""
    if not api_key:
        logger.error("AUDD_API_KEY not provided")
        return False

    logger.info(f"Testing AudD API key: {api_key}")

    try:
        # Préparer les données pour l'API AudD
        # Utiliser l'endpoint de test qui ne nécessite pas de fichier audio
        data = {
            "api_token": api_key,
            "url": "https://audd.tech/example1.mp3",  # URL d'exemple fournie par AudD
        }

        logger.info("Sending request to AudD API")

        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.audd.io/", data=data, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"AudD API error: {response.status}")
                    text = await response.text()
                    logger.error(f"Response text: {text}")
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
    logger.info("Starting AudD API simple test")

    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path("/Users/cex/Desktop/sodav-monitor/.env")
    logger.info(f"Looking for .env file at: {env_path}")

    env_vars = load_env_file(env_path)

    if not env_vars:
        logger.error("Failed to load environment variables")
        return

    audd_api_key = env_vars.get("AUDD_API_KEY")
    logger.info(f"AUDD_API_KEY: {audd_api_key}")

    # Tester l'API AudD avec une requête simple
    result = await test_audd_api_simple(audd_api_key)

    if result:
        logger.info("AudD API test passed successfully")
    else:
        logger.warning("AudD API test failed")


if __name__ == "__main__":
    asyncio.run(main())
