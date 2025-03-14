#!/usr/bin/env python
"""
Script simplifié pour tester la détection de musique par URL avec l'API AudD.
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


async def detect_track_with_url(api_key, url):
    """
    Détecte une piste en utilisant l'API AudD avec une URL.

    Args:
        api_key: Clé API AudD
        url: URL de l'audio à analyser

    Returns:
        Dict contenant les informations de la piste ou None si aucune correspondance
    """
    try:
        # Préparer les données pour l'API AudD
        data = {"api_token": api_key, "url": url, "return": "apple_music,spotify"}

        logger.info(f"Sending URL request to AudD API: {url}")

        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.audd.io/", data=data, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"AudD API error: {response.status}")
                    text = await response.text()
                    logger.error(f"Response text: {text}")
                    return None

                result = await response.json()
                logger.info(f"AudD API response: {result}")

                if result.get("status") == "error":
                    error_msg = result.get("error", {}).get("error_message", "Unknown error")
                    logger.error(f"AudD API error: {error_msg}")
                    return None

                if not result.get("result"):
                    return None

                track = result["result"]
                return {
                    "title": track.get("title", "Unknown"),
                    "artist": track.get("artist", "Unknown Artist"),
                    "album": track.get("album", "Unknown Album"),
                    "confidence": 0.8,  # Default confidence for URL-based detection
                    "source": "audd",
                    "id": track.get("song_link", ""),
                }

    except Exception as e:
        logger.error(f"Error detecting music from URL: {str(e)}")
        return None


async def test_audd_url():
    """Teste la détection de musique par URL avec l'API AudD."""
    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path("/Users/cex/Desktop/sodav-monitor/.env")
    logger.info(f"Looking for .env file at: {env_path}")

    env_vars = load_env_file(env_path)

    if not env_vars:
        logger.error("Failed to load environment variables")
        return False

    audd_api_key = env_vars.get("AUDD_API_KEY")
    logger.info(f"AUDD_API_KEY: {audd_api_key}")

    if not audd_api_key:
        logger.error("AUDD_API_KEY not found in environment variables")
        return False

    # Liste d'URLs à tester
    test_urls = [
        "https://audd.tech/example1.mp3",  # URL d'exemple fournie par AudD
        "https://audd.tech/example2.mp3",  # URL d'exemple fournie par AudD
        "https://audd.tech/example3.mp3",  # URL d'exemple fournie par AudD
    ]

    success_count = 0

    for url in test_urls:
        logger.info(f"Testing URL: {url}")

        # Utiliser la méthode de détection par URL
        result = await detect_track_with_url(audd_api_key, url)

        if result:
            logger.info(f"Detection successful: {result}")
            success_count += 1
        else:
            logger.warning(f"No result found for URL: {url}")

    logger.info(f"Test completed: {success_count}/{len(test_urls)} URLs successfully detected")

    return success_count > 0


async def main():
    """Fonction principale."""
    logger.info("Starting AudD URL detection test")

    result = await test_audd_url()

    if result:
        logger.info("AudD URL detection test passed successfully")
    else:
        logger.warning("AudD URL detection test failed")


if __name__ == "__main__":
    asyncio.run(main())
