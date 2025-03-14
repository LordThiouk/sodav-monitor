"""
Module de recherche de pistes audio.

Ce module contient la classe TrackFinder qui est responsable de la recherche
de pistes dans la base de données locale, par ISRC ou par empreinte digitale.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session

from backend.models.models import Artist, Track
from backend.utils.logging import log_with_category

logger = logging.getLogger(__name__)


class TrackFinder:
    """
    Classe responsable de la recherche de pistes dans la base de données locale.

    Cette classe extrait les fonctionnalités de recherche de pistes du TrackManager
    pour améliorer la séparation des préoccupations et faciliter la maintenance.
    """

    def __init__(self, db_session: Session):
        """
        Initialise un nouveau TrackFinder.

        Args:
            db_session: Session de base de données SQLAlchemy
        """
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

        # Seuil de similarité pour considérer deux empreintes comme correspondantes
        self.similarity_threshold = 0.85

    async def find_local_match(self, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Recherche une correspondance locale pour les caractéristiques audio fournies.

        Cette méthode recherche d'abord une correspondance exacte par empreinte digitale,
        puis essaie de trouver une correspondance approximative si aucune correspondance
        exacte n'est trouvée.

        Args:
            features: Caractéristiques audio extraites

        Returns:
            Dictionnaire contenant les informations de la piste correspondante ou None si aucune correspondance
        """
        try:
            log_with_category(logger, "TRACK_FINDER", "info", "Searching for local match")

            # Extraire l'empreinte digitale des caractéristiques
            fingerprint = self._extract_fingerprint(features)
            if not fingerprint:
                log_with_category(
                    logger, "TRACK_FINDER", "warning", "No fingerprint found in features"
                )
                return None

            # Rechercher une correspondance exacte par empreinte digitale
            track = self.db_session.query(Track).filter(Track.fingerprint == fingerprint).first()
            if track:
                log_with_category(
                    logger, "TRACK_FINDER", "info", f"Found exact fingerprint match: {track.title}"
                )
                return self._create_match_result(track, 1.0, "local_exact")

            # Si aucune correspondance exacte n'est trouvée, essayer une correspondance approximative
            log_with_category(
                logger, "TRACK_FINDER", "info", "No exact match found, trying approximate match"
            )

            # Récupérer toutes les pistes avec une empreinte digitale
            tracks_with_fingerprint = (
                self.db_session.query(Track).filter(Track.fingerprint.isnot(None)).all()
            )

            best_match = None
            best_similarity = 0.0

            # Calculer la similarité avec chaque piste
            for track in tracks_with_fingerprint:
                similarity = self._calculate_similarity(fingerprint, track.fingerprint)

                if similarity > self.similarity_threshold and similarity > best_similarity:
                    best_match = track
                    best_similarity = similarity

            if best_match:
                log_with_category(
                    logger,
                    "TRACK_FINDER",
                    "info",
                    f"Found approximate match: {best_match.title} (similarity: {best_similarity:.2f})",
                )
                return self._create_match_result(best_match, best_similarity, "local_approximate")

            log_with_category(logger, "TRACK_FINDER", "info", "No local match found")
            return None

        except Exception as e:
            log_with_category(logger, "TRACK_FINDER", "error", f"Error finding local match: {e}")
            return None

    async def find_track_by_isrc(self, isrc: str) -> Optional[Dict[str, Any]]:
        """
        Recherche une piste par son code ISRC dans la base de données.

        Args:
            isrc: Code ISRC à rechercher

        Returns:
            Dictionnaire contenant les informations de la piste ou None si aucune correspondance
        """
        if not isrc:
            return None

        # Normaliser l'ISRC (supprimer les tirets, mettre en majuscules)
        normalized_isrc = isrc.replace("-", "").upper()

        # Vérifier la validité du format ISRC
        if not self._validate_isrc(normalized_isrc):
            log_with_category(logger, "TRACK_FINDER", "warning", f"Invalid ISRC format: {isrc}")
            return None

        # Rechercher la piste par ISRC
        track = self.db_session.query(Track).filter(Track.isrc == normalized_isrc).first()

        if not track:
            log_with_category(logger, "TRACK_FINDER", "info", f"No track found with ISRC: {isrc}")
            return None

        # Récupérer l'artiste
        artist = self.db_session.query(Artist).filter(Artist.id == track.artist_id).first()
        artist_name = artist.name if artist else "Unknown Artist"

        log_with_category(
            logger,
            "TRACK_FINDER",
            "info",
            f"Found track with ISRC {isrc}: {track.title} by {artist_name}",
        )

        return self._create_match_result(track, 1.0, "isrc_match")

    def _calculate_similarity(self, fingerprint1: str, fingerprint2: str) -> float:
        """
        Calcule la similarité entre deux empreintes digitales.

        Args:
            fingerprint1: Première empreinte digitale
            fingerprint2: Deuxième empreinte digitale

        Returns:
            Score de similarité entre 0.0 et 1.0
        """
        try:
            # Convertir les empreintes en tableaux numériques
            # Note: Dans une implémentation réelle, cette conversion dépendrait
            # du format spécifique des empreintes digitales
            fp1 = np.array([ord(c) for c in fingerprint1])
            fp2 = np.array([ord(c) for c in fingerprint2])

            # Normaliser les tableaux
            fp1 = fp1 / np.linalg.norm(fp1)
            fp2 = fp2 / np.linalg.norm(fp2)

            # Calculer la similarité cosinus
            similarity = np.dot(fp1, fp2)

            return float(similarity)

        except Exception as e:
            log_with_category(logger, "TRACK_FINDER", "error", f"Error calculating similarity: {e}")
            return 0.0

    def _extract_fingerprint(self, features: Dict[str, Any]) -> Optional[str]:
        """
        Extrait l'empreinte digitale des caractéristiques audio.

        Args:
            features: Caractéristiques audio extraites

        Returns:
            Empreinte digitale sous forme de chaîne de caractères ou None si non disponible
        """
        # Vérifier si l'empreinte est déjà disponible dans les caractéristiques
        if "fingerprint" in features and features["fingerprint"]:
            return features["fingerprint"]

        # Si non disponible, retourner None
        # Dans une implémentation réelle, on pourrait essayer de calculer l'empreinte
        # à partir d'autres caractéristiques disponibles
        return None

    def _validate_isrc(self, isrc: str) -> bool:
        """
        Valide le format d'un code ISRC.

        Un code ISRC valide doit:
        - Avoir exactement 12 caractères
        - Commencer par 2 lettres (code pays)
        - Suivi de 3 caractères alphanumériques (code d'enregistrement)
        - Suivi de 2 chiffres (année)
        - Suivi de 5 chiffres (numéro de désignation)

        Args:
            isrc: Code ISRC à valider

        Returns:
            True si le format est valide, False sinon
        """
        if not isrc or len(isrc) != 12:
            return False

        # Vérifier le format: 2 lettres + 3 alphanumériques + 2 chiffres + 5 chiffres
        country_code = isrc[0:2]
        registrant_code = isrc[2:5]
        year_code = isrc[5:7]
        designation_code = isrc[7:12]

        # Vérifier le code pays (2 lettres)
        if not country_code.isalpha():
            return False

        # Vérifier le code d'enregistrement (3 caractères alphanumériques)
        if not registrant_code.isalnum():
            return False

        # Vérifier l'année (2 chiffres)
        if not year_code.isdigit():
            return False

        # Vérifier le numéro de désignation (5 chiffres)
        if not designation_code.isdigit():
            return False

        return True

    def _create_match_result(
        self, track: Track, confidence: float, detection_method: str
    ) -> Dict[str, Any]:
        """
        Crée un dictionnaire de résultat standardisé pour une correspondance de piste.

        Args:
            track: Objet Track correspondant
            confidence: Score de confiance de la correspondance (entre 0.0 et 1.0)
            detection_method: Méthode de détection utilisée

        Returns:
            Dictionnaire contenant les informations de la piste
        """
        # Récupérer l'artiste
        artist = self.db_session.query(Artist).filter(Artist.id == track.artist_id).first()
        artist_name = artist.name if artist else "Unknown Artist"

        return {
            "track": {
                "id": track.id,
                "title": track.title,
                "artist": artist_name,
                "artist_id": track.artist_id,
                "album": track.album,
                "isrc": track.isrc,
                "label": track.label,
                "release_date": track.release_date,
                "duration": track.duration.total_seconds() if track.duration else 0,
                "fingerprint": track.fingerprint,
            },
            "confidence": confidence,
            "detection_method": detection_method,
            "source": "local_database",
        }
