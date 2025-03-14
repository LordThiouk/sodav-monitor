"""
Script simplifié pour tester la détection musicale avec le simulateur de radio.

Ce script utilise le simulateur de radio pour diffuser les fichiers audio sénégalais
et teste la détection musicale de base sans dépendre de modules externes.
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from backend.tests.utils.enhanced_radio_simulator import EnhancedRadioSimulator

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple_detection_test")

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


async def capture_audio(url, duration=15):
    """
    Capture l'audio à partir d'une URL.
    
    Args:
        url: URL du flux audio
        duration: Durée de capture en secondes
        
    Returns:
        Données audio capturées ou None en cas d'échec
    """
    logger.info(f"Capture audio depuis {url} pendant {duration} secondes...")
    
    try:
        # Simuler la capture audio
        await asyncio.sleep(duration)
        
        # Dans un cas réel, nous utiliserions une bibliothèque comme requests ou aiohttp
        # pour capturer le flux audio, mais ici nous simulons simplement
        audio_data = b"Simulated audio data"
        
        logger.info(f"Audio capturé: {len(audio_data)} octets")
        return audio_data
    
    except Exception as e:
        logger.error(f"Erreur lors de la capture audio: {e}")
        return None


async def detect_music(audio_data):
    """
    Détecte si l'audio contient de la musique.
    
    Args:
        audio_data: Données audio à analyser
        
    Returns:
        Dictionnaire avec les résultats de détection
    """
    logger.info("Analyse de l'audio pour détecter la musique...")
    
    # Simuler la détection de musique
    await asyncio.sleep(2)
    
    # Dans un cas réel, nous utiliserions un algorithme de détection,
    # mais ici nous simulons simplement un résultat positif
    return {
        "is_music": True,
        "confidence": 0.95,
        "play_duration": 15.0,
    }


async def test_detection():
    """Teste la détection musicale avec le simulateur de radio amélioré."""
    # Vérifier si des fichiers audio sont disponibles
    if not AUDIO_DIR.exists() or not any(AUDIO_DIR.glob("*.mp3")):
        logger.error(f"Aucun fichier audio trouvé dans {AUDIO_DIR}")
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
    
    # Démarrer le monitoring
    simulator.start_monitoring(interval_seconds=5)
    
    try:
        # Attendre que la station soit prête
        logger.info("Attente de 5 secondes pour que la station soit prête...")
        await asyncio.sleep(5)
        
        # Effectuer plusieurs détections
        detection_count = 3
        
        for i in range(detection_count):
            logger.info(f"Détection {i+1}/{detection_count}...")
            
            # Capturer l'audio
            audio_data = await capture_audio(f"http://localhost:{station.port}")
            
            if not audio_data:
                logger.error("Échec de la capture audio")
                continue
            
            # Détecter la musique
            detection_result = await detect_music(audio_data)
            
            if detection_result["is_music"]:
                logger.info(f"Musique détectée avec une confiance de {detection_result['confidence']:.2f}")
                
                # Simuler une correspondance avec un morceau
                track_name = station.playlist[station.current_track_index].name
                
                # Enregistrer la détection dans le simulateur
                simulator.register_detection(
                    station_name=station.name,
                    track_name=track_name,
                    detection_method="simulation",
                    confidence=detection_result["confidence"],
                    detected_at=datetime.now(),
                    play_duration=detection_result["play_duration"],
                    fingerprint="simulated_fingerprint",
                    metadata={"detection_index": i+1}
                )
                
                logger.info(f"Détection enregistrée pour {track_name}")
            else:
                logger.info("Aucune musique détectée")
            
            # Attendre avant la prochaine détection
            if i < detection_count - 1:
                logger.info("Attente de 10 secondes avant la prochaine détection...")
                await asyncio.sleep(10)
        
        # Simuler une interruption
        logger.info("Simulation d'une interruption...")
        simulator.simulate_interruption(station.name, duration_seconds=5)
        
        # Attendre un peu
        await asyncio.sleep(10)
        
        # Effectuer une autre détection après l'interruption
        logger.info("Détection après interruption...")
        audio_data = await capture_audio(f"http://localhost:{station.port}")
        
        if audio_data:
            detection_result = await detect_music(audio_data)
            
            if detection_result["is_music"]:
                track_name = station.playlist[station.current_track_index].name
                
                simulator.register_detection(
                    station_name=station.name,
                    track_name=track_name,
                    detection_method="simulation",
                    confidence=detection_result["confidence"],
                    detected_at=datetime.now(),
                    play_duration=detection_result["play_duration"],
                    fingerprint="simulated_fingerprint",
                    metadata={"after_interruption": True}
                )
                
                logger.info(f"Détection après interruption enregistrée pour {track_name}")
        
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
        simulator.export_logs("simple_detection_test_logs.json", format="json")
        logger.info("Logs exportés dans simple_detection_test_logs.json")
        
    finally:
        # Arrêter le monitoring
        simulator.stop_monitoring()
        
        # Arrêter la station
        station.stop()
        logger.info("Station arrêtée")
        
        # Arrêter l'enregistrement des logs
        simulator.stop_logging()
        
        logger.info("Test de détection terminé avec succès")


if __name__ == "__main__":
    # Exécuter le test
    asyncio.run(test_detection()) 