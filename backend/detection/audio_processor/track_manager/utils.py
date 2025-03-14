"""
Module de fonctions utilitaires pour la gestion des pistes audio.

Ce module contient des fonctions utilitaires partagées par les différentes
classes du package track_manager.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def validate_isrc(isrc: str) -> bool:
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


def normalize_isrc(isrc: str) -> str:
    """
    Normalise un code ISRC en supprimant les tirets et en mettant en majuscules.

    Args:
        isrc: Code ISRC à normaliser

    Returns:
        Code ISRC normalisé
    """
    if not isrc:
        return ""

    # Supprimer les tirets et mettre en majuscules
    normalized = isrc.replace("-", "").upper()

    return normalized


def normalize_title(title: str) -> str:
    """
    Normalise un titre de piste pour faciliter la recherche et la comparaison.

    La normalisation comprend:
    - Suppression des caractères spéciaux
    - Conversion en minuscules
    - Suppression des mots communs comme "feat.", "ft.", etc.
    - Suppression des espaces multiples

    Args:
        title: Titre à normaliser

    Returns:
        Titre normalisé
    """
    if not title:
        return ""

    # Convertir en minuscules
    normalized = title.lower()

    # Supprimer les caractères spéciaux
    normalized = re.sub(r"[^\w\s]", " ", normalized)

    # Supprimer les mots communs
    common_words = [
        "feat",
        "ft",
        "featuring",
        "prod",
        "produced by",
        "remix",
        "edit",
        "version",
        "radio edit",
        "extended",
        "original mix",
        "official",
        "video",
        "lyric",
        "lyrics",
        "audio",
        "official audio",
        "official video",
    ]

    for word in common_words:
        normalized = re.sub(r"\b" + word + r"\b", "", normalized)

    # Supprimer les espaces multiples
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def calculate_confidence(similarity: float, method: str) -> float:
    """
    Calcule un score de confiance pour une détection en fonction de la similarité et de la méthode.

    Args:
        similarity: Score de similarité entre 0.0 et 1.0
        method: Méthode de détection utilisée

    Returns:
        Score de confiance entre 0.0 et 1.0
    """
    # Facteurs de confiance par méthode
    method_factors = {
        "isrc_match": 1.0,  # Correspondance ISRC: confiance maximale
        "local_exact": 1.0,  # Correspondance exacte locale: confiance maximale
        "local_approximate": 0.9,  # Correspondance approximative locale: confiance élevée
        "acoustid": 0.85,  # AcoustID: bonne confiance
        "musicbrainz": 0.8,  # MusicBrainz: confiance moyenne-haute
        "audd": 0.75,  # AudD: confiance moyenne
        "unknown": 0.5,  # Méthode inconnue: confiance faible
    }

    # Utiliser le facteur de la méthode ou 0.7 par défaut
    method_factor = method_factors.get(method, 0.7)

    # Calculer le score de confiance final
    confidence = similarity * method_factor

    # Limiter le score entre 0.0 et 1.0
    return max(0.0, min(1.0, confidence))


def format_duration(seconds: Union[int, float, timedelta]) -> str:
    """
    Formate une durée en secondes en format lisible (MM:SS).

    Args:
        seconds: Durée en secondes ou timedelta

    Returns:
        Durée formatée en MM:SS
    """
    if isinstance(seconds, timedelta):
        seconds = seconds.total_seconds()

    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)

    return f"{minutes:02d}:{remaining_seconds:02d}"


def parse_duration(duration_str: str) -> Optional[float]:
    """
    Convertit une durée formatée (MM:SS) en secondes.

    Args:
        duration_str: Durée formatée en MM:SS

    Returns:
        Durée en secondes ou None si le format est invalide
    """
    try:
        # Format MM:SS
        if re.match(r"^\d+:\d{2}$", duration_str):
            parts = duration_str.split(":")
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds

        # Format HH:MM:SS
        elif re.match(r"^\d+:\d{2}:\d{2}$", duration_str):
            parts = duration_str.split(":")
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds

        # Format numérique (secondes)
        elif re.match(r"^\d+(\.\d+)?$", duration_str):
            return float(duration_str)

        return None

    except (ValueError, IndexError):
        return None
