#!/usr/bin/env python
"""
Script pour exécuter la visualisation des résultats de détection en chargeant les variables d'environnement depuis le fichier .env.
Ce script recherche automatiquement les fichiers de logs JSON et exécute la visualisation.
"""

import os
import sys
import subprocess
import glob
from pathlib import Path
import dotenv

def find_log_files():
    """Recherche les fichiers de logs JSON dans le répertoire courant et les répertoires de logs."""
    # Recherche dans le répertoire backend
    backend_dir = Path(__file__).parent.parent.parent
    log_files = list(backend_dir.glob("*_logs.json"))
    
    # Recherche dans le répertoire de logs s'il existe
    logs_dir = backend_dir / "logs"
    if logs_dir.exists():
        log_files.extend(logs_dir.glob("*_logs.json"))
    
    return log_files

def main():
    """Fonction principale qui charge les variables d'environnement et exécute la visualisation."""
    # Charger les variables d'environnement depuis le fichier .env
    env_file = Path(__file__).parent.parent.parent.parent / ".env"
    if env_file.exists():
        print(f"Chargement des variables d'environnement depuis {env_file}")
        loaded_env = dotenv.load_dotenv(env_file)
        if loaded_env:
            env_count = len(os.environ)
            print(f"Variables d'environnement chargées avec succès: {env_count} variables")
        else:
            print("Erreur lors du chargement des variables d'environnement")
    else:
        print(f"Fichier .env non trouvé à {env_file}")
    
    # Trouver les fichiers de logs
    log_files = find_log_files()
    if not log_files:
        print("Aucun fichier de logs trouvé. Impossible de continuer.")
        return
    
    print(f"Fichiers de logs trouvés: {len(log_files)}")
    for i, log_file in enumerate(log_files):
        print(f"{i+1}. {log_file}")
    
    # Créer le répertoire de sortie pour les visualisations
    output_dir = Path(__file__).parent.parent.parent / "visualizations"
    output_dir.mkdir(exist_ok=True)
    print(f"Les visualisations seront enregistrées dans: {output_dir}")
    
    # Chemin vers le script de visualisation
    visualization_script = Path(__file__).parent / "visualize_detection_results.py"
    if not visualization_script.exists():
        print(f"Script de visualisation non trouvé à {visualization_script}")
        return
    
    # Exécuter la visualisation pour chaque fichier de logs
    for log_file in log_files:
        print(f"\nVisualisation du fichier: {log_file}")
        try:
            # Passer le fichier de logs comme argument positionnel, pas comme option nommée
            cmd = [
                sys.executable,
                str(visualization_script),
                str(log_file),  # Argument positionnel
                "--output-dir", str(output_dir),
                "--format", "both"
            ]
            
            print(f"Exécution de la commande: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True)
            
            if result.returncode == 0:
                print(f"Visualisation réussie pour {log_file}")
            else:
                print(f"Erreur lors de la visualisation de {log_file}")
        
        except Exception as e:
            print(f"Erreur lors de la visualisation: {e}")

if __name__ == "__main__":
    main() 