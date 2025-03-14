#!/usr/bin/env python
"""
Script pour tester les services externes AudD et AcoustID.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from detection.audio_processor.external_services import AcoustIDService, AuddService
from utils.logging_config import log_with_category, setup_logging

logger = setup_logging(__name__)


async def test_acoustid():
    """Teste le service AcoustID."""
    api_key = os.getenv("ACOUSTID_API_KEY")
    if not api_key:
        log_with_category(
            logger, "TEST", "error", "ACOUSTID_API_KEY not found in environment variables"
        )
        return False

    log_with_category(logger, "TEST", "info", f"Testing AcoustID with API key: {api_key}")

    # Utiliser un fichier audio de test
    test_file_path = Path(__file__).parent.parent / "tests" / "data" / "audio" / "sample1.mp3"
    if not test_file_path.exists():
        log_with_category(logger, "TEST", "error", f"Test audio file not found at {test_file_path}")
        return False

    try:
        with open(test_file_path, "rb") as f:
            audio_data = f.read()

        service = AcoustIDService(api_key=api_key)
        result = await service.detect_track_with_retry(audio_data)

        if result:
            log_with_category(logger, "TEST", "info", f"AcoustID test successful: {result}")
            return True
        else:
            log_with_category(logger, "TEST", "warning", "AcoustID test failed: No result returned")
            return False
    except Exception as e:
        log_with_category(logger, "TEST", "error", f"AcoustID test failed with error: {str(e)}")
        return False


async def test_audd():
    """Teste le service AudD."""
    api_key = os.getenv("AUDD_API_KEY")
    if not api_key:
        log_with_category(
            logger, "TEST", "error", "AUDD_API_KEY not found in environment variables"
        )
        return False

    log_with_category(logger, "TEST", "info", f"Testing AudD with API key: {api_key}")

    # Utiliser un fichier audio de test
    test_file_path = Path(__file__).parent.parent / "tests" / "data" / "audio" / "sample1.mp3"
    if not test_file_path.exists():
        log_with_category(logger, "TEST", "error", f"Test audio file not found at {test_file_path}")
        return False

    try:
        with open(test_file_path, "rb") as f:
            audio_data = f.read()

        service = AuddService(api_key=api_key)
        result = await service.detect_track_with_retry(audio_data)

        if result:
            log_with_category(logger, "TEST", "info", f"AudD test successful: {result}")
            return True
        else:
            log_with_category(logger, "TEST", "warning", "AudD test failed: No result returned")
            return False
    except Exception as e:
        log_with_category(logger, "TEST", "error", f"AudD test failed with error: {str(e)}")
        return False


async def main():
    """Fonction principale."""
    log_with_category(logger, "TEST", "info", "Starting external services test")

    acoustid_result = await test_acoustid()
    audd_result = await test_audd()

    if acoustid_result and audd_result:
        log_with_category(logger, "TEST", "info", "All external services tests passed successfully")
    else:
        log_with_category(logger, "TEST", "warning", "Some external services tests failed")
        if not acoustid_result:
            log_with_category(logger, "TEST", "warning", "AcoustID test failed")
        if not audd_result:
            log_with_category(logger, "TEST", "warning", "AudD test failed")


if __name__ == "__main__":
    asyncio.run(main())
