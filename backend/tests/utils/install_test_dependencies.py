"""
Script pour installer les dépendances nécessaires aux tests de détection musicale.

Ce script vérifie et installe les dépendances Python requises pour exécuter
les tests de détection musicale et la visualisation des résultats.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("install_test_dependencies.log")
    ]
)
logger = logging.getLogger("install_test_dependencies")

# Liste des dépendances requises
REQUIRED_PACKAGES = [
    "matplotlib",
    "pandas",
    "numpy",
    "tabulate",
    "requests",
    "pydub",
    "soundfile",
    "librosa",
    "scipy"
]

# Dépendances optionnelles (pour des fonctionnalités avancées)
OPTIONAL_PACKAGES = [
    "seaborn",  # Pour des visualisations plus avancées
    "plotly",   # Pour des graphiques interactifs
    "tqdm",     # Pour les barres de progression
    "pytest",   # Pour exécuter les tests unitaires
    "pytest-asyncio"  # Pour les tests asynchrones
]


def check_package_installed(package_name):
    """
    Vérifie si un package Python est installé.
    
    Args:
        package_name: Nom du package à vérifier
        
    Returns:
        True si le package est installé, False sinon
    """
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def install_package(package_name):
    """
    Installe un package Python.
    
    Args:
        package_name: Nom du package à installer
        
    Returns:
        True si l'installation a réussi, False sinon
    """
    try:
        logger.info(f"Installation de {package_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        logger.info(f"{package_name} installé avec succès")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'installation de {package_name}: {e}")
        return False


def check_and_install_dependencies(packages, optional=False):
    """
    Vérifie et installe une liste de dépendances.
    
    Args:
        packages: Liste des packages à vérifier et installer
        optional: Si True, les packages sont considérés comme optionnels
        
    Returns:
        Nombre de packages installés avec succès
    """
    installed_count = 0
    missing_packages = []
    
    # Vérifier quels packages sont déjà installés
    for package in packages:
        if check_package_installed(package):
            logger.info(f"{package} est déjà installé")
        else:
            missing_packages.append(package)
    
    # Demander confirmation pour l'installation des packages manquants
    if missing_packages:
        package_type = "optionnels" if optional else "requis"
        logger.info(f"Les packages {package_type} suivants ne sont pas installés: {', '.join(missing_packages)}")
        
        if optional:
            install_optional = input(f"Voulez-vous installer les packages optionnels? (o/n): ").strip().lower()
            if install_optional not in ["o", "oui", "y", "yes"]:
                logger.info("Installation des packages optionnels annulée")
                return 0
        
        # Installer les packages manquants
        for package in missing_packages:
            if install_package(package):
                installed_count += 1
    else:
        package_type = "optionnels" if optional else "requis"
        logger.info(f"Tous les packages {package_type} sont déjà installés")
    
    return installed_count


def check_fpcalc():
    """
    Vérifie si fpcalc.exe est disponible.
    
    Returns:
        True si fpcalc.exe est disponible, False sinon
    """
    # Chemin vers fpcalc.exe
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = current_dir.parent.parent
    fpcalc_path = backend_dir / "bin" / "fpcalc.exe"
    
    if fpcalc_path.exists():
        logger.info(f"fpcalc.exe trouvé à {fpcalc_path}")
        return True
    else:
        logger.warning(f"fpcalc.exe non trouvé à {fpcalc_path}")
        logger.warning("La génération d'empreintes acoustiques pourrait échouer")
        logger.warning("Veuillez télécharger fpcalc.exe et le placer dans le répertoire backend/bin/")
        return False


def main():
    """Fonction principale."""
    logger.info("Vérification et installation des dépendances pour les tests de détection musicale")
    
    # Vérifier et installer les dépendances requises
    required_installed = check_and_install_dependencies(REQUIRED_PACKAGES)
    
    # Vérifier et installer les dépendances optionnelles
    optional_installed = check_and_install_dependencies(OPTIONAL_PACKAGES, optional=True)
    
    # Vérifier si fpcalc.exe est disponible
    fpcalc_available = check_fpcalc()
    
    # Résumé
    logger.info("\nRésumé de l'installation:")
    logger.info(f"- {required_installed} packages requis installés")
    logger.info(f"- {optional_installed} packages optionnels installés")
    logger.info(f"- fpcalc.exe disponible: {fpcalc_available}")
    
    # Vérifier si les dépendances requises sont installées
    all_required_installed = all(check_package_installed(package) for package in REQUIRED_PACKAGES)
    
    if all_required_installed:
        logger.info("\nToutes les dépendances requises sont installées")
        logger.info("Vous pouvez maintenant exécuter les tests de détection musicale")
    else:
        logger.error("\nCertaines dépendances requises n'ont pas pu être installées")
        logger.error("Veuillez les installer manuellement avant d'exécuter les tests")
    
    # Instructions pour exécuter les tests
    logger.info("\nPour exécuter les tests de détection musicale:")
    logger.info("1. Test simple: python -m backend.tests.utils.simple_detection_test")
    logger.info("2. Test avec API réelles: python -m backend.tests.utils.run_real_api_detection")
    logger.info("3. Test multi-stations: python -m backend.tests.utils.run_multi_station_test")
    logger.info("4. Visualisation des résultats: python -m backend.tests.utils.run_visualize_detection_results")


if __name__ == "__main__":
    main() 