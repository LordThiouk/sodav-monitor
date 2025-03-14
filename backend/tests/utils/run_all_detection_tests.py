"""
Script pour exécuter tous les tests de détection musicale en séquence.

Ce script exécute les différents tests de détection musicale dans l'ordre suivant :
1. Test simple
2. Test avec API réelles
3. Test multi-stations
4. Visualisation des résultats
"""

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("run_all_detection_tests.log")
    ]
)
logger = logging.getLogger("run_all_detection_tests")


def setup_environment():
    """Configure l'environnement pour les tests."""
    # Ajouter le répertoire parent au PYTHONPATH
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = current_dir.parent.parent
    
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
        logger.info(f"Ajout de {backend_dir} au PYTHONPATH")
    
    # Vérifier si le répertoire des données audio existe
    audio_dir = current_dir.parent / "data" / "audio" / "senegal"
    if not audio_dir.exists():
        audio_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Répertoire créé: {audio_dir}")
    
    # Vérifier si fpcalc.exe existe
    fpcalc_path = backend_dir / "bin" / "fpcalc.exe"
    if fpcalc_path.exists():
        os.environ["FPCALC_PATH"] = str(fpcalc_path)
        logger.info(f"fpcalc.exe trouvé à {fpcalc_path}")
        return True
    else:
        logger.warning(f"fpcalc.exe non trouvé à {fpcalc_path}")
        logger.warning("La génération d'empreintes acoustiques pourrait échouer")
        return False


def check_audio_files():
    """
    Vérifie si des fichiers audio sont disponibles pour les tests.
    
    Returns:
        True si des fichiers audio sont disponibles, False sinon
    """
    # Répertoire des fichiers audio
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    audio_dir = current_dir.parent / "data" / "audio" / "senegal"
    
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
        
        # Proposer de télécharger des fichiers audio
        download_files = input("Voulez-vous télécharger des fichiers audio de test? (o/n): ").strip().lower()
        if download_files in ["o", "oui"]:
            try:
                from backend.tests.utils.download_test_audio_direct import download_all_audio
                downloaded = download_all_audio()
                if downloaded > 0:
                    logger.info(f"{downloaded} fichiers audio téléchargés avec succès.")
                    return True
                else:
                    logger.error("Aucun fichier audio n'a été téléchargé.")
                    return False
            except ImportError:
                logger.error("Impossible d'importer le module de téléchargement de fichiers audio.")
                return False
        
        return False
    
    return True


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


def run_command(command, description):
    """
    Exécute une commande et affiche sa sortie.
    
    Args:
        command: Commande à exécuter
        description: Description de la commande
        
    Returns:
        True si la commande a réussi, False sinon
    """
    logger.info(f"Exécution de {description}...")
    
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True
        )
        
        # Afficher la sortie en temps réel
        while True:
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        # Récupérer le code de retour
        return_code = process.poll()
        
        if return_code == 0:
            logger.info(f"{description} terminé avec succès")
            return True
        else:
            logger.error(f"{description} a échoué avec le code de retour {return_code}")
            return False
    
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de {description}: {e}")
        return False


def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        Arguments parsés
    """
    parser = argparse.ArgumentParser(description="Exécution de tous les tests de détection musicale")
    
    parser.add_argument(
        "--acoustid-key",
        dest="acoustid_key",
        help="Clé API AcoustID"
    )
    
    parser.add_argument(
        "--audd-key",
        dest="audd_key",
        help="Clé API Audd.io"
    )
    
    parser.add_argument(
        "--skip-simple",
        action="store_true",
        help="Ignorer le test simple"
    )
    
    parser.add_argument(
        "--skip-real-api",
        action="store_true",
        help="Ignorer le test avec API réelles"
    )
    
    parser.add_argument(
        "--skip-multi-station",
        action="store_true",
        help="Ignorer le test multi-stations"
    )
    
    parser.add_argument(
        "--skip-visualization",
        action="store_true",
        help="Ignorer la visualisation des résultats"
    )
    
    return parser.parse_args()


def main():
    """Fonction principale."""
    # Parser les arguments
    args = parse_arguments()
    
    # Configurer l'environnement
    if not setup_environment():
        logger.warning("L'environnement n'est pas correctement configuré")
    
    # Vérifier les fichiers audio
    if not check_audio_files():
        logger.error("Tests annulés: fichiers audio manquants")
        return
    
    # Configurer les clés API
    if args.acoustid_key:
        os.environ["ACOUSTID_API_KEY"] = args.acoustid_key
        logger.info("Clé API AcoustID configurée via les arguments")
    
    if args.audd_key:
        os.environ["AUDD_API_KEY"] = args.audd_key
        logger.info("Clé API Audd.io configurée via les arguments")
    
    if not args.acoustid_key or not args.audd_key:
        setup_api_keys()
    
    # Exécuter les tests
    results = {}
    
    # 1. Test simple
    if not args.skip_simple:
        results["simple"] = run_command(
            "python -m backend.tests.utils.simple_detection_test",
            "Test simple"
        )
    else:
        logger.info("Test simple ignoré")
    
    # 2. Test avec API réelles
    if not args.skip_real_api:
        results["real_api"] = run_command(
            "python -m backend.tests.utils.run_real_api_detection",
            "Test avec API réelles"
        )
    else:
        logger.info("Test avec API réelles ignoré")
    
    # 3. Test multi-stations
    if not args.skip_multi_station:
        results["multi_station"] = run_command(
            "python -m backend.tests.utils.run_multi_station_test",
            "Test multi-stations"
        )
    else:
        logger.info("Test multi-stations ignoré")
    
    # 4. Visualisation des résultats
    if not args.skip_visualization:
        results["visualization"] = run_command(
            "python -m backend.tests.utils.run_visualize_detection_results",
            "Visualisation des résultats"
        )
    else:
        logger.info("Visualisation des résultats ignorée")
    
    # Afficher le résumé
    logger.info("\nRésumé des tests:")
    for test, result in results.items():
        status = "Réussi" if result else "Échoué"
        logger.info(f"- {test}: {status}")
    
    # Vérifier si tous les tests ont réussi
    if all(results.values()):
        logger.info("\nTous les tests ont réussi!")
    else:
        logger.warning("\nCertains tests ont échoué")


if __name__ == "__main__":
    main() 