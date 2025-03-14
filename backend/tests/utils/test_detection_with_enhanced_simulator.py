"""
Script pour tester la détection musicale avec le simulateur de radio amélioré.

Ce script permet de tester la détection musicale en utilisant le simulateur de radio amélioré.
Il capture le flux audio d'une station simulée, effectue la détection musicale,
et compare les résultats de détection avec les logs de diffusion pour évaluer la précision.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.app.config import settings
from backend.app.database.connection import get_db
from backend.app.models.artist import Artist
from backend.app.models.track import Track
from backend.app.services.audio_capture import AudioCapture
from backend.app.services.music_detector import MusicDetector
from backend.app.services.track_manager import TrackManager
from backend.tests.utils.enhanced_radio_simulator import EnhancedRadioSimulator

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_detection_with_enhanced_simulator")

# Répertoire des fichiers audio
AUDIO_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "audio" / "senegal"

# Chemin vers fpcalc.exe pour la génération d'empreintes acoustiques
FPCALC_PATH = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "bin" / "fpcalc.exe"

# Configurer fpcalc.exe si disponible
if FPCALC_PATH.exists():
    logger.info(f"fpcalc.exe trouvé à {FPCALC_PATH}")
    os.environ["FPCALC_PATH"] = str(FPCALC_PATH)
else:
    logger.warning(f"fpcalc.exe non trouvé à {FPCALC_PATH}. La génération d'empreintes acoustiques pourrait échouer.")

# Configuration de la base de données en mémoire pour les tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


async def setup_database():
    """Configure la base de données en mémoire pour les tests."""
    # Vérifier si fpcalc.exe est disponible
    if not FPCALC_PATH.exists():
        logger.error(f"fpcalc.exe non trouvé à {FPCALC_PATH}")
        logger.error("La génération d'empreintes acoustiques ne fonctionnera pas correctement.")
        logger.error("Veuillez télécharger fpcalc.exe et le placer dans le répertoire bin/")
        return False
    
    # Obtenir une session de base de données
    db = next(get_db())
    
    # Créer les tables
    settings.create_all_tables()
    
    logger.info("Base de données configurée avec succès")
    return True


async def create_test_data():
    """Crée des données de test dans la base de données."""
    db = next(get_db())
    
    # Créer un artiste
    artist = Artist(name="Dip Doundou Guiss")
    db.add(artist)
    db.commit()
    db.refresh(artist)
    logger.info(f"Artiste créé: {artist.name} (ID: {artist.id})")
    
    # Vérifier si des fichiers audio sont disponibles
    if not AUDIO_DIR.exists() or not any(AUDIO_DIR.glob("*.mp3")):
        logger.error(f"Aucun fichier audio trouvé dans {AUDIO_DIR}")
        return False
    
    # Créer des pistes pour chaque fichier audio
    track_count = 0
    for file_path in AUDIO_DIR.glob("*.mp3"):
        track_name = file_path.stem
        
        # Créer la piste
        track = Track(
            name=track_name,
            artist_id=artist.id,
            release_date=datetime.now().date(),
            genre="Hip-Hop/Rap"
        )
        
        db.add(track)
        db.commit()
        db.refresh(track)
        
        logger.info(f"Piste créée: {track.name} (ID: {track.id})")
        track_count += 1
    
    logger.info(f"{track_count} pistes créées avec succès")
    return track_count > 0


async def generate_fingerprints():
    """Génère des empreintes acoustiques pour les pistes."""
    db = next(get_db())
    track_manager = TrackManager(db)
    
    # Récupérer toutes les pistes
    tracks = db.query(Track).all()
    
    # Générer des empreintes pour chaque piste
    for track in tracks:
        # Trouver le fichier audio correspondant
        file_path = None
        for path in AUDIO_DIR.glob("*.mp3"):
            if track.name in path.stem:
                file_path = path
                break
        
        if not file_path:
            logger.warning(f"Fichier audio non trouvé pour la piste {track.name}")
            continue
        
        # Générer l'empreinte acoustique
        logger.info(f"Génération de l'empreinte acoustique pour {track.name}...")
        fingerprint_result = track_manager.extract_fingerprint(file_path)
        
        if fingerprint_result and fingerprint_result.get("success"):
            logger.info(f"Empreinte générée avec succès pour {track.name}")
        else:
            logger.error(f"Échec de la génération d'empreinte pour {track.name}")
    
    logger.info("Génération des empreintes terminée")
    return True


async def test_detection():
    """Teste la détection musicale avec le simulateur de radio amélioré."""
    # Configurer la base de données
    db_setup = await setup_database()
    if not db_setup:
        logger.error("Échec de la configuration de la base de données")
        return
    
    # Créer des données de test
    data_created = await create_test_data()
    if not data_created:
        logger.error("Échec de la création des données de test")
        return
    
    # Générer des empreintes acoustiques
    fingerprints_generated = await generate_fingerprints()
    if not fingerprints_generated:
        logger.error("Échec de la génération des empreintes acoustiques")
        return
    
    # Créer un simulateur de radio amélioré
    simulator = EnhancedRadioSimulator()
    
    # Créer une station avec les fichiers audio sénégalais
    station = simulator.create_station(
        name="Radio Sénégal Test",
        audio_dir=AUDIO_DIR,
        genre="Hip-Hop/Rap",
        country="Sénégal",
        language="Wolof/Français"
    )
    
    if not station:
        logger.error("Échec de la création de la station")
        return
    
    # Démarrer l'enregistrement des logs
    simulator.start_logging()
    
    # Démarrer la station
    station.start()
    logger.info(f"Station démarrée: {station.name} sur http://localhost:{station.port}")
    
    # Attendre que la station soit prête
    logger.info("Attente de 5 secondes pour que la station soit prête...")
    await asyncio.sleep(5)
    
    # Créer un détecteur de musique
    music_detector = MusicDetector()
    
    # Créer un capteur audio
    audio_capture = AudioCapture(f"http://localhost:{station.port}")
    
    # Effectuer plusieurs détections
    detection_count = 3
    detection_duration = 15  # secondes
    
    for i in range(detection_count):
        logger.info(f"Détection {i+1}/{detection_count}...")
        
        # Capturer l'audio
        logger.info(f"Capture audio pendant {detection_duration} secondes...")
        audio_data = await audio_capture.capture(duration_seconds=detection_duration)
        
        if not audio_data:
            logger.error("Échec de la capture audio")
            continue
        
        logger.info(f"Audio capturé: {len(audio_data)} octets")
        
        # Détecter la musique
        logger.info("Analyse de l'audio pour détecter la musique...")
        detection_result = music_detector.detect(audio_data)
        
        if detection_result["is_music"]:
            logger.info(f"Musique détectée avec une confiance de {detection_result['confidence']:.2f}")
            
            # Rechercher des correspondances
            db = next(get_db())
            track_manager = TrackManager(db)
            
            # Rechercher des correspondances locales
            logger.info("Recherche de correspondances locales...")
            local_matches = track_manager.find_local_matches(audio_data)
            
            if local_matches:
                logger.info(f"Correspondances locales trouvées: {len(local_matches)}")
                for match in local_matches:
                    logger.info(f"  - {match['track_name']} (Score: {match['score']:.2f})")
                    
                    # Enregistrer la détection dans le simulateur
                    simulator.register_detection(
                        station_name=station.name,
                        track_name=match['track_name'],
                        detection_method="fingerprint",
                        confidence=match['score'],
                        detected_at=datetime.now(),
                        play_duration=detection_result.get('play_duration', 0),
                        fingerprint=match.get('fingerprint', ''),
                        metadata={"detection_index": i+1}
                    )
            else:
                logger.warning("Aucune correspondance locale trouvée")
        else:
            logger.info("Aucune musique détectée")
        
        # Attendre avant la prochaine détection
        if i < detection_count - 1:
            logger.info("Attente de 10 secondes avant la prochaine détection...")
            await asyncio.sleep(10)
    
    # Obtenir les logs de lecture
    play_logs = simulator.get_play_logs()
    logger.info(f"Logs de lecture: {len(play_logs)} événements")
    
    # Obtenir les logs de détection
    detection_logs = simulator.detection_logs
    logger.info(f"Logs de détection: {len(detection_logs)} événements")
    
    # Calculer la durée totale de lecture
    total_play_duration = simulator.get_total_play_duration()
    logger.info(f"Durée totale de lecture: {total_play_duration:.2f} secondes")
    
    # Exporter les logs
    simulator.export_logs("detection_test_logs.json", format="json")
    logger.info("Logs exportés dans detection_test_logs.json")
    
    # Arrêter la station
    station.stop()
    logger.info("Station arrêtée")
    
    # Arrêter l'enregistrement des logs
    simulator.stop_logging()
    
    logger.info("Test de détection terminé avec succès")


if __name__ == "__main__":
    asyncio.run(test_detection()) 