from typing import Dict, Optional, Union
from datetime import datetime
import re
import logging

from backend.models.models import ReportFormat, ReportType

logger = logging.getLogger(__name__)

def validate_track_info(track_info: Dict) -> bool:
    """Valide les informations de piste avant la sauvegarde"""
    try:
        required_fields = ['title', 'artist']
        optional_fields = ['isrc', 'label', 'album', 'duration']
        
        # Vérification des champs requis
        if not all(track_info.get(field) for field in required_fields):
            missing = [f for f in required_fields if not track_info.get(f)]
            logger.error(f"Champs requis manquants: {', '.join(missing)}")
            return False
            
        # Validation des types de données
        if not isinstance(track_info['title'], str) or not isinstance(track_info['artist'], str):
            logger.error("Le titre et l'artiste doivent être des chaînes de caractères")
            return False
            
        # Validation des longueurs
        if len(track_info['title']) > 255 or len(track_info['artist']) > 255:
            logger.error("Le titre ou l'artiste est trop long (max 255 caractères)")
            return False
            
        # Validation ISRC si présent
        if track_info.get('isrc'):
            if not isinstance(track_info['isrc'], str) or len(track_info['isrc']) != 12:
                logger.error("Format ISRC invalide")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la validation: {str(e)}")
        return False

def validate_email(email: str) -> bool:
    """Validate email address format."""
    if not email or not isinstance(email, str):
        return False
    
    # Check for whitespace
    if re.search(r'\s', email):
        return False
    
    try:
        # Split into local and domain parts
        local, domain = email.split('@')
        
        # Check lengths
        if len(email) > 254 or len(local) > 64:
            return False
            
        # Local part checks
        if not local or local.startswith('.') or local.endswith('.') or '..' in local:
            return False
            
        # Domain checks
        if not domain or domain.startswith('.') or domain.endswith('.') or '..' in domain:
            return False
            
        # Basic email validation regex
        pattern = r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(pattern, email))
        
    except Exception as e:
        logger.error(f"Error validating email: {str(e)}")
        return False

def validate_date_range(start_date: Union[datetime, None], end_date: Union[datetime, None]) -> bool:
    """Validate date range."""
    if not start_date or not end_date:
        return False
    
    try:
        return start_date <= end_date
    except Exception as e:
        logger.error(f"Error validating date range: {str(e)}")
        return False

def validate_report_format(report_format: Union[ReportFormat, str, None]) -> bool:
    """Validate report format."""
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
    """Validate subscription frequency."""
    if not frequency:
        return False
    
    try:
        if isinstance(frequency, str):
            return frequency in [freq.value for freq in ReportType]
        return isinstance(frequency, ReportType)
    except Exception as e:
        logger.error(f"Error validating subscription frequency: {str(e)}")
        return False 