"""
Script simplifié pour diffuser les fichiers audio sénégalais via le simulateur radio.

Ce script crée une station de radio simulée qui diffuse les fichiers audio sénégalais
et affiche les informations sur les morceaux en cours de lecture.
"""

import logging
import os
import time
from pathlib import Path

from backend.tests.utils.radio_simulator import RadioSimulator

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("senegal_radio_simulator")

# Répertoire des fichiers audio
AUDIO_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "audio" / "senegal"

# Chemin vers fpcalc.exe pour la génération d'empreintes acoustiques
FPCALC_PATH = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "bin" / "fpcalc.exe"

# Vérifier si fpcalc.exe existe
if FPCALC_PATH.exists():
    logger.info(f"fpcalc.exe trouvé à {FPCALC_PATH}")
    # Définir la variable d'environnement pour que le système puisse trouver fpcalc
    os.environ["FPCALC_PATH"] = str(FPCALC_PATH)
else:
    logger.warning(f"fpcalc.exe non trouvé à {FPCALC_PATH}. La génération d'empreintes acoustiques pourrait échouer.")


def track_change_callback(station_name, track_path, start_time):
    """
    Callback appelé lorsqu'un morceau change sur la station.
    
    Args:
        station_name: Nom de la station
        track_path: Chemin du fichier audio
        start_time: Timestamp de début de lecture
    """
    logger.info(f"[{station_name}] Nouveau morceau: {track_path.name}")
    logger.info(f"[{station_name}] Début de lecture: {time.strftime('%H:%M:%S', time.localtime(start_time))}")


def run_senegal_radio():
    """
    Crée et démarre une station de radio simulée diffusant des fichiers audio sénégalais.
    """
    # Vérifier si des fichiers audio sont disponibles
    if not AUDIO_DIR.exists() or not any(AUDIO_DIR.glob("*.mp3")):
        logger.error(f"Aucun fichier audio trouvé dans {AUDIO_DIR}")
        logger.info("Veuillez d'abord télécharger ou copier des fichiers audio dans ce répertoire.")
        return
    
    # Créer un simulateur radio
    simulator = RadioSimulator()
    
    # Créer une station avec les fichiers audio sénégalais
    station = simulator.create_station(name="Radio Sénégal", audio_dir=AUDIO_DIR)
    
    if not station or not station.playlist:
        logger.error("Impossible de créer la station simulée")
        return
    
    # Ajouter un callback pour être notifié des changements de morceaux
    station.add_track_change_callback(track_change_callback)
    
    # Démarrer la station
    station.start()
    
    # Afficher les informations sur la station
    logger.info(f"Station démarrée: {station.name}")
    logger.info(f"URL de streaming: http://localhost:{station.port}")
    logger.info(f"Nombre de morceaux dans la playlist: {len(station.playlist)}")
    
    # Afficher la liste des morceaux
    logger.info("Playlist:")
    for i, track in enumerate(station.playlist):
        logger.info(f"  {i+1}. {track.name}")
    
    try:
        # Afficher les informations sur le morceau en cours toutes les 5 secondes
        logger.info("Appuyez sur Ctrl+C pour arrêter la diffusion")
        
        while True:
            # Obtenir les informations sur le morceau en cours
            track_info = station.get_current_track_info()
            
            if track_info["status"] == "playing":
                logger.info(
                    f"En cours: {track_info['track']} - "
                    f"Écoulé: {track_info['elapsed']:.1f}s - "
                    f"Restant: {track_info['remaining']:.1f}s"
                )
            
            # Attendre 5 secondes
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
    finally:
        # Arrêter la station
        station.stop()
        logger.info("Station arrêtée")


if __name__ == "__main__":
    run_senegal_radio() 