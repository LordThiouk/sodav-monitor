#!/usr/bin/env python
"""
Script simplifié pour tester l'API AcoustID en utilisant uniquement la durée du fichier audio.
Documentation: https://acoustid.org/webservice
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


async def test_acoustid_api_simple(api_key):
    """Teste l'API AcoustID avec une requête simple."""
    if not api_key:
        logger.error("ACOUSTID_API_KEY not provided")
        return False

    logger.info(f"Testing AcoustID API key: {api_key}")

    try:
        # Préparer les paramètres pour l'API AcoustID
        # Recherche simple par artiste et titre
        params = {
            "client": api_key,
            "format": "json",
            "meta": "recordings",
            "artist": "Michael Jackson",
            "title": "Thriller",
        }

        logger.info("Sending request to AcoustID API")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.acoustid.org/v2/lookup", params=params, timeout=30
            ) as response:
                if response.status != 200:
                    logger.error(f"AcoustID API error: {response.status}")
                    text = await response.text()
                    logger.error(f"Response text: {text}")
                    return False

                result = await response.json()
                logger.info(f"AcoustID API response: {result}")

                if result.get("status") != "ok":
                    error_msg = result.get("error", {}).get("message", "Unknown error")
                    logger.error(f"AcoustID API error: {error_msg}")
                    return False

                logger.info("AcoustID API test successful")
                return True

    except Exception as e:
        logger.error(f"AcoustID API test failed with error: {str(e)}")
        return False


async def main():
    """Fonction principale."""
    logger.info("Starting AcoustID API simple test")

    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path("/Users/cex/Desktop/sodav-monitor/.env")
    logger.info(f"Looking for .env file at: {env_path}")

    env_vars = load_env_file(env_path)

    if not env_vars:
        logger.error("Failed to load environment variables")
        return

    acoustid_api_key = env_vars.get("ACOUSTID_API_KEY")
    logger.info(f"ACOUSTID_API_KEY: {acoustid_api_key}")

    # Tester l'API AcoustID avec une requête simple
    result = await test_acoustid_api_simple(acoustid_api_key)

    if result:
        logger.info("AcoustID API test passed successfully")
    else:
        logger.warning("AcoustID API test failed")


if __name__ == "__main__":
    asyncio.run(main())
