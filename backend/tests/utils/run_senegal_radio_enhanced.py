"""
Script pour exécuter le simulateur de radio amélioré avec les fichiers audio sénégalais.

Ce script permet de démarrer facilement une station de radio simulée diffusant
des fichiers audio sénégalais, avec toutes les fonctionnalités améliorées :
- Enregistrement précis des durées de lecture
- Logs détaillés
- Monitoring en temps réel
- Simulation d'interruptions
- Sélection manuelle de morceaux
"""

import logging
import os
import time
from pathlib import Path

from backend.tests.utils.enhanced_radio_simulator import EnhancedRadioSimulator

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_senegal_radio_enhanced")

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


def run_senegal_radio_enhanced():
    """
    Exécute le simulateur de radio amélioré avec les fichiers audio sénégalais.
    """
    # Vérifier si des fichiers audio sont disponibles
    if not AUDIO_DIR.exists() or not any(AUDIO_DIR.glob("*.mp3")):
        logger.error(f"Aucun fichier audio trouvé dans {AUDIO_DIR}")
        logger.info("Veuillez d'abord télécharger ou copier des fichiers audio dans ce répertoire.")
        return
    
    # Créer un simulateur de radio amélioré
    simulator = EnhancedRadioSimulator()
    
    # Créer une station avec les fichiers audio sénégalais
    station = simulator.create_station(
        name="Radio Sénégal",
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
    
    # Afficher les informations sur la station
    logger.info(f"Station démarrée: {station.name}")
    logger.info(f"URL de streaming: http://localhost:{station.port}")
    logger.info(f"Nombre de morceaux dans la playlist: {len(station.playlist)}")
    
    # Afficher la liste des morceaux
    logger.info("Playlist:")
    for i, track in enumerate(station.playlist):
        logger.info(f"  {i+1}. {track.name}")
    
    # Démarrer le monitoring
    simulator.start_monitoring(interval_seconds=5)
    
    # Afficher le menu des commandes
    logger.info("\nCommandes disponibles:")
    logger.info("  i - Simuler une interruption")
    logger.info("  s <index> - Sélectionner un morceau (ex: s 1)")
    logger.info("  e - Exporter les logs")
    logger.info("  q - Quitter")
    
    try:
        # Boucle principale
        while True:
            command = input("\nEntrez une commande (i/s/e/q): ").strip().lower()
            
            if command == "q":
                logger.info("Arrêt demandé par l'utilisateur")
                break
            
            elif command == "i":
                duration = 5
                try:
                    duration_input = input("Durée de l'interruption en secondes (défaut: 5): ").strip()
                    if duration_input:
                        duration = int(duration_input)
                except ValueError:
                    logger.warning("Durée invalide, utilisation de la valeur par défaut (5s)")
                
                simulator.simulate_interruption(station.name, duration_seconds=duration)
            
            elif command.startswith("s "):
                try:
                    index = int(command.split()[1]) - 1  # Convertir en index 0-based
                    if 0 <= index < len(station.playlist):
                        simulator.select_track(station.name, index)
                    else:
                        logger.warning(f"Index invalide. Utilisez un nombre entre 1 et {len(station.playlist)}")
                except (ValueError, IndexError):
                    logger.warning("Format invalide. Utilisez 's <index>' (ex: 's 1')")
            
            elif command == "e":
                filename = f"radio_logs_{time.strftime('%Y%m%d_%H%M%S')}.json"
                simulator.export_logs(filename, format="json")
                logger.info(f"Logs exportés dans {filename}")
            
            else:
                logger.warning("Commande non reconnue")
    
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur (Ctrl+C)")
    finally:
        # Arrêter le monitoring
        simulator.stop_monitoring()
        
        # Arrêter la station
        station.stop()
        logger.info("Station arrêtée")
        
        # Exporter les logs avant de quitter
        filename = f"radio_logs_{time.strftime('%Y%m%d_%H%M%S')}.json"
        simulator.export_logs(filename, format="json")
        logger.info(f"Logs exportés dans {filename}")
        
        # Arrêter l'enregistrement des logs
        simulator.stop_logging()


if __name__ == "__main__":
    run_senegal_radio_enhanced() 