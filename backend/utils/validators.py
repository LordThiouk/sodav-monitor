"""Validation utilities for the SODAV Monitor system.

This module provides validation functions for various data types and models
used throughout the application.
"""

import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union

from backend.models.models import ReportFormat, ReportType
from backend.utils.logging_config import setup_logging

logger = setup_logging(__name__)


def validate_track_info(track_info: Dict) -> bool:
    """Validate track information before saving.

    Checks for required fields, data types, and field length constraints.

    Args:
        track_info: Dictionary containing track information

    Returns:
        bool: True if validation passes, False otherwise
    """
    try:
        required_fields = ["title", "artist"]

        # Vérification des champs requis
        if not all(track_info.get(field) for field in required_fields):
            missing = [f for f in required_fields if not track_info.get(f)]
            logger.error(f"Champs requis manquants: {', '.join(missing)}")
            return False

        # Validation des types de données
        if not isinstance(track_info["title"], str) or not isinstance(track_info["artist"], str):
            logger.error("Le titre et l'artiste doivent être des chaînes de caractères")
            return False

        # Validation des longueurs
        if len(track_info["title"]) > 255 or len(track_info["artist"]) > 255:
            logger.error("Le titre ou l'artiste est trop long (max 255 caractères)")
            return False

        # Validation ISRC si présent
        if track_info.get("isrc"):
            if not isinstance(track_info["isrc"], str) or len(track_info["isrc"]) != 12:
                logger.error("Format ISRC invalide")
                return False

        return True

    except Exception as e:
        logger.error(f"Erreur lors de la validation: {str(e)}")
        return False


def validate_email(email: str) -> bool:
    """Validate email address format.

    Performs comprehensive validation of email addresses including length checks,
    format validation, and structural integrity.

    Args:
        email: The email address to validate

    Returns:
        bool: True if the email is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False

    # Check for whitespace
    if re.search(r"\s", email):
        return False

    try:
        # Split into local and domain parts
        local, domain = email.split("@")

        # Check lengths
        if len(email) > 254 or len(local) > 64:
            return False

        # Local part checks
        if not local or local.startswith(".") or local.endswith(".") or ".." in local:
            return False

        # Domain checks
        if not domain or domain.startswith(".") or domain.endswith(".") or ".." in domain:
            return False

        # Basic email validation regex
        pattern = (
            r"^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
            r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        )
        return bool(re.match(pattern, email))

    except Exception as e:
        logger.error(f"Error validating email: {str(e)}")
        return False


def validate_date_range(start_date: Union[datetime, None], end_date: Union[datetime, None]) -> bool:
    """Validate that a date range is properly ordered.

    Ensures that the start date is before or equal to the end date.

    Args:
        start_date: The starting date of the range
        end_date: The ending date of the range

    Returns:
        bool: True if the range is valid, False otherwise
    """
    if not start_date or not end_date:
        return False

    try:
        return start_date <= end_date
    except Exception as e:
        logger.error(f"Error validating date range: {str(e)}")
        return False


def validate_report_format(report_format: Union[ReportFormat, str, None]) -> bool:
    """Validate that a report format is supported.

    Checks if the provided format is a valid ReportFormat enum value.

    Args:
        report_format: The format to validate, either as a string or ReportFormat enum

    Returns:
        bool: True if the format is valid, False otherwise
    """
    if not report_format:
        return False

    try:
        if isinstance(report_format, str):
            return report_format in [format.value for format in ReportFormat]
        return isinstance(report_format, ReportFormat)
    except Exception as e:
        logger.error(f"Error validating report format: {str(e)}")
        return False


def validate_subscription_frequency(frequency: Union[ReportType, str, None]) -> bool:
    """Validate that a subscription frequency is supported.

    Checks if the provided frequency is a valid ReportType enum value.

    Args:
        frequency: The frequency to validate, either as a string or ReportType enum

    Returns:
        bool: True if the frequency is valid, False otherwise
    """
    if not frequency:
        return False

    try:
        if isinstance(frequency, str):
            return frequency in [freq.value for freq in ReportType]
        return isinstance(frequency, ReportType)
    except Exception as e:
        logger.error(f"Error validating subscription frequency: {str(e)}")
        return False


def validate_isrc(isrc: str) -> Tuple[bool, Optional[str]]:
    """Validate and normalize an ISRC code.

    Args:
        isrc: ISRC code to validate

    Returns:
        tuple[bool, Optional[str]]: (is_valid, normalized_isrc)
    """
    # Remove whitespace and convert to uppercase
    normalized = isrc.strip().upper()

    # Check basic format (12 characters: 2 country code + 3 registrant + 2 year + 5 designation)
    if len(normalized) != 12:
        return False, None

    # Check country code (first 2 characters must be letters)
    if not normalized[:2].isalpha():
        return False, None

    # Check registrant code (next 3 characters must be alphanumeric)
    if not normalized[2:5].isalnum():
        return False, None

    # Check year code (next 2 characters must be digits)
    if not normalized[5:7].isdigit():
        return False, None

    # Check designation code (last 5 characters must be digits)
    if not normalized[7:].isdigit():
        return False, None

    return True, normalized


def validate_model_data(data: Dict[str, Any], model_class: type) -> Dict[str, Any]:
    """Validate data against a model class.

    Args:
        data: Data to validate
        model_class: Model class to validate against

    Returns:
        Dict[str, Any]: Validated and cleaned data
    """
    try:
        # Create model instance
        model = model_class(**data)
        return model.dict()
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise


def validate_station_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate radio station data.

    Args:
        data: Station data to validate

    Returns:
        Dict[str, Any]: Validated and cleaned station data
    """
    required_fields = {"name", "stream_url", "region", "language"}
    missing_fields = required_fields - set(data.keys())

    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate field types
    if not isinstance(data["name"], str):
        raise ValueError("Name must be a string")
    if not isinstance(data["stream_url"], str):
        raise ValueError("Stream URL must be a string")
    if not isinstance(data["region"], str):
        raise ValueError("Region must be a string")
    if not isinstance(data["language"], str):
        raise ValueError("Language must be a string")

    return data


def validate_track_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate track data.

    Args:
        data: Track data to validate

    Returns:
        Dict[str, Any]: Validated and cleaned track data
    """
    required_fields = {"title", "artist_id", "isrc"}
    missing_fields = required_fields - set(data.keys())

    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate field types
    if not isinstance(data["title"], str):
        raise ValueError("Title must be a string")
    if not isinstance(data["artist_id"], int):
        raise ValueError("Artist ID must be an integer")
    if not isinstance(data["isrc"], str):
        raise ValueError("ISRC must be a string")

    return data


def validate_detection_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate detection data.

    Args:
        data: Detection data to validate

    Returns:
        Dict[str, Any]: Validated and cleaned detection data
    """
    required_fields = {"track_id", "station_id", "detected_at", "confidence"}
    missing_fields = required_fields - set(data.keys())

    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate field types
    if not isinstance(data["track_id"], int):
        raise ValueError("Track ID must be an integer")
    if not isinstance(data["station_id"], int):
        raise ValueError("Station ID must be an integer")
    if not isinstance(data["confidence"], (int, float)):
        raise ValueError("Confidence must be a number")

    return data


def validate_report_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate report data.

    Args:
        data: Report data to validate

    Returns:
        Dict[str, Any]: Validated and cleaned report data
    """
    required_fields = {"type", "format", "start_date", "end_date"}
    missing_fields = required_fields - set(data.keys())

    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate field types
    if not isinstance(data["type"], str):
        raise ValueError("Report type must be a string")
    if not isinstance(data["format"], str):
        raise ValueError("Report format must be a string")

    return data
