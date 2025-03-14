"""
Script pour exécuter tous les tests liés à la durée de lecture.

Ce script exécute tous les tests qui vérifient le bon fonctionnement du système
de suivi de la durée de lecture, y compris les tests unitaires, d'intégration et
les tests avec le simulateur de radio amélioré.
"""

import logging
import os
import subprocess
import sys
from datetime import datetime

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("play_duration_tests.log"),
    ],
)

logger = logging.getLogger(__name__)


def run_command(command):
    """
    Exécute une commande shell et retourne le résultat.

    Args:
        command: Commande à exécuter

    Returns:
        Tuple (code de sortie, sortie standard, sortie d'erreur)
    """
    logger.info(f"Exécution de la commande: {command}")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        universal_newlines=True,
    )
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr


def run_tests():
    """
    Exécute tous les tests liés à la durée de lecture.

    Returns:
        True si tous les tests ont réussi, False sinon
    """
    # Définir les tests à exécuter
    tests = [
        "backend/tests/integration/test_play_duration_tracker.py",
        "backend/tests/integration/test_enhanced_radio_simulator.py",
        "backend/tests/integration/test_play_duration.py",
        "backend/tests/integration/detection/test_play_duration_real_data.py",
    ]

    # Exécuter chaque test
    all_success = True
    for test in tests:
        logger.info(f"Exécution du test: {test}")
        
        # Vérifier si le fichier existe
        if not os.path.exists(test):
            logger.warning(f"Le fichier de test {test} n'existe pas, il sera ignoré")
            continue
            
        # Exécuter le test avec pytest
        command = f"python -m pytest {test} -v"
        returncode, stdout, stderr = run_command(command)
        
        # Afficher la sortie
        logger.info(f"Sortie standard:\n{stdout}")
        if stderr:
            logger.error(f"Sortie d'erreur:\n{stderr}")
            
        # Vérifier le résultat
        if returncode == 0:
            logger.info(f"Test {test} réussi")
        else:
            logger.error(f"Test {test} échoué avec le code de sortie {returncode}")
            all_success = False
            
    return all_success


def main():
    """
    Fonction principale.
    """
    logger.info("Démarrage des tests de durée de lecture")
    start_time = datetime.now()
    
    # Exécuter les tests
    success = run_tests()
    
    # Afficher le résultat
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if success:
        logger.info(f"Tous les tests ont réussi en {duration:.2f} secondes")
    else:
        logger.error(f"Certains tests ont échoué. Durée totale: {duration:.2f} secondes")
        
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 