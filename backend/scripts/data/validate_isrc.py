#!/usr/bin/env python
"""
Script pour valider et normaliser les codes ISRC dans la base de données.

Ce script parcourt toutes les pistes de la base de données, valide leurs codes ISRC,
normalise les codes valides et corrige les entrées dans la base de données.
"""

import argparse
import logging
import os
import sys
from typing import Dict, List, Tuple

from sqlalchemy import update
from sqlalchemy.orm import Session

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, backend_dir)

from backend.logs.log_manager import LogManager
from backend.models.database import get_db
from backend.models.models import Track
from backend.utils.validators import validate_isrc

# Configurer le logging
log_manager = LogManager()
logger = log_manager.get_logger("validate_isrc")


def get_tracks_with_isrc(db_session: Session) -> List[Track]:
    """
    Récupère toutes les pistes avec un code ISRC non nul.

    Args:
        db_session: Session de base de données

    Returns:
        Liste des pistes avec un code ISRC
    """
    return db_session.query(Track).filter(Track.isrc.isnot(None)).all()


def validate_and_normalize_isrc(track: Track) -> Tuple[bool, str, str]:
    """
    Valide et normalise le code ISRC d'une piste.

    Args:
        track: Piste à valider

    Returns:
        Tuple contenant:
        - Un booléen indiquant si l'ISRC est valide
        - L'ISRC original
        - L'ISRC normalisé si valide, l'original sinon
    """
    original_isrc = track.isrc
    is_valid, normalized_isrc = validate_isrc(original_isrc)

    return is_valid, original_isrc, normalized_isrc if is_valid else original_isrc


def update_track_isrc(db_session: Session, track_id: int, normalized_isrc: str) -> bool:
    """
    Met à jour le code ISRC d'une piste.

    Args:
        db_session: Session de base de données
        track_id: ID de la piste à mettre à jour
        normalized_isrc: Code ISRC normalisé

    Returns:
        True si la mise à jour a réussi, False sinon
    """
    try:
        stmt = update(Track).where(Track.id == track_id).values(isrc=normalized_isrc)
        db_session.execute(stmt)
        db_session.commit()
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de l'ISRC pour la piste {track_id}: {e}")
        db_session.rollback()
        return False


def process_tracks(db_session: Session, dry_run: bool = False) -> Dict[str, int]:
    """
    Traite toutes les pistes avec un code ISRC.

    Args:
        db_session: Session de base de données
        dry_run: Si True, n'effectue pas de modifications dans la base de données

    Returns:
        Dictionnaire contenant les statistiques de traitement
    """
    stats = {"total": 0, "valid": 0, "invalid": 0, "normalized": 0, "errors": 0}

    tracks = get_tracks_with_isrc(db_session)
    stats["total"] = len(tracks)

    for track in tracks:
        is_valid, original_isrc, normalized_isrc = validate_and_normalize_isrc(track)

        if is_valid:
            stats["valid"] += 1
            if original_isrc != normalized_isrc:
                stats["normalized"] += 1
                logger.info(
                    f"Piste {track.id} ({track.title}): ISRC normalisé de {original_isrc} à {normalized_isrc}"
                )

                if not dry_run:
                    success = update_track_isrc(db_session, track.id, normalized_isrc)
                    if not success:
                        stats["errors"] += 1
        else:
            stats["invalid"] += 1
            logger.warning(f"Piste {track.id} ({track.title}): ISRC invalide {original_isrc}")

    return stats


def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(
        description="Valide et normalise les codes ISRC dans la base de données."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Exécute le script sans modifier la base de données"
    )
    args = parser.parse_args()

    logger.info(f"Démarrage du script de validation des ISRC (dry-run: {args.dry_run})")

    # Obtenir une session de base de données
    db = next(get_db())

    try:
        # Traiter les pistes
        stats = process_tracks(db, args.dry_run)

        # Afficher les statistiques
        logger.info("Statistiques de traitement:")
        logger.info(f"  Total de pistes avec ISRC: {stats['total']}")

        if stats["total"] > 0:
            valid_percent = stats["valid"] / stats["total"] * 100
            invalid_percent = stats["invalid"] / stats["total"] * 100
            normalized_percent = stats["normalized"] / stats["total"] * 100

            logger.info(f"  ISRC valides: {stats['valid']} ({valid_percent:.1f}%)")
            logger.info(f"  ISRC invalides: {stats['invalid']} ({invalid_percent:.1f}%)")
            logger.info(f"  ISRC normalisés: {stats['normalized']} ({normalized_percent:.1f}%)")
        else:
            logger.info("  Aucune piste avec ISRC trouvée dans la base de données")
            logger.info("  ISRC valides: 0 (0.0%)")
            logger.info("  ISRC invalides: 0 (0.0%)")
            logger.info("  ISRC normalisés: 0 (0.0%)")

        logger.info(f"  Erreurs de mise à jour: {stats['errors']}")

        if args.dry_run:
            logger.info(
                "Mode dry-run: aucune modification n'a été effectuée dans la base de données"
            )
        else:
            logger.info("Les modifications ont été appliquées à la base de données")

    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du script: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.exit(1)

    logger.info("Script terminé avec succès")


if __name__ == "__main__":
    main()
