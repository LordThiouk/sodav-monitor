#!/usr/bin/env python3
"""
Script pour télécharger des fichiers audio sénégalais pour les tests.

Ce script télécharge une collection de fichiers audio sénégalais
à utiliser pour les tests de détection musicale.
"""

import argparse
import logging
import os
from pathlib import Path

from radio_simulator import AUDIO_DIR, download_test_audio

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("download_test_audio")

# Liste d'URLs de fichiers audio sénégalais libres de droits ou sous licence Creative Commons
# Note: Ces URLs sont fictives et doivent être remplacées par de vraies URLs
SENEGAL_AUDIO_URLS = [
    # Remplacer ces URLs par de vraies URLs de musique sénégalaise
    # Format: (url, nom_fichier)
    ("https://example.com/senegal/mbalax1.mp3", "mbalax_sample1.mp3"),
    ("https://example.com/senegal/mbalax2.mp3", "mbalax_sample2.mp3"),
    ("https://example.com/senegal/sabar1.mp3", "sabar_sample1.mp3"),
    ("https://example.com/senegal/tassou1.mp3", "tassou_sample1.mp3"),
    ("https://example.com/senegal/afrojazz1.mp3", "afrojazz_sample1.mp3"),
]

# URLs alternatives réelles (à utiliser si disponibles)
REAL_AUDIO_URLS = [
    # Musique libre de droits ou sous licence Creative Commons
    # Format: (url, nom_fichier)
    # Ajouter ici des URLs réelles de musique sénégalaise libre de droits
]


def download_all_test_audio(output_dir=None, use_real_urls=False):
    """
    Télécharge tous les fichiers audio de test.

    Args:
        output_dir: Répertoire de sortie (utilise le répertoire par défaut si None)
        use_real_urls: Utiliser les URLs réelles au lieu des URLs fictives

    Returns:
        Liste des chemins vers les fichiers téléchargés
    """
    if output_dir is None:
        output_dir = AUDIO_DIR

    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)

    # Sélectionner la liste d'URLs à utiliser
    urls = REAL_AUDIO_URLS if use_real_urls and REAL_AUDIO_URLS else SENEGAL_AUDIO_URLS

    if not urls:
        logger.warning("Aucune URL de fichier audio disponible")
        return []

    # Télécharger chaque fichier
    downloaded_files = []
    for url, filename in urls:
        logger.info(f"Téléchargement de {filename} depuis {url}")
        file_path = download_test_audio(url, output_dir, filename)
        if file_path:
            downloaded_files.append(file_path)

    logger.info(f"{len(downloaded_files)} fichiers téléchargés sur {len(urls)}")
    return downloaded_files


def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(
        description="Télécharge des fichiers audio sénégalais pour les tests"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Répertoire de sortie pour les fichiers téléchargés",
    )
    parser.add_argument(
        "--use-real-urls",
        action="store_true",
        help="Utiliser les URLs réelles au lieu des URLs fictives",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    if output_dir:
        output_dir = Path(output_dir)

    downloaded_files = download_all_test_audio(output_dir, args.use_real_urls)

    if downloaded_files:
        logger.info("Téléchargement terminé avec succès")
        for file_path in downloaded_files:
            logger.info(f"  - {file_path}")
    else:
        logger.warning("Aucun fichier n'a été téléchargé")
        logger.info(
            "Pour utiliser ce script, vous devez ajouter des URLs réelles dans REAL_AUDIO_URLS"
        )
        logger.info("Ou placer manuellement des fichiers audio dans le répertoire:")
        logger.info(f"  {AUDIO_DIR}")


if __name__ == "__main__":
    main()
