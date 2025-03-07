#!/usr/bin/env python3
"""Script de réorganisation du backend SODAV Monitor."""

import os
import shutil
from pathlib import Path
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_dir(path):
    """Crée un répertoire s'il n'existe pas."""
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"✅ Créé le répertoire {path}")

def update_init_file(directory):
    """Met à jour ou crée le fichier __init__.py dans le répertoire."""
    init_file = os.path.join(directory, '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write(f'"""Module d\'initialisation pour {os.path.basename(directory)}."""\n')
        logger.info(f"✅ Créé {init_file}")

def move_file(src, dest):
    """Déplace un fichier en gérant les erreurs."""
    try:
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(src, dest)
            logger.info(f"✅ Déplacé {src} vers {dest}")
        else:
            logger.warning(f"⚠️ Fichier source non trouvé: {src}")
    except Exception as e:
        logger.error(f"❌ Erreur lors du déplacement de {src}: {str(e)}")

def main():
    """Fonction principale de réorganisation."""
    # Définition de la structure
    backend_dir = "backend"
    directories = [
        "analytics",
        "core",
        "detection",
        "logs",
        "models",
        "processing",
        "reports",
        "routers",
        "schemas",
        "tests",
        "utils",
        "data"
    ]

    # Création des répertoires
    for dir_name in directories:
        dir_path = os.path.join(backend_dir, dir_name)
        ensure_dir(dir_path)
        update_init_file(dir_path)

    # Déplacement des fichiers
    file_moves = {
        "detection": [
            "audio_processor.py",
            "music_recognition.py",
            "fingerprint.py"
        ],
        "processing": [
            "stream_processor.py",
            "audio_handler.py"
        ],
        "models": [
            "models.py",
            "database.py"
        ],
        "utils": [
            "config.py",
            "redis_config.py",
            "logging_config.py"
        ]
    }

    # Déplacement des fichiers
    for dir_name, files in file_moves.items():
        target_dir = os.path.join(backend_dir, dir_name)
        for file_name in files:
            src = os.path.join(backend_dir, file_name)
            dest = os.path.join(target_dir, file_name)
            move_file(src, dest)

    # Mise à jour du fichier REORGANISATION.md
    with open("docs/REORGANISATION.md", "a") as f:
        f.write(f"\n### {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write("- Réorganisation des fichiers du backend :\n")
        for dir_name in directories:
            f.write(f"  - Création/Mise à jour du dossier `{dir_name}/`\n")
        f.write("- Mise à jour des fichiers __init__.py\n")
        f.write("- Déplacement des fichiers vers leurs nouveaux emplacements\n")

    logger.info("✅ Réorganisation terminée avec succès!")

if __name__ == "__main__":
    main() 