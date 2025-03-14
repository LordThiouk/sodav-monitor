"""
Script pour vérifier le répertoire courant et lister les fichiers.
"""

import os
import sys
from pathlib import Path

def main():
    # Afficher le répertoire courant
    current_dir = os.getcwd()
    print(f"Répertoire courant: {current_dir}")
    
    # Afficher le répertoire du script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Répertoire du script: {script_dir}")
    
    # Lister les fichiers dans le répertoire courant
    print("\nFichiers dans le répertoire courant:")
    for item in os.listdir(current_dir):
        print(f"  {item}")
    
    # Lister les fichiers dans le répertoire du script
    print("\nFichiers dans le répertoire du script:")
    for item in os.listdir(script_dir):
        print(f"  {item}")
    
    # Vérifier si le fichier .env existe
    env_file = Path(current_dir) / ".env"
    if env_file.exists():
        print(f"\nLe fichier .env existe dans le répertoire courant: {env_file}")
    else:
        print(f"\nLe fichier .env n'existe pas dans le répertoire courant: {env_file}")
    
    # Remonter pour trouver le fichier .env
    parent_dir = Path(current_dir)
    for _ in range(3):
        parent_dir = parent_dir.parent
        env_file = parent_dir / ".env"
        if env_file.exists():
            print(f"Le fichier .env existe dans le répertoire parent: {env_file}")
            break

if __name__ == "__main__":
    main() 