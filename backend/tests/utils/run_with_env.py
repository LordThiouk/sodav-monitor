"""
Script pour exécuter un test spécifique en chargeant d'abord les variables d'environnement.

Ce script charge les variables d'environnement à partir du fichier .env,
puis exécute le test spécifié.
"""

import os
import sys
import subprocess
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(str(current_dir.parent.parent))

# Importer le module de chargement des variables d'environnement
from tests.utils.load_env import load_env_variables

def main():
    # Charger les variables d'environnement
    print("Chargement des variables d'environnement...")
    if not load_env_variables():
        print("Impossible de charger les variables d'environnement. Arrêt du test.")
        return 1
    
    # Vérifier les clés API importantes
    acoustid_key = os.environ.get("ACOUSTID_API_KEY")
    audd_key = os.environ.get("AUDD_API_KEY")
    
    if acoustid_key:
        print(f"Clé API AcoustID chargée: {acoustid_key}")
    else:
        print("Clé API AcoustID non trouvée dans le fichier .env")
    
    if audd_key:
        print(f"Clé API Audd.io chargée: {audd_key}")
    else:
        print("Clé API Audd.io non trouvée dans le fichier .env")
    
    # Exécuter le test multi-stations
    print("\nExécution du test multi-stations...")
    try:
        subprocess.run([sys.executable, "-m", "tests.utils.multi_station_test"], check=True)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution du test: {e}")
        return e.returncode

if __name__ == "__main__":
    sys.exit(main()) 