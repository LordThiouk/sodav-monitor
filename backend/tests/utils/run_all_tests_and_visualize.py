#!/usr/bin/env python
"""
Script pour exécuter tous les tests de détection musicale et visualiser les résultats.

Ce script exécute les tests suivants dans l'ordre :
1. Test de détection simple
2. Test avec API réelle
3. Test multi-stations
4. Visualisation des résultats

Les variables d'environnement sont chargées automatiquement depuis le fichier .env.
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path
import dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("run_all_tests_and_visualize.log")
    ]
)
logger = logging.getLogger("run_all_tests_and_visualize")

def load_env_variables():
    """Charge les variables d'environnement depuis le fichier .env."""
    env_file = Path(__file__).parent.parent.parent.parent / ".env"
    if env_file.exists():
        logger.info(f"Chargement des variables d'environnement depuis {env_file}")
        loaded_env = dotenv.load_dotenv(env_file)
        if loaded_env:
            env_count = len(os.environ)
            logger.info(f"Variables d'environnement chargées avec succès: {env_count} variables")
            
            # Vérifier les clés API importantes
            acoustid_key = os.environ.get("ACOUSTID_API_KEY")
            audd_key = os.environ.get("AUDD_API_KEY")
            
            if acoustid_key:
                logger.info(f"Clé API AcoustID: {acoustid_key}")
            else:
                logger.warning("Clé API AcoustID non trouvée dans les variables d'environnement")
            
            if audd_key:
                logger.info(f"Clé API Audd.io: {audd_key}")
            else:
                logger.warning("Clé API Audd.io non trouvée dans les variables d'environnement")
            
            return True
        else:
            logger.error("Erreur lors du chargement des variables d'environnement")
    else:
        logger.error(f"Fichier .env non trouvé à {env_file}")
    
    return False

def run_command(cmd, description):
    """Exécute une commande et affiche son résultat."""
    logger.info(f"Exécution de {description}...")
    logger.info(f"Commande: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"{description} terminé avec succès")
        logger.info(f"Sortie: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'exécution de {description}")
        logger.error(f"Code de sortie: {e.returncode}")
        logger.error(f"Erreur: {e.stderr}")
        return False

def run_simple_test():
    """Exécute le test de détection simple."""
    cmd = [
        sys.executable,
        "-m",
        "tests.utils.simple_detection_test"
    ]
    return run_command(cmd, "Test de détection simple")

def run_real_api_test():
    """Exécute le test avec API réelle."""
    cmd = [
        sys.executable,
        "-m",
        "tests.utils.run_real_api_detection"
    ]
    return run_command(cmd, "Test avec API réelle")

def run_multi_station_test():
    """Exécute le test multi-stations."""
    cmd = [
        sys.executable,
        "-m",
        "tests.utils.multi_station_test"
    ]
    return run_command(cmd, "Test multi-stations")

def run_visualization():
    """Exécute la visualisation des résultats."""
    cmd = [
        sys.executable,
        "-m",
        "tests.utils.run_visualize_with_env"
    ]
    return run_command(cmd, "Visualisation des résultats")

def main():
    """Fonction principale qui exécute tous les tests et la visualisation."""
    logger.info("=== DÉBUT DE L'EXÉCUTION DE TOUS LES TESTS ET VISUALISATIONS ===")
    
    # Charger les variables d'environnement
    if not load_env_variables():
        logger.error("Impossible de charger les variables d'environnement. Arrêt des tests.")
        return 1
    
    # Créer le répertoire de visualisations s'il n'existe pas
    visualizations_dir = Path(__file__).parent.parent.parent / "visualizations"
    visualizations_dir.mkdir(exist_ok=True)
    
    # Exécuter les tests
    tests_results = {}
    
    # Test de détection simple
    tests_results["simple"] = run_simple_test()
    time.sleep(1)  # Pause pour s'assurer que les logs sont bien écrits
    
    # Test avec API réelle
    tests_results["real_api"] = run_real_api_test()
    time.sleep(1)  # Pause pour s'assurer que les logs sont bien écrits
    
    # Test multi-stations
    tests_results["multi_station"] = run_multi_station_test()
    time.sleep(1)  # Pause pour s'assurer que les logs sont bien écrits
    
    # Visualisation des résultats
    if any(tests_results.values()):
        tests_results["visualization"] = run_visualization()
    else:
        logger.error("Aucun test n'a réussi. La visualisation ne sera pas exécutée.")
        tests_results["visualization"] = False
    
    # Résumé des résultats
    logger.info("=== RÉSUMÉ DES RÉSULTATS ===")
    for test_name, result in tests_results.items():
        status = "RÉUSSI" if result else "ÉCHOUÉ"
        logger.info(f"{test_name}: {status}")
    
    # Vérifier si tous les tests ont réussi
    if all(tests_results.values()):
        logger.info("Tous les tests et visualisations ont réussi !")
        return 0
    else:
        logger.error("Certains tests ou visualisations ont échoué.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 