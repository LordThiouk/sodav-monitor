"""
Script de test pour la détection musicale avec plusieurs stations simultanées.

Ce script crée plusieurs stations de radio virtuelles et teste la détection musicale
en parallèle sur toutes les stations, en utilisant de vrais appels API.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("multi_station_test.log")
    ]
)
logger = logging.getLogger("multi_station_test")

# Importer les modules nécessaires
try:
    from backend.tests.utils.enhanced_radio_simulator import EnhancedRadioSimulator, create_multi_station_simulator
    from backend.tests.utils.real_api_detection_test import capture_audio, detect_music
except ImportError:
    logger.error("Impossible d'importer les modules nécessaires. Vérifiez que les fichiers existent.")
    sys.exit(1)

# Répertoire des fichiers audio
AUDIO_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "audio"

# Chemin vers fpcalc.exe pour la génération d'empreintes acoustiques
FPCALC_PATH = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "bin" / "fpcalc.exe"

# Configurer fpcalc.exe si disponible
if FPCALC_PATH.exists():
    logger.info(f"fpcalc.exe trouvé à {FPCALC_PATH}")
    os.environ["FPCALC_PATH"] = str(FPCALC_PATH)
else:
    logger.warning(f"fpcalc.exe non trouvé à {FPCALC_PATH}. La génération d'empreintes acoustiques pourrait échouer.")


def setup_api_keys():
    """Configure les clés API nécessaires pour les tests."""
    # Vérifier si les clés API sont déjà définies
    acoustid_key = os.environ.get("ACOUSTID_API_KEY")
    audd_key = os.environ.get("AUDD_API_KEY")
    
    if not acoustid_key:
        logger.warning("Clé API AcoustID non définie dans les variables d'environnement.")
        acoustid_input = input("Entrez votre clé API AcoustID (laissez vide pour ignorer): ").strip()
        if acoustid_input:
            os.environ["ACOUSTID_API_KEY"] = acoustid_input
            logger.info("Clé API AcoustID configurée.")
    else:
        logger.info("Clé API AcoustID déjà configurée.")
    
    if not audd_key:
        logger.warning("Clé API Audd.io non définie dans les variables d'environnement.")
        audd_input = input("Entrez votre clé API Audd.io (laissez vide pour ignorer): ").strip()
        if audd_input:
            os.environ["AUDD_API_KEY"] = audd_input
            logger.info("Clé API Audd.io configurée.")
    else:
        logger.info("Clé API Audd.io déjà configurée.")


def check_audio_files():
    """Vérifie si des fichiers audio sont disponibles pour les tests."""
    # Répertoire des fichiers audio pour le Sénégal
    senegal_dir = AUDIO_DIR / "senegal"
    
    if not senegal_dir.exists() or not any(senegal_dir.glob("*.mp3")):
        logger.error(f"Aucun fichier audio trouvé dans {senegal_dir}")
        logger.info("Veuillez d'abord télécharger ou copier des fichiers audio dans ce répertoire.")
        
        # Proposer de copier des fichiers audio
        copy_files = input("Voulez-vous copier des fichiers audio depuis le dossier Téléchargements? (o/n): ").strip().lower()
        if copy_files in ["o", "oui"]:
            try:
                from backend.tests.utils.copy_downloaded_audio import copy_audio_files
                copied = copy_audio_files()
                if copied > 0:
                    logger.info(f"{copied} fichiers audio copiés avec succès.")
                    return True
                else:
                    logger.error("Aucun fichier audio n'a été copié.")
                    return False
            except ImportError:
                logger.error("Impossible d'importer le module de copie de fichiers audio.")
                return False
        return False
    
    return True


async def detect_music_on_station(simulator, station_name, num_detections=3, detection_duration=15):
    """
    Détecte la musique sur une station spécifique.
    
    Args:
        simulator: Instance du simulateur de radio
        station_name: Nom de la station
        num_detections: Nombre de détections à effectuer
        detection_duration: Durée de chaque détection en secondes
        
    Returns:
        Liste des résultats de détection
    """
    station = simulator.stations.get(station_name)
    if not station:
        logger.error(f"Station non trouvée: {station_name}")
        return []
    
    stream_url = f"http://localhost:{station.port}"
    logger.info(f"Début des détections sur {station_name} ({stream_url})")
    
    detection_results = []
    
    for i in range(num_detections):
        logger.info(f"Détection {i+1}/{num_detections} sur {station_name}...")
        
        # Capturer l'audio
        audio_data = await capture_audio(stream_url, duration=detection_duration)
        
        if not audio_data:
            logger.error(f"Échec de la capture audio sur {station_name}")
            continue
        
        # Détecter la musique
        detection_start_time = time.time()
        detection_result = await detect_music(audio_data)
        detection_end_time = time.time()
        detection_duration_real = detection_end_time - detection_start_time
        
        # Traiter le résultat
        if detection_result["is_music"]:
            if detection_result["success"]:
                logger.info(
                    f"[{station_name}] Musique détectée: {detection_result.get('title', 'Unknown')} "
                    f"par {detection_result.get('artist', 'Unknown')} "
                    f"(méthode: {detection_result['method']}, "
                    f"confiance: {detection_result['confidence']:.2f})"
                )
                
                # Enregistrer la détection dans le simulateur
                simulator.register_detection(
                    station_name=station_name,
                    track_name=detection_result.get("title", "Unknown"),
                    detection_method=detection_result["method"],
                    confidence=detection_result["confidence"],
                    detected_at=datetime.now(),
                    play_duration=detection_result["play_duration"],
                    fingerprint=detection_result["fingerprint"],
                    metadata={
                        "artist": detection_result.get("artist", "Unknown"),
                        "album": detection_result.get("album", "Unknown"),
                        "year": detection_result.get("year", ""),
                        "detection_time": detection_duration_real,
                        "detection_index": i+1
                    }
                )
            else:
                logger.warning(
                    f"[{station_name}] Musique détectée mais non identifiée "
                    f"(méthode: {detection_result['method']}, "
                    f"erreur: {detection_result['error']})"
                )
        else:
            logger.info(f"[{station_name}] Aucune musique détectée")
        
        detection_results.append(detection_result)
        
        # Attendre entre les détections
        if i < num_detections - 1:
            await asyncio.sleep(10)
    
    return detection_results


async def run_multi_station_test():
    """Exécute le test de détection sur plusieurs stations simultanément."""
    # Vérifier les fichiers audio
    if not check_audio_files():
        logger.error("Test annulé: fichiers audio manquants")
        return
    
    # Configurer les clés API
    setup_api_keys()
    
    # Créer les répertoires pour les différentes stations
    senegal_dir = AUDIO_DIR / "senegal"
    
    # Créer un simulateur avec plusieurs stations
    simulator = create_multi_station_simulator({
        "Radio Sénégal": {
            "audio_dir": senegal_dir,
            "genre": "Hip-Hop/Rap",
            "country": "Sénégal",
            "language": "Wolof/Français",
            "port": 8765
        },
        "Radio Sénégal 2": {
            "audio_dir": senegal_dir,
            "genre": "Mbalax",
            "country": "Sénégal",
            "language": "Wolof",
            "port": 8766
        },
        "Radio Dakar": {
            "audio_dir": senegal_dir,
            "genre": "Afrobeat",
            "country": "Sénégal",
            "language": "Français",
            "port": 8767
        }
    })
    
    # Démarrer l'enregistrement des logs
    simulator.start_logging()
    
    # Démarrer toutes les stations
    simulator.start_all_stations()
    logger.info("Toutes les stations ont été démarrées")
    
    # Démarrer le monitoring
    simulator.start_monitoring(interval_seconds=10)
    
    try:
        # Attendre que les stations soient prêtes
        logger.info("Attente de 5 secondes pour que les stations soient prêtes...")
        await asyncio.sleep(5)
        
        # Lancer les détections en parallèle sur toutes les stations
        detection_tasks = []
        for station_name in simulator.stations.keys():
            task = asyncio.create_task(
                detect_music_on_station(
                    simulator=simulator,
                    station_name=station_name,
                    num_detections=2,
                    detection_duration=15
                )
            )
            detection_tasks.append(task)
        
        # Attendre que toutes les détections soient terminées
        await asyncio.gather(*detection_tasks)
        
        # Simuler une interruption sur une station
        logger.info("Simulation d'une interruption sur Radio Sénégal...")
        simulator.simulate_interruption("Radio Sénégal", duration_seconds=5)
        
        # Attendre un peu
        await asyncio.sleep(10)
        
        # Effectuer une détection après l'interruption
        logger.info("Détection après interruption sur Radio Sénégal...")
        await detect_music_on_station(
            simulator=simulator,
            station_name="Radio Sénégal",
            num_detections=1,
            detection_duration=15
        )
        
        # Sélectionner manuellement un morceau sur une station
        if simulator.stations["Radio Dakar"].playlist:
            logger.info("Sélection manuelle d'un morceau sur Radio Dakar...")
            simulator.select_track("Radio Dakar", 0)
            
            # Attendre un peu
            await asyncio.sleep(5)
            
            # Effectuer une détection après la sélection manuelle
            logger.info("Détection après sélection manuelle sur Radio Dakar...")
            await detect_music_on_station(
                simulator=simulator,
                station_name="Radio Dakar",
                num_detections=1,
                detection_duration=15
            )
        
        # Obtenir les logs de lecture
        play_logs = simulator.get_play_logs()
        logger.info(f"Logs de lecture: {len(play_logs)} événements")
        
        # Obtenir les logs de détection
        detection_logs = simulator.detection_logs
        logger.info(f"Logs de détection: {len(detection_logs)} événements")
        
        # Calculer la durée totale de lecture par station
        for station_name in simulator.stations.keys():
            total_play_duration = simulator.get_total_play_duration(station_name=station_name)
            logger.info(f"Durée totale de lecture pour {station_name}: {total_play_duration:.2f} secondes")
        
        # Exporter les logs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"multi_station_test_{timestamp}.json"
        simulator.export_logs(log_file, format="json")
        logger.info(f"Logs exportés dans {log_file}")
        
        # Afficher un résumé des détections
        logger.info("\nRésumé des détections:")
        logger.info(f"Nombre total de détections: {len(detection_logs)}")
        
        # Compter les détections par méthode
        methods_count = {}
        for log in detection_logs:
            method = log.get("detection_method", "unknown")
            methods_count[method] = methods_count.get(method, 0) + 1
        
        logger.info("Méthodes de détection utilisées:")
        for method, count in methods_count.items():
            logger.info(f"  - {method}: {count} détection(s)")
        
        # Compter les détections par station
        stations_count = {}
        for log in detection_logs:
            station = log.get("station_name", "unknown")
            stations_count[station] = stations_count.get(station, 0) + 1
        
        logger.info("Détections par station:")
        for station, count in stations_count.items():
            logger.info(f"  - {station}: {count} détection(s)")
        
        logger.info(f"Durée totale de lecture enregistrée: {sum(log.get('play_duration', 0) for log in detection_logs):.2f} secondes")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du test: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Arrêter le monitoring
        simulator.stop_monitoring()
        
        # Arrêter toutes les stations
        simulator.stop_all_stations()
        logger.info("Toutes les stations ont été arrêtées")
        
        # Arrêter l'enregistrement des logs
        simulator.stop_logging()
        
        logger.info("Test multi-stations terminé")


if __name__ == "__main__":
    # Exécuter le test
    asyncio.run(run_multi_station_test()) 