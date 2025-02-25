import asyncio
from database import get_db
from models import RadioStation, StationStatus
from music_recognition import MusicRecognizer
from audio_processor import AudioProcessor
from utils.logging_config import setup_logging
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configurer le logging
logger = setup_logging(__name__)

async def main():
    try:
        logger.info("Démarrage de la détection de musique")
        
        # Obtenir la session de base de données
        db = next(get_db())
        
        # Obtenir toutes les stations actives
        stations = db.query(RadioStation).filter(
            RadioStation.status == StationStatus.active,
            RadioStation.is_active == True
        ).all()
        
        if not stations:
            logger.warning("Aucune station active trouvée")
            return
        
        logger.info(f"Nombre de stations actives: {len(stations)}")
        
        # Initialiser le reconnaisseur de musique
        music_recognizer = MusicRecognizer(db, os.getenv('AUDD_API_KEY'))
        
        # Initialiser le processeur audio
        audio_processor = AudioProcessor(db, music_recognizer)
        
        # Lancer la détection sur toutes les stations
        result = await audio_processor.process_all_stations(stations)
        
        logger.info("Résultats de la détection:", extra={
            'total_stations': result['total_stations'],
            'successful_detections': result['successful_detections'],
            'failed_detections': result['failed_detections']
        })
        
        # Afficher les résultats détaillés
        for detection in result['results']:
            if detection.get('is_music'):
                logger.info("Musique détectée:", extra={
                    'station': detection.get('station'),
                    'track': detection.get('track', {}).get('title'),
                    'artist': detection.get('track', {}).get('artist'),
                    'confidence': detection.get('confidence')
                })
            else:
                logger.info("Pas de musique détectée:", extra={
                    'station': detection.get('station'),
                    'error': detection.get('error')
                })
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection: {str(e)}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main()) 