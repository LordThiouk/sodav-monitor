from typing import Dict, Optional, Union, Tuple
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

def validate_isrc(isrc: str) -> Tuple[bool, Optional[str]]:
    """
    Valide et normalise un code ISRC.
    
    Format ISRC: CC-XXX-YY-NNNNN
    - CC: Code pays (2 lettres)
    - XXX: Code du propriétaire (3 caractères alphanumériques)
    - YY: Année de référence (2 chiffres)
    - NNNNN: Code de désignation (5 chiffres)
    
    Args:
        isrc: Code ISRC à valider.
        
    Returns:
        Tuple contenant:
        - Un booléen indiquant si l'ISRC est valide.
        - L'ISRC normalisé si valide, None sinon.
        
    Examples:
        >>> validate_isrc("FR-Z03-14-00123")
        (True, "FRZ0314000123")
        >>> validate_isrc("XX-123-45-6789")
        (False, None)
    """
    if not isrc or not isinstance(isrc, str):
        logger.warning(f"ISRC invalide (type incorrect ou vide): {isrc}")
        return False, None
    
    # Supprimer les tirets et les espaces, mettre en majuscules
    normalized_isrc = re.sub(r'[\s-]', '', isrc).upper()
    
    # Vérifier la longueur
    if len(normalized_isrc) != 12:
        logger.warning(f"ISRC invalide (longueur incorrecte): {isrc} -> {normalized_isrc}")
        return False, None
    
    # Vérifier le format
    pattern = r'^[A-Z]{2}[A-Z0-9]{3}[0-9]{7}$'
    if not re.match(pattern, normalized_isrc):
        logger.warning(f"ISRC invalide (format incorrect): {isrc} -> {normalized_isrc}")
        return False, None
    
    # Vérifier le code pays (doit être un code ISO valide)
    country_code = normalized_isrc[:2]
    valid_country_codes = [
        'AD', 'AE', 'AF', 'AG', 'AI', 'AL', 'AM', 'AO', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AW', 'AX', 'AZ',
        'BA', 'BB', 'BD', 'BE', 'BF', 'BG', 'BH', 'BI', 'BJ', 'BL', 'BM', 'BN', 'BO', 'BQ', 'BR', 'BS',
        'BT', 'BV', 'BW', 'BY', 'BZ', 'CA', 'CC', 'CD', 'CF', 'CG', 'CH', 'CI', 'CK', 'CL', 'CM', 'CN',
        'CO', 'CR', 'CU', 'CV', 'CW', 'CX', 'CY', 'CZ', 'DE', 'DJ', 'DK', 'DM', 'DO', 'DZ', 'EC', 'EE',
        'EG', 'EH', 'ER', 'ES', 'ET', 'FI', 'FJ', 'FK', 'FM', 'FO', 'FR', 'GA', 'GB', 'GD', 'GE', 'GF',
        'GG', 'GH', 'GI', 'GL', 'GM', 'GN', 'GP', 'GQ', 'GR', 'GS', 'GT', 'GU', 'GW', 'GY', 'HK', 'HM',
        'HN', 'HR', 'HT', 'HU', 'ID', 'IE', 'IL', 'IM', 'IN', 'IO', 'IQ', 'IR', 'IS', 'IT', 'JE', 'JM',
        'JO', 'JP', 'KE', 'KG', 'KH', 'KI', 'KM', 'KN', 'KP', 'KR', 'KW', 'KY', 'KZ', 'LA', 'LB', 'LC',
        'LI', 'LK', 'LR', 'LS', 'LT', 'LU', 'LV', 'LY', 'MA', 'MC', 'MD', 'ME', 'MF', 'MG', 'MH', 'MK',
        'ML', 'MM', 'MN', 'MO', 'MP', 'MQ', 'MR', 'MS', 'MT', 'MU', 'MV', 'MW', 'MX', 'MY', 'MZ', 'NA',
        'NC', 'NE', 'NF', 'NG', 'NI', 'NL', 'NO', 'NP', 'NR', 'NU', 'NZ', 'OM', 'PA', 'PE', 'PF', 'PG',
        'PH', 'PK', 'PL', 'PM', 'PN', 'PR', 'PS', 'PT', 'PW', 'PY', 'QA', 'RE', 'RO', 'RS', 'RU', 'RW',
        'SA', 'SB', 'SC', 'SD', 'SE', 'SG', 'SH', 'SI', 'SJ', 'SK', 'SL', 'SM', 'SN', 'SO', 'SR', 'SS',
        'ST', 'SV', 'SX', 'SY', 'SZ', 'TC', 'TD', 'TF', 'TG', 'TH', 'TJ', 'TK', 'TL', 'TM', 'TN', 'TO',
        'TR', 'TT', 'TV', 'TW', 'TZ', 'UA', 'UG', 'UM', 'US', 'UY', 'UZ', 'VA', 'VC', 'VE', 'VG', 'VI',
        'VN', 'VU', 'WF', 'WS', 'YE', 'YT', 'ZA', 'ZM', 'ZW'
    ]
    
    if country_code not in valid_country_codes:
        logger.warning(f"ISRC invalide (code pays incorrect): {country_code}")
        return False, None
    
    # Vérifier l'année (doit être entre 00 et 99)
    year_code = normalized_isrc[5:7]
    try:
        year = int(year_code)
        if year < 0 or year > 99:
            logger.warning(f"ISRC invalide (année incorrecte): {year_code}")
            return False, None
    except ValueError:
        logger.warning(f"ISRC invalide (année non numérique): {year_code}")
        return False, None
    
    # Formater l'ISRC avec des tirets pour l'affichage (optionnel)
    formatted_isrc = f"{normalized_isrc[:2]}-{normalized_isrc[2:5]}-{normalized_isrc[5:7]}-{normalized_isrc[7:]}"
    logger.debug(f"ISRC valide: {isrc} -> {normalized_isrc} (formaté: {formatted_isrc})")
    
    return True, normalized_isrc 