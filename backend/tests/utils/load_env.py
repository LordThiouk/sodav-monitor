"""
Script pour charger les variables d'environnement à partir du fichier .env.

Ce script permet de charger les variables d'environnement nécessaires pour les tests
de détection musicale, notamment les clés API pour AcoustID et Audd.io.
"""

import logging
import os
import sys
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("load_env")

def find_env_file():
    """
    Recherche le fichier .env dans les répertoires parents.
    
    Returns:
        Path: Chemin vers le fichier .env ou None si non trouvé
    """
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # Remonter jusqu'à 3 niveaux pour trouver le fichier .env
    for _ in range(4):
        env_file = current_dir / ".env"
        if env_file.exists():
            return env_file
        current_dir = current_dir.parent
    
    return None

def load_env_variables():
    """
    Charge les variables d'environnement à partir du fichier .env.
    
    Returns:
        bool: True si les variables ont été chargées avec succès, False sinon
    """
    env_file = find_env_file()
    
    if not env_file:
        logger.error("Fichier .env non trouvé")
        return False
    
    logger.info(f"Chargement des variables d'environnement depuis {env_file}")
    
    # Charger les variables d'environnement
    variables_loaded = 0
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
                
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                
                # Supprimer les guillemets si présents
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Définir la variable d'environnement
                os.environ[key] = value
                variables_loaded += 1
    
    logger.info(f"{variables_loaded} variables d'environnement chargées")
    
    # Vérifier les clés API importantes
    acoustid_key = os.environ.get("ACOUSTID_API_KEY")
    audd_key = os.environ.get("AUDD_API_KEY")
    
    if acoustid_key:
        logger.info("Clé API AcoustID chargée")
    else:
        logger.warning("Clé API AcoustID non trouvée dans le fichier .env")
    
    if audd_key:
        logger.info("Clé API Audd.io chargée")
    else:
        logger.warning("Clé API Audd.io non trouvée dans le fichier .env")
    
    return True

if __name__ == "__main__":
    load_env_variables() 