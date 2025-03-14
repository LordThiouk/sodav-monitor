"""
Script de test amélioré pour la détection musicale avec les fichiers audio sénégalais.

Ce script utilise le simulateur de radio amélioré pour tester la détection musicale
en conditions réelles, avec enregistrement précis des durées de lecture et des détections.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from backend.detection.audio_processor.track_manager.track_manager import TrackManager
from backend.models.models import Artist, Base, RadioStation, Track, TrackDetection
from backend.tests.utils.enhanced_radio_simulator import EnhancedRadioSimulator
from backend.utils.detection.music_detector import MusicDetector
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_senegal_detection_enhanced")

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


async def generate_fingerprints(db_session, tracks, track_files):
    """
    Génère les empreintes acoustiques pour les pistes.
    
    Args:
        db_session: Session de base de données
        tracks: Liste des pistes
        track_files: Dictionnaire des chemins de fichiers
    """
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


async def detect_music(detector, db_station, simulator, station_name, duration=15):
    """
    Détecte la musique sur une station et enregistre les résultats.
    
    Args:
        detector: Détecteur de musique
        db_station: Station dans la base de données
        simulator: Simulateur de radio
        station_name: Nom de la station
        duration: Durée de capture en secondes
        
    Returns:
        Résultat de la détection
    """
    logger.info(f"Détection sur {station_name}...")
    
    # Capturer et analyser l'audio
    detection_result = await detector.process_track(
        station_id=db_station.id,
        stream_url=db_station.stream_url,
        capture_duration=duration,
    )
    
    # Afficher le résultat de la détection
    logger.info(f"Résultat de la détection: {detection_result}")
    
    # Vérifier si la détection a réussi
    if detection_result and detection_result.get("success", False):
        track_id = detection_result.get("track_id")
        
        if track_id:
            # Récupérer les informations sur le morceau détecté
            track = detector.db.query(Track).filter(Track.id == track_id).first()
            
            if track:
                logger.info(f"Morceau détecté: {track.title} par {track.artist.name if track.artist else 'Inconnu'}")
                
                # Récupérer la dernière détection
                detection = (
                    detector.db.query(TrackDetection)
                    .filter(
                        TrackDetection.track_id == track_id,
                        TrackDetection.station_id == db_station.id,
                    )
                    .order_by(TrackDetection.detected_at.desc())
                    .first()
                )
                
                if detection:
                    # Enregistrer la détection dans le simulateur
                    simulator.register_detection(
                        station_name=station_name,
                        track_name=track.title,
                        detection_method=detection_result.get("method", "unknown"),
                        confidence=detection.confidence,
                        detected_at=detection.detected_at,
                        play_duration=detection.play_duration.total_seconds() if detection.play_duration else 0,
                        fingerprint=track.fingerprint,
                        metadata={
                            "artist": track.artist.name if track.artist else "Inconnu",
                            "album": track.album,
                            "genre": track.genre,
                            "isrc": track.isrc,
                        }
                    )
                    
                    logger.info(
                        f"Détection enregistrée: {track.title} "
                        f"(durée: {detection.play_duration.total_seconds() if detection.play_duration else 0:.2f}s, "
                        f"confiance: {detection.confidence:.2f})"
                    )
    
    return detection_result


async def verify_detection_accuracy(db_session, simulator, station_name):
    """
    Vérifie la précision des détections par rapport aux logs de lecture.
    
    Args:
        db_session: Session de base de données
        simulator: Simulateur de radio
        station_name: Nom de la station
    """
    logger.info(f"Vérification de la précision des détections pour {station_name}...")
    
    # Récupérer les logs de lecture
    play_logs = simulator.get_play_logs(station_name=station_name)
    play_logs = [log for log in play_logs if log["event_type"] == "track_end"]
    
    # Récupérer les logs de détection
    detection_logs = [log for log in simulator.detection_logs if log["station_name"] == station_name]
    
    if not play_logs or not detection_logs:
        logger.warning("Pas assez de données pour vérifier la précision")
        return
    
    # Calculer la durée totale de lecture
    total_play_duration = simulator.get_total_play_duration(station_name=station_name)
    
    # Calculer la durée totale détectée
    total_detected_duration = sum(log["play_duration"] for log in detection_logs)
    
    # Calculer le taux de couverture
    coverage_rate = (total_detected_duration / total_play_duration) * 100 if total_play_duration > 0 else 0
    
    logger.info(f"Durée totale de lecture: {total_play_duration:.2f}s")
    logger.info(f"Durée totale détectée: {total_detected_duration:.2f}s")
    logger.info(f"Taux de couverture: {coverage_rate:.2f}%")
    
    # Vérifier la précision des détections
    for detection in detection_logs:
        # Trouver le log de lecture correspondant
        matching_logs = [
            log for log in play_logs 
            if log["track_name"].endswith(detection["track_name"] + ".mp3")
            and abs((log["timestamp"] - detection["detected_at"]).total_seconds()) < 30
        ]
        
        if matching_logs:
            matching_log = matching_logs[0]
            duration_diff = abs(matching_log["duration"] - detection["play_duration"])
            duration_diff_percent = (duration_diff / matching_log["duration"]) * 100 if matching_log["duration"] > 0 else 0
            
            logger.info(
                f"Morceau: {detection['track_name']} - "
                f"Durée réelle: {matching_log['duration']:.2f}s, "
                f"Durée détectée: {detection['play_duration']:.2f}s, "
                f"Différence: {duration_diff:.2f}s ({duration_diff_percent:.2f}%)"
            )
        else:
            logger.warning(f"Aucun log de lecture correspondant pour {detection['track_name']}")


async def test_detection_with_enhanced_simulator():
    """
    Teste la détection musicale avec le simulateur de radio amélioré.
    
    Ce test vérifie que:
    1. Le simulateur diffuse correctement les fichiers audio
    2. Le système détecte les morceaux joués
    3. Les durées de lecture sont correctement enregistrées
    4. Les détections sont précises par rapport aux logs de lecture
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
        
        # Générer les empreintes acoustiques
        await generate_fingerprints(db_session, tracks, track_files)
        
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
        
        if not station or not station.playlist:
            logger.error("Impossible de créer la station simulée")
            return
        
        # Démarrer l'enregistrement des logs
        simulator.start_logging()
        
        # Démarrer la station
        station.start()
        logger.info(f"Station démarrée: {station.name} sur http://localhost:{station.port}")
        
        # Démarrer le monitoring
        simulator.start_monitoring(interval_seconds=5)
        
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
            
            # Créer un détecteur de musique
            detector = MusicDetector(db_session)
            
            # Laisser la station diffuser pendant un moment
            logger.info("Attente de 10 secondes pour laisser la station démarrer...")
            await asyncio.sleep(10)
            
            # Effectuer plusieurs détections
            for i in range(3):
                # Effectuer une détection
                await detect_music(
                    detector=detector,
                    db_station=db_station,
                    simulator=simulator,
                    station_name=station.name,
                    duration=15
                )
                
                # Attendre entre les détections
                await asyncio.sleep(20)
            
            # Simuler une interruption
            logger.info("Simulation d'une interruption...")
            simulator.simulate_interruption(station.name, duration_seconds=5)
            
            # Attendre un peu
            await asyncio.sleep(10)
            
            # Effectuer une autre détection après l'interruption
            await detect_music(
                detector=detector,
                db_station=db_station,
                simulator=simulator,
                station_name=station.name,
                duration=15
            )
            
            # Sélectionner manuellement un morceau
            if station.playlist:
                logger.info("Sélection manuelle d'un morceau...")
                simulator.select_track(station.name, 0)
                
                # Attendre un peu
                await asyncio.sleep(10)
                
                # Effectuer une détection sur le morceau sélectionné
                await detect_music(
                    detector=detector,
                    db_station=db_station,
                    simulator=simulator,
                    station_name=station.name,
                    duration=15
                )
            
            # Vérifier la précision des détections
            await verify_detection_accuracy(db_session, simulator, station.name)
            
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
            
            # Exporter les logs
            simulator.export_logs("detection_test_logs.json", format="json")
            logger.info("Logs exportés dans detection_test_logs.json")
            
        finally:
            # Arrêter le monitoring
            simulator.stop_monitoring()
            
            # Arrêter la station
            station.stop()
            logger.info("Station arrêtée")
            
            # Arrêter l'enregistrement des logs
            simulator.stop_logging()
            
    finally:
        # Fermer la session de base de données
        db_session.close()
        Base.metadata.drop_all(engine)


if __name__ == "__main__":
    # Exécuter le test
    asyncio.run(test_detection_with_enhanced_simulator()) 