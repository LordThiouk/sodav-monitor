#!/usr/bin/env python3
"""
Script pour copier des fichiers audio sénégalais depuis le dossier Téléchargements.

Ce script copie les fichiers audio sénégalais depuis le dossier Téléchargements
vers le répertoire de test pour les utiliser dans les tests de détection musicale.
"""

import argparse
import logging
import os
import shutil
from pathlib import Path

from radio_simulator import AUDIO_DIR

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("copy_test_audio")

# Chemin par défaut vers le dossier Téléchargements
DEFAULT_DOWNLOADS_DIR = os.path.expanduser("~/Downloads")


def copy_audio_files(source_dir=None, output_dir=None, extensions=None):
    """
    Copie les fichiers audio depuis le dossier source vers le répertoire de test.

    Args:
        source_dir: Répertoire source (utilise le dossier Téléchargements par défaut si None)
        output_dir: Répertoire de sortie (utilise le répertoire par défaut si None)
        extensions: Liste des extensions de fichiers à copier (utilise les extensions audio courantes si None)

    Returns:
        Liste des chemins vers les fichiers copiés
    """
    if source_dir is None:
        source_dir = DEFAULT_DOWNLOADS_DIR

    if output_dir is None:
        output_dir = AUDIO_DIR

    if extensions is None:
        extensions = [".mp3", ".wav", ".ogg", ".m4a", ".flac"]

    # Convertir en objets Path
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)

    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)

    # Trouver tous les fichiers audio dans le répertoire source
    audio_files = []
    for ext in extensions:
        audio_files.extend(list(source_dir.glob(f"*{ext}")))

    if not audio_files:
        logger.warning(f"Aucun fichier audio trouvé dans {source_dir}")
        return []

    # Copier chaque fichier
    copied_files = []
    for file_path in audio_files:
        output_path = output_dir / file_path.name
        try:
            shutil.copy2(file_path, output_path)
            logger.info(f"Fichier copié: {file_path.name}")
            copied_files.append(output_path)
        except Exception as e:
            logger.error(f"Erreur lors de la copie de {file_path.name}: {e}")

    logger.info(f"{len(copied_files)} fichiers copiés sur {len(audio_files)}")
    return copied_files


def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(
        description="Copie des fichiers audio sénégalais depuis le dossier Téléchargements"
    )
    parser.add_argument(
        "--source-dir",
        type=str,
        default=None,
        help=f"Répertoire source (par défaut: {DEFAULT_DOWNLOADS_DIR})",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None, help="Répertoire de sortie pour les fichiers copiés"
    )
    parser.add_argument(
        "--extensions",
        type=str,
        nargs="+",
        default=None,
        help="Extensions de fichiers à copier (par défaut: .mp3 .wav .ogg .m4a .flac)",
    )
    args = parser.parse_args()

    source_dir = args.source_dir
    output_dir = args.output_dir
    extensions = args.extensions

    if output_dir:
        output_dir = Path(output_dir)

    copied_files = copy_audio_files(source_dir, output_dir, extensions)

    if copied_files:
        logger.info("Copie terminée avec succès")
        for file_path in copied_files:
            logger.info(f"  - {file_path}")
    else:
        logger.warning("Aucun fichier n'a été copié")
        logger.info("Assurez-vous que des fichiers audio sont présents dans le dossier source")
        logger.info(f"  Source: {source_dir or DEFAULT_DOWNLOADS_DIR}")
        logger.info(f"  Destination: {output_dir or AUDIO_DIR}")


if __name__ == "__main__":
    main()
