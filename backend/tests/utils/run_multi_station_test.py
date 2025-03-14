"""
Script d'exécution pour le test multi-stations.

Ce script permet de lancer facilement le test de détection musicale
avec plusieurs stations simultanées.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("run_multi_station_test.log")
    ]
)
logger = logging.getLogger("run_multi_station_test")

def setup_environment():
    """Configure l'environnement pour le test."""
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
    else:
        logger.warning(f"fpcalc.exe non trouvé à {fpcalc_path}")
        logger.warning("La génération d'empreintes acoustiques pourrait échouer.")
    
    # Charger les variables d'environnement depuis le fichier .env
    try:
        from tests.utils.load_env import load_env_variables
        if load_env_variables():
            logger.info("Variables d'environnement chargées depuis le fichier .env")
        else:
            logger.warning("Impossible de charger les variables d'environnement depuis le fichier .env")
    except ImportError:
        logger.warning("Module load_env non trouvé, les variables d'environnement ne seront pas chargées automatiquement")

def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Test de détection musicale avec plusieurs stations simultanées")
    
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
        "--stations", 
        type=int, 
        default=3,
        help="Nombre de stations à simuler (défaut: 3)"
    )
    
    parser.add_argument(
        "--detections", 
        type=int, 
        default=2,
        help="Nombre de détections par station (défaut: 2)"
    )
    
    parser.add_argument(
        "--duration", 
        type=int, 
        default=15,
        help="Durée de chaque détection en secondes (défaut: 15)"
    )
    
    parser.add_argument(
        "--no-interruption", 
        action="store_true",
        help="Désactiver la simulation d'interruption"
    )
    
    parser.add_argument(
        "--no-manual-selection", 
        action="store_true",
        help="Désactiver la sélection manuelle de piste"
    )
    
    return parser.parse_args()

def main():
    """Fonction principale."""
    # Configurer l'environnement
    setup_environment()
    
    # Parser les arguments
    args = parse_arguments()
    
    # Configurer les clés API si fournies en argument (priorité sur le fichier .env)
    if args.acoustid_key:
        os.environ["ACOUSTID_API_KEY"] = args.acoustid_key
        logger.info("Clé API AcoustID configurée via les arguments")
    
    if args.audd_key:
        os.environ["AUDD_API_KEY"] = args.audd_key
        logger.info("Clé API Audd.io configurée via les arguments")
    
    # Afficher les clés API configurées
    acoustid_key = os.environ.get("ACOUSTID_API_KEY")
    audd_key = os.environ.get("AUDD_API_KEY")
    
    if acoustid_key:
        logger.info(f"Clé API AcoustID configurée: {acoustid_key[:5]}...{acoustid_key[-5:] if len(acoustid_key) > 10 else ''}")
    else:
        logger.warning("Clé API AcoustID non configurée")
    
    if audd_key:
        logger.info(f"Clé API Audd.io configurée: {audd_key[:5]}...{audd_key[-5:] if len(audd_key) > 10 else ''}")
    else:
        logger.warning("Clé API Audd.io non configurée")
    
    # Importer le module de test multi-stations
    try:
        from tests.utils.multi_station_test import run_multi_station_test
        import asyncio
        
        # Exécuter le test
        logger.info("Démarrage du test multi-stations...")
        asyncio.run(run_multi_station_test())
        logger.info("Test multi-stations terminé")
        
    except ImportError as e:
        logger.error(f"Erreur lors de l'importation du module: {e}")
        logger.error("Vérifiez que le fichier multi_station_test.py existe et est accessible")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 