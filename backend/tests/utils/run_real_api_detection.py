"""
Script pour exécuter le test de détection musicale avec de vrais appels API.

Ce script permet de lancer facilement le test de détection musicale qui utilise
de vrais appels API (locale, MusicBrainz, Audd.io) avec le simulateur de radio amélioré.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("real_api_detection.log")
    ]
)
logger = logging.getLogger("run_real_api_detection")

# Importer le test de détection avec API réelles
try:
    from backend.tests.utils.real_api_detection_test import test_real_api_detection
except ImportError:
    logger.error("Impossible d'importer le module de test. Vérifiez que le fichier real_api_detection_test.py existe.")
    sys.exit(1)


def setup_api_keys():
    """Configure les clés API nécessaires pour les tests."""
    # Vérifier si les clés API sont déjà définies
    acoustid_key = os.environ.get("ACOUSTID_API_KEY")
    audd_key = os.environ.get("AUDD_API_KEY")
    
    if not acoustid_key:
        logger.warning("Clé API AcoustID non définie dans les variables d'environnement.")
        acoustid_input = input("Entrez votre clé API AcoustID (laissez vide pour ignorer): ").strip()
        if acoustid_input:
            os.environ["ACOUSTID_API_KEY"] = acoustid_input
            logger.info("Clé API AcoustID configurée.")
    else:
        logger.info("Clé API AcoustID déjà configurée.")
    
    if not audd_key:
        logger.warning("Clé API Audd.io non définie dans les variables d'environnement.")
        audd_input = input("Entrez votre clé API Audd.io (laissez vide pour ignorer): ").strip()
        if audd_input:
            os.environ["AUDD_API_KEY"] = audd_input
            logger.info("Clé API Audd.io configurée.")
    else:
        logger.info("Clé API Audd.io déjà configurée.")


def check_audio_files():
    """Vérifie si des fichiers audio sont disponibles pour les tests."""
    # Répertoire des fichiers audio
    audio_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "audio" / "senegal"
    
    if not audio_dir.exists() or not any(audio_dir.glob("*.mp3")):
        logger.error(f"Aucun fichier audio trouvé dans {audio_dir}")
        logger.info("Veuillez d'abord télécharger ou copier des fichiers audio dans ce répertoire.")
        
        # Proposer de copier des fichiers audio
        copy_files = input("Voulez-vous copier des fichiers audio depuis le dossier Téléchargements? (o/n): ").strip().lower()
        if copy_files in ["o", "oui"]:
            try:
                from backend.tests.utils.copy_downloaded_audio import copy_audio_files
                copied = copy_audio_files()
                if copied > 0:
                    logger.info(f"{copied} fichiers audio copiés avec succès.")
                    return True
                else:
                    logger.error("Aucun fichier audio n'a été copié.")
                    return False
            except ImportError:
                logger.error("Impossible d'importer le module de copie de fichiers audio.")
                return False
        return False
    
    return True


async def main():
    """Fonction principale pour exécuter le test."""
    logger.info("Démarrage du test de détection musicale avec API réelles")
    
    # Vérifier les fichiers audio
    if not check_audio_files():
        logger.error("Test annulé: fichiers audio manquants")
        return
    
    # Configurer les clés API
    setup_api_keys()
    
    # Exécuter le test
    try:
        logger.info("Exécution du test de détection...")
        await test_real_api_detection()
        logger.info("Test terminé avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du test: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    # Exécuter le test
    asyncio.run(main()) 