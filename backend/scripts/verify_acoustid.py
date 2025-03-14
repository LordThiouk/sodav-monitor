#!/usr/bin/env python
"""
Script de vérification de l'intégration AcoustID.
Ce script permet de vérifier que l'intégration AcoustID fonctionne correctement.
"""

import asyncio
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from backend.detection.audio_processor.external_services import AcoustIDService, get_fpcalc_path
from backend.utils.logging_config import setup_logging

# Configurer le logging
logger = setup_logging(__name__)


async def verify_acoustid():
    """
    Vérifier que l'intégration AcoustID fonctionne correctement.
    """
    print("=== Vérification de l'intégration AcoustID ===")

    # Vérifier que fpcalc est disponible
    fpcalc_path = get_fpcalc_path()
    if fpcalc_path:
        print(f"✅ fpcalc est disponible à : {fpcalc_path}")
    else:
        print("❌ fpcalc n'est pas disponible sur le système")
        print("   Veuillez installer fpcalc ou vérifier qu'il est dans le PATH")
        return False

    # Initialiser le service AcoustID
    acoustid_service = AcoustIDService()

    # Vérifier que la clé API est configurée
    if not acoustid_service.api_key:
        print("❌ La clé API AcoustID n'est pas configurée")
        print("   Veuillez configurer la clé API dans le fichier .env.development")
        return False

    print(
        f"✅ Clé API AcoustID configurée : {acoustid_service.api_key[:3]}...{acoustid_service.api_key[-3:]}"
    )

    # Tester l'API AcoustID
    print("\nTest de l'API AcoustID...")
    api_works = await acoustid_service.test_acoustid_api()

    if api_works:
        print("✅ L'API AcoustID fonctionne correctement")
    else:
        print("❌ Problème avec l'API AcoustID")
        print("   Veuillez vérifier la clé API et la connexion Internet")
        return False

    print("\n=== Vérification terminée avec succès ===")
    print("L'intégration AcoustID est correctement configurée et fonctionne.")
    return True


if __name__ == "__main__":
    success = asyncio.run(verify_acoustid())
    sys.exit(0 if success else 1)
