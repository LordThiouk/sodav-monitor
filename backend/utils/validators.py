from typing import Dict, Optional
import logging

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