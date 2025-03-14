"""
Script pour exécuter les tests de détection musicale en chargeant d'abord les variables d'environnement.

Ce script charge les variables d'environnement à partir du fichier .env,
puis exécute les tests de détection musicale spécifiés.
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.append(str(Path(os.path.dirname(os.path.abspath(__file__))).parent.parent))

# Importer le module de chargement des variables d'environnement
from tests.utils.load_env import load_env_variables

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("run_tests_with_env.log")
    ]
)
logger = logging.getLogger("run_tests_with_env")

def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Arguments parsés
    """
    parser = argparse.ArgumentParser(description="Exécuter les tests de détection musicale")
    parser.add_argument(
        "--test", 
        choices=["simple", "real", "multi", "all", "visualize"],
        default="all",
        help="Type de test à exécuter (simple, real, multi, all, visualize)"
    )
    parser.add_argument(
        "--skip-env", 
        action="store_true",
        help="Ne pas charger les variables d'environnement"
    )
    
    return parser.parse_args()

def run_test(test_module):
    """
    Exécute un module de test spécifique.
    
    Args:
        test_module: Nom du module de test à exécuter
        
    Returns:
        int: Code de retour de la commande
    """
    logger.info(f"Exécution du test: {test_module}")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", test_module],
            check=True,
            capture_output=False
        )
        return result.returncode
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'exécution du test {test_module}: {e}")
        return e.returncode

def main():
    """
    Fonction principale pour exécuter les tests.
    """
    args = parse_arguments()
    
    # Charger les variables d'environnement si nécessaire
    if not args.skip_env:
        logger.info("Chargement des variables d'environnement...")
        if not load_env_variables():
            logger.error("Impossible de charger les variables d'environnement. Arrêt des tests.")
            return 1
    
    # Définir les modules de test à exécuter
    test_modules = []
    
    if args.test == "simple" or args.test == "all":
        test_modules.append("tests.utils.simple_detection_test")
    
    if args.test == "real" or args.test == "all":
        test_modules.append("tests.utils.run_real_api_detection")
    
    if args.test == "multi" or args.test == "all":
        test_modules.append("tests.utils.run_multi_station_test")
    
    if args.test == "visualize" or args.test == "all":
        test_modules.append("tests.utils.run_visualize_detection_results")
    
    # Exécuter les tests
    results = {}
    for module in test_modules:
        results[module] = run_test(module)
    
    # Afficher les résultats
    logger.info("Résultats des tests:")
    for module, returncode in results.items():
        status = "Succès" if returncode == 0 else f"Échec (code {returncode})"
        logger.info(f"  {module}: {status}")
    
    # Retourner 0 si tous les tests ont réussi, 1 sinon
    return 0 if all(returncode == 0 for returncode in results.values()) else 1

if __name__ == "__main__":
    sys.exit(main()) 