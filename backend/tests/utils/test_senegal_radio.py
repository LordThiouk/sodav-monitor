"""
Script pour tester la détection et le temps de jeu avec le simulateur radio.

Ce script utilise le simulateur radio pour diffuser les fichiers audio sénégalais
et tester la détection musicale et le calcul du temps de jeu.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.track_manager.track_manager import TrackManager
from backend.models.models import Artist, Base
from backend.models.models import RadioStation as Station
from backend.models.models import StationTrackStats, Track, TrackDetection, TrackStats
from backend.tests.utils.radio_simulator import RadioSimulator
from backend.utils.detection.music_detector import MusicDetector

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_senegal_radio")

# Répertoire des fichiers audio
AUDIO_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "audio" / "senegal"

# Configuration de la base de données en mémoire pour les tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


async def setup_database():
    """Configure la base de données en mémoire pour les tests."""
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
    
    return artist


async def test_detection_with_senegal_music():
    """
    Teste la détection musicale avec des fichiers audio sénégalais.
    
    Ce test vérifie que:
    1. Le simulateur radio diffuse correctement les fichiers audio
    2. Le système détecte les morceaux joués
    3. Le temps de jeu est correctement calculé
    4. Les statistiques sont mises à jour
    """
    # Vérifier si des fichiers audio sont disponibles
    if not AUDIO_DIR.exists() or not any(AUDIO_DIR.glob("*.mp3")):
        logger.error(f"Aucun fichier audio trouvé dans {AUDIO_DIR}")
        return
    
    # Configurer la base de données
    engine, db_session = await setup_database()
    
    try:
        # Créer des données de test
        artist = await create_test_data(db_session)
        
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
            db_station = Station(
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
                            
                            # Vérifier les statistiques
                            track_stats = (
                                db_session.query(TrackStats)
                                .filter(TrackStats.track_id == track_id)
                                .first()
                            )
                            
                            if track_stats:
                                logger.info(
                                    f"Statistiques: {track_stats.total_plays} lectures, "
                                    f"{track_stats.total_play_time.total_seconds():.2f}s de temps de jeu"
                                )
                            
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
                                    f"Durée: {detection.play_duration.total_seconds():.2f}s, "
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