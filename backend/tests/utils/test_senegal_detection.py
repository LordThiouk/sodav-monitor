"""
Script amélioré pour tester la détection musicale avec les fichiers audio sénégalais.

Ce script utilise le simulateur radio pour diffuser les fichiers audio sénégalais
et teste la détection musicale complète, y compris la génération d'empreintes acoustiques
avec fpcalc.exe.
"""

import asyncio
import logging
import os
import time
from datetime import timedelta
from pathlib import Path

from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.track_manager.track_manager import TrackManager
from backend.models.models import Artist, Base, RadioStation, Track, TrackDetection
from backend.tests.utils.radio_simulator import RadioSimulator
from backend.utils.detection.music_detector import MusicDetector
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_senegal_detection")

# Répertoire des fichiers audio
AUDIO_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "audio" / "senegal"

# Chemin vers fpcalc.exe pour la génération d'empreintes acoustiques
FPCALC_PATH = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "bin" / "fpcalc.exe"

# Configuration de la base de données en mémoire pour les tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


async def setup_database():
    """Configure la base de données en mémoire pour les tests."""
    # Configurer fpcalc.exe
    if FPCALC_PATH.exists():
        logger.info(f"fpcalc.exe trouvé à {FPCALC_PATH}")
        # Définir la variable d'environnement pour que le système puisse trouver fpcalc
        os.environ["FPCALC_PATH"] = str(FPCALC_PATH)
    else:
        logger.warning(f"fpcalc.exe non trouvé à {FPCALC_PATH}. La génération d'empreintes acoustiques pourrait échouer.")
    
    # Créer la base de données
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    return engine, session


async def create_test_data(db_session):
    """Crée des données de test dans la base de données."""
    # Créer un artiste de test
    artist = Artist(
        name="Dip Doundou Guiss",
        country="Sénégal",
        region="Dakar",
        type="musician",
        label="Prince Arts",
    )
    db_session.add(artist)
    db_session.commit()
    
    logger.info(f"Artiste créé: {artist.name} (ID: {artist.id})")
    
    # Créer des entrées de pistes pour les fichiers audio
    tracks = []
    track_files = {}  # Dictionnaire pour stocker les chemins de fichiers
    
    for audio_file in AUDIO_DIR.glob("*.mp3"):
        track_name = audio_file.stem
        
        # Nettoyer le nom de la piste
        track_name = track_name.replace("DIP DOUNDOU GUISS - ", "").replace("Dip Doundou Guiss - ", "")
        
        track = Track(
            title=track_name,
            artist_id=artist.id,
            isrc=f"SENTEST{len(tracks) + 1:04d}",
            release_date="2023",
            genre="Hip-Hop/Rap",
            label="Prince Arts",
            album="Sénégal Test",
        )
        db_session.add(track)
        tracks.append(track)
        
        # Stocker le chemin du fichier séparément
        track_files[track_name] = str(audio_file)
    
    db_session.commit()
    
    for track in tracks:
        logger.info(f"Piste créée: {track.title} (ID: {track.id})")
    
    return artist, tracks, track_files


async def test_detection_with_senegal_music():
    """
    Teste la détection musicale avec des fichiers audio sénégalais.
    
    Ce test vérifie que:
    1. Le simulateur radio diffuse correctement les fichiers audio
    2. Le système détecte les morceaux joués
    3. Les empreintes acoustiques sont correctement générées avec fpcalc.exe
    """
    # Vérifier si des fichiers audio sont disponibles
    if not AUDIO_DIR.exists() or not any(AUDIO_DIR.glob("*.mp3")):
        logger.error(f"Aucun fichier audio trouvé dans {AUDIO_DIR}")
        return
    
    # Configurer la base de données
    engine, db_session = await setup_database()
    
    try:
        # Créer des données de test
        artist, tracks, track_files = await create_test_data(db_session)
        
        # Créer un simulateur radio
        simulator = RadioSimulator()
        station = simulator.create_station(name="Radio Sénégal Test", audio_dir=AUDIO_DIR)
        
        if not station or not station.playlist:
            logger.error("Impossible de créer la station simulée")
            return
        
        # Démarrer la station
        station.start()
        logger.info(f"Station démarrée: {station.name} sur http://localhost:{station.port}")
        
        try:
            # Créer une entrée de station dans la base de données
            db_station = RadioStation(
                name="Radio Sénégal Test",
                stream_url=f"http://localhost:{station.port}",
                country="Sénégal",
                language="Wolof/Français",
                status="active",
                is_active=True,
            )
            db_session.add(db_station)
            db_session.commit()
            
            logger.info(f"Station créée dans la base de données: {db_station.name} (ID: {db_station.id})")
            
            # Créer un gestionnaire de pistes pour générer les empreintes acoustiques
            track_manager = TrackManager(db_session)
            
            # Générer les empreintes acoustiques pour toutes les pistes
            logger.info("Génération des empreintes acoustiques pour les pistes...")
            for track in tracks:
                # Récupérer le chemin du fichier à partir du dictionnaire
                file_path = track_files.get(track.title)
                
                if file_path and os.path.exists(file_path):
                    logger.info(f"Génération de l'empreinte acoustique pour {track.title}...")
                    
                    # Générer l'empreinte acoustique
                    fingerprint_result = track_manager.extract_fingerprint(file_path)
                    
                    if fingerprint_result and "fingerprint" in fingerprint_result:
                        # Mettre à jour la piste avec l'empreinte acoustique
                        track.fingerprint = fingerprint_result["fingerprint"]
                        track.duration = timedelta(seconds=fingerprint_result.get("duration", 0))
                        db_session.commit()
                        
                        logger.info(
                            f"Empreinte générée pour {track.title} "
                            f"(durée: {fingerprint_result.get('duration', 0):.2f}s, "
                            f"fingerprint: {track.fingerprint[:20]}...)"
                        )
                    else:
                        logger.warning(
                            f"Échec de la génération de l'empreinte pour {track.title}: "
                            f"{fingerprint_result.get('error', 'Erreur inconnue')}"
                        )
            
            # Créer un détecteur de musique
            detector = MusicDetector(db_session)
            
            # Effectuer plusieurs détections pour capturer différents morceaux
            for i in range(3):
                logger.info(f"Détection {i+1}/3...")
                
                # Capturer et analyser l'audio
                detection_result = await detector.process_track(
                    station_id=db_station.id,
                    stream_url=db_station.stream_url,
                    capture_duration=15,  # Capturer 15 secondes d'audio
                )
                
                # Afficher le résultat de la détection
                logger.info(f"Résultat de la détection: {detection_result}")
                
                # Vérifier si la détection a réussi
                if detection_result and detection_result.get("success", False):
                    track_id = detection_result.get("track_id")
                    
                    if track_id:
                        # Récupérer les informations sur le morceau détecté
                        track = db_session.query(Track).filter(Track.id == track_id).first()
                        
                        if track:
                            logger.info(f"Morceau détecté: {track.title} par {track.artist.name if track.artist else 'Inconnu'}")
                            
                            # Vérifier les détections
                            detections = (
                                db_session.query(TrackDetection)
                                .filter(
                                    TrackDetection.track_id == track_id,
                                    TrackDetection.station_id == db_station.id,
                                )
                                .order_by(TrackDetection.detected_at.desc())
                                .all()
                            )
                            
                            for detection in detections:
                                logger.info(
                                    f"Détection: {detection.detected_at}, "
                                    f"Durée: {detection.play_duration.total_seconds() if detection.play_duration else 'N/A'}s, "
                                    f"Confiance: {detection.confidence:.2f}"
                                )
                    else:
                        logger.warning("Aucun track_id dans le résultat de détection")
                else:
                    error_msg = (
                        detection_result.get("error", "Erreur inconnue")
                        if detection_result
                        else "Aucun résultat"
                    )
                    logger.warning(f"Échec de la détection: {error_msg}")
                
                # Attendre entre les détections
                await asyncio.sleep(10)
            
            # Afficher un résumé des détections
            logger.info("Résumé des détections:")
            
            # Récupérer toutes les détections
            all_detections = (
                db_session.query(TrackDetection)
                .filter(TrackDetection.station_id == db_station.id)
                .order_by(TrackDetection.detected_at.desc())
                .all()
            )
            
            if all_detections:
                logger.info(f"{len(all_detections)} détections enregistrées")
                
                # Calculer le temps de jeu total
                total_play_time = sum(
                    d.play_duration.total_seconds() for d in all_detections if d.play_duration
                )
                
                logger.info(f"Temps de jeu total: {total_play_time:.2f}s")
                
                # Afficher les détails de chaque détection
                for i, detection in enumerate(all_detections):
                    track = db_session.query(Track).filter(Track.id == detection.track_id).first()
                    logger.info(
                        f"Détection {i+1}: {track.title if track else 'Inconnu'}, "
                        f"Durée: {detection.play_duration.total_seconds() if detection.play_duration else 'N/A'}s, "
                        f"Confiance: {detection.confidence:.2f}"
                    )
            else:
                logger.warning("Aucune détection enregistrée")
            
        finally:
            # Arrêter la station
            station.stop()
            logger.info("Station arrêtée")
            
    finally:
        # Fermer la session de base de données
        db_session.close()
        Base.metadata.drop_all(engine)


if __name__ == "__main__":
    # Exécuter le test
    asyncio.run(test_detection_with_senegal_music()) 