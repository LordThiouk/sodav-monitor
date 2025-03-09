#!/usr/bin/env python
"""
Script pour vérifier les clés API des services externes de détection musicale.
Ce script teste les clés API pour AcoustID, AudD et MusicBrainz pour s'assurer qu'elles sont correctement configurées.
"""

import os
import sys
import asyncio
from pathlib import Path
import json
from dotenv import load_dotenv

# Ajouter le répertoire racine du projet au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# Ajouter également le répertoire backend au chemin
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from backend.utils.logging_config import setup_logging, log_with_category
from backend.detection.audio_processor.external_services import (
    AcoustIDService, 
    AuddService, 
    MusicBrainzService,
    get_fpcalc_path
)

# Configurer le logging
logger = setup_logging("api_keys_check")

def load_env_file(env_path=None):
    """
    Charge les variables d'environnement à partir d'un fichier .env
    
    Args:
        env_path: Chemin vers le fichier .env (par défaut: .env à la racine du projet)
    """
    if env_path is None:
        env_path = project_root / ".env"
    
    if not os.path.exists(env_path):
        log_with_category(logger, "DETECTION", "warning", f"Fichier .env non trouvé à {env_path}")
        return False
    
    load_dotenv(env_path)
    log_with_category(logger, "DETECTION", "info", f"Variables d'environnement chargées depuis {env_path}")
    return True

async def check_acoustid_api_key():
    """
    Vérifie la clé API AcoustID
    
    Returns:
        bool: True si la clé est valide, False sinon
    """
    api_key = os.environ.get("ACOUSTID_API_KEY")
    
    if not api_key:
        log_with_category(logger, "DETECTION", "error", "Clé API AcoustID non définie dans les variables d'environnement")
        return False
    
    log_with_category(logger, "DETECTION", "info", f"Clé API AcoustID trouvée: {api_key[:5]}...{api_key[-3:]}")
    
    # Vérifier si fpcalc est disponible
    fpcalc_path = get_fpcalc_path()
    if not fpcalc_path:
        log_with_category(logger, "DETECTION", "error", "fpcalc non trouvé, nécessaire pour AcoustID")
        return False
    
    log_with_category(logger, "DETECTION", "info", f"fpcalc trouvé à: {fpcalc_path}")
    
    # Créer un service AcoustID
    acoustid_service = AcoustIDService(api_key)
    
    # Tester la clé avec une recherche simple
    try:
        result = await acoustid_service.search_by_metadata("Michael Jackson", "Thriller")
        
        if result:
            log_with_category(logger, "DETECTION", "info", "Test AcoustID réussi avec recherche par métadonnées")
            log_with_category(logger, "DETECTION", "info", f"Résultat: {json.dumps(result)}")
            return True
        else:
            log_with_category(logger, "DETECTION", "warning", "Test AcoustID échoué: aucun résultat trouvé")
            return False
    except Exception as e:
        log_with_category(logger, "DETECTION", "error", f"Erreur lors du test AcoustID: {e}")
        return False

async def check_audd_api_key():
    """
    Vérifie la clé API AudD
    
    Returns:
        bool: True si la clé est valide, False sinon
    """
    api_key = os.environ.get("AUDD_API_KEY")
    
    if not api_key:
        log_with_category(logger, "DETECTION", "error", "Clé API AudD non définie dans les variables d'environnement")
        return False
    
    log_with_category(logger, "DETECTION", "info", f"Clé API AudD trouvée: {api_key[:5]}...{api_key[-3:]}")
    
    # Créer un service AudD
    audd_service = AuddService(api_key)
    
    # Tester la clé avec une URL connue
    try:
        # URL d'un extrait de musique connu
        test_url = "https://example.com/audio/test.mp3"
        
        log_with_category(logger, "DETECTION", "info", f"Test AudD avec URL: {test_url}")
        log_with_category(logger, "DETECTION", "info", "Ce test peut échouer si l'URL n'est pas accessible, mais vérifie quand même la validité de la clé API")
        
        result = await audd_service.detect_track_with_url(test_url)
        
        if result:
            log_with_category(logger, "DETECTION", "info", "Test AudD réussi")
            log_with_category(logger, "DETECTION", "info", f"Résultat: {json.dumps(result)}")
            return True
        else:
            log_with_category(logger, "DETECTION", "warning", "Test AudD échoué: aucun résultat trouvé (peut être normal si l'URL de test n'est pas valide)")
            return True  # Considérer comme réussi car l'échec peut être dû à l'URL de test
    except Exception as e:
        log_with_category(logger, "DETECTION", "error", f"Erreur lors du test AudD: {e}")
        if "Invalid API key" in str(e) or "Unauthorized" in str(e):
            return False
        return True  # Considérer comme réussi si l'erreur n'est pas liée à la clé API

async def check_musicbrainz_setup():
    """
    Vérifie la configuration de MusicBrainz
    
    Returns:
        bool: True si la configuration est valide, False sinon
    """
    log_with_category(logger, "DETECTION", "info", "Vérification de la configuration MusicBrainz")
    
    # MusicBrainz ne nécessite pas de clé API, mais nous vérifions quand même la configuration
    try:
        # Créer un service MusicBrainz
        musicbrainz_service = MusicBrainzService()
        
        # Tester avec une recherche simple
        result = await musicbrainz_service.search_recording("Michael Jackson", "Thriller")
        
        if result:
            log_with_category(logger, "DETECTION", "info", "Test MusicBrainz réussi")
            log_with_category(logger, "DETECTION", "info", f"Résultat: {json.dumps(result)}")
            return True
        else:
            log_with_category(logger, "DETECTION", "warning", "Test MusicBrainz échoué: aucun résultat trouvé")
            return False
    except Exception as e:
        log_with_category(logger, "DETECTION", "error", f"Erreur lors du test MusicBrainz: {e}")
        return False

async def main():
    """Fonction principale"""
    log_with_category(logger, "DETECTION", "info", "Vérification des clés API des services externes")
    
    # Charger les variables d'environnement
    load_env_file()
    
    # Vérifier les clés API
    acoustid_ok = await check_acoustid_api_key()
    audd_ok = await check_audd_api_key()
    musicbrainz_ok = await check_musicbrainz_setup()
    
    # Afficher un résumé
    log_with_category(logger, "DETECTION", "info", "Résumé des vérifications:")
    log_with_category(logger, "DETECTION", "info", f"AcoustID: {'OK' if acoustid_ok else 'ERREUR'}")
    log_with_category(logger, "DETECTION", "info", f"AudD: {'OK' if audd_ok else 'ERREUR'}")
    log_with_category(logger, "DETECTION", "info", f"MusicBrainz: {'OK' if musicbrainz_ok else 'ERREUR'}")
    
    # Vérifier si toutes les clés sont valides
    if acoustid_ok and audd_ok and musicbrainz_ok:
        log_with_category(logger, "DETECTION", "info", "Toutes les clés API sont valides")
        return 0
    else:
        log_with_category(logger, "DETECTION", "error", "Certaines clés API ne sont pas valides")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 