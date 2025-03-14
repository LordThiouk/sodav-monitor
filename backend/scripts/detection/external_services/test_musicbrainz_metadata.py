#!/usr/bin/env python
"""
Script pour tester la recherche par métadonnées avec MusicBrainz.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from detection.audio_processor.external_services import AcoustIDService
from utils.logging_config import log_with_category, setup_logging

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


async def test_musicbrainz_metadata():
    """Teste la recherche par métadonnées avec MusicBrainz."""
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
        log_with_category(
            logger, "TEST", "error", "ACOUSTID_API_KEY not found in environment variables"
        )
        return False

    # Initialiser le service AcoustID
    acoustid_service = AcoustIDService(api_key=acoustid_api_key)

    # Liste de pistes à tester
    test_tracks = [
        {"artist": "Michael Jackson", "title": "Thriller"},
        {"artist": "Queen", "title": "Bohemian Rhapsody"},
        {"artist": "The Beatles", "title": "Hey Jude"},
        {"artist": "Youssou N'Dour", "title": "7 Seconds"},
        {"artist": "Baaba Maal", "title": "African Woman"},
    ]

    success_count = 0

    for track in test_tracks:
        artist = track["artist"]
        title = track["title"]

        log_with_category(logger, "TEST", "info", f"Testing search for: {title} by {artist}")

        try:
            # Utiliser la méthode de recherche par métadonnées
            result = await acoustid_service.search_by_metadata(artist, title)

            if result:
                log_with_category(logger, "TEST", "info", f"Search successful: {result}")
                success_count += 1
            else:
                log_with_category(
                    logger, "TEST", "warning", f"No result found for: {title} by {artist}"
                )

        except Exception as e:
            log_with_category(logger, "TEST", "error", f"Error searching for track: {str(e)}")

    log_with_category(
        logger,
        "TEST",
        "info",
        f"Test completed: {success_count}/{len(test_tracks)} tracks successfully found",
    )

    return success_count > 0


async def main():
    """Fonction principale."""
    log_with_category(logger, "TEST", "info", "Starting MusicBrainz metadata search test")

    result = await test_musicbrainz_metadata()

    if result:
        log_with_category(
            logger, "TEST", "info", "MusicBrainz metadata search test passed successfully"
        )
    else:
        log_with_category(logger, "TEST", "warning", "MusicBrainz metadata search test failed")


if __name__ == "__main__":
    asyncio.run(main())
