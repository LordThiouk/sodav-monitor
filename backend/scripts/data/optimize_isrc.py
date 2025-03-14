#!/usr/bin/env python
"""
Script pour optimiser les codes ISRC dans la base de données.

Ce script exécute les étapes suivantes :
1. Validation et normalisation des codes ISRC existants
2. Fusion des pistes dupliquées basées sur l'ISRC

Utilisation :
    python -m backend.scripts.data.optimize_isrc [--dry-run]
"""

import argparse
import logging
import os
import subprocess
import sys
from typing import List

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, backend_dir)

from backend.logs.log_manager import LogManager

# Configurer le logging
log_manager = LogManager()
logger = log_manager.get_logger("optimize_isrc")


def run_script(script_path: str, args: List[str] = None) -> bool:
    """
    Exécute un script Python.

    Args:
        script_path: Chemin vers le script à exécuter
        args: Arguments à passer au script

    Returns:
        True si le script s'est exécuté avec succès, False sinon
    """
    if args is None:
        args = []

    cmd = [sys.executable, script_path] + args
    logger.info(f"Exécution de la commande : {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Sortie standard : {result.stdout}")
        if result.stderr:
            logger.warning(f"Erreur standard : {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'exécution du script : {e}")
        logger.error(f"Sortie standard : {e.stdout}")
        logger.error(f"Erreur standard : {e.stderr}")
        return False


def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(description="Optimise les codes ISRC dans la base de données.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Exécute le script sans modifier la base de données"
    )
    args = parser.parse_args()

    logger.info(f"Démarrage du script d'optimisation des ISRC (dry-run: {args.dry_run})")

    # Chemins vers les scripts à exécuter
    validate_script = os.path.join(current_dir, "validate_isrc.py")
    merge_script = os.path.join(current_dir, "merge_duplicate_isrc.py")

    # Arguments pour les scripts
    script_args = ["--dry-run"] if args.dry_run else []

    # Étape 1 : Validation et normalisation des ISRC
    logger.info("Étape 1 : Validation et normalisation des ISRC")
    if not run_script(validate_script, script_args):
        logger.error("Échec de l'étape 1. Arrêt du script.")
        sys.exit(1)

    # Étape 2 : Fusion des pistes dupliquées
    logger.info("Étape 2 : Fusion des pistes dupliquées")
    if not run_script(merge_script, script_args):
        logger.error("Échec de l'étape 2. Arrêt du script.")
        sys.exit(1)

    logger.info("Optimisation des ISRC terminée avec succès")


if __name__ == "__main__":
    main()
