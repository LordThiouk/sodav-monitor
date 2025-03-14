"""
Simulateur de radio amélioré pour les tests de détection musicale.

Ce module étend le simulateur de radio existant avec des fonctionnalités supplémentaires
pour tester la détection musicale en conditions réelles, notamment :
- Diffusion de flux audio en continu
- Simulation réaliste de stations de radio
- Enregistrement précis de la durée de lecture
- Logs détaillés pour analyse
- Simulation d'interruptions et de conditions réelles
"""

import csv
import json
import logging
import os
import random
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Callable

from backend.tests.utils.radio_simulator import RadioSimulator, RadioStation

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enhanced_radio_simulator")

# Chemin vers fpcalc.exe pour la génération d'empreintes acoustiques
FPCALC_PATH = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "bin" / "fpcalc.exe"

# Configurer fpcalc.exe si disponible
if FPCALC_PATH.exists():
    logger.info(f"fpcalc.exe trouvé à {FPCALC_PATH}")
    os.environ["FPCALC_PATH"] = str(FPCALC_PATH)
else:
    logger.warning(f"fpcalc.exe non trouvé à {FPCALC_PATH}. La génération d'empreintes acoustiques pourrait échouer.")


class EnhancedRadioSimulator(RadioSimulator):
    """
    Version améliorée du simulateur de radio avec des fonctionnalités supplémentaires
    pour les tests de détection musicale.
    """

    def __init__(self):
        """Initialise le simulateur de radio amélioré."""
        super().__init__()
        self.stations = {}  # Dictionnaire des stations par ID
        self.play_logs = []  # Logs de lecture
        self.detection_logs = []  # Logs de détection
        self.log_file = None  # Fichier de log CSV
        self.log_writer = None  # Writer CSV pour les logs
        self.monitoring_thread = None  # Thread de monitoring
        self.monitoring_active = False  # État du monitoring

    def create_station(self, name: str, audio_dir: Union[str, Path], 
                       genre: str = None, country: str = None, 
                       language: str = None, port: int = None) -> Optional[RadioStation]:
        """
        Crée une station de radio virtuelle.
        
        Args:
            name: Nom de la station
            audio_dir: Répertoire contenant les fichiers audio
            genre: Genre musical de la station
            country: Pays d'origine de la station
            language: Langue principale de la station
            port: Port pour le streaming (optionnel)
            
        Returns:
            Instance de RadioStation ou None en cas d'échec
        """
        station = super().create_station(name=name, audio_dir=audio_dir)
        
        if station and port is not None:
            station.port = port
        
        if station:
            # Ajouter des métadonnées supplémentaires à la station
            station.genre = genre
            station.country = country
            station.language = language
            station.start_time = None
            station.current_track_start_time = None
            station.interruption_active = False
            
            # Ajouter un callback pour suivre les changements de morceaux
            station.add_track_change_callback(self._track_change_callback)
            
            # Stocker la station dans le dictionnaire
            self.stations[station.name] = station
            
            logger.info(f"Station créée: {name} ({genre or 'Genre non spécifié'}, {country or 'Pays non spécifié'})")
        
        return station

    def start_all_stations(self):
        """Démarre toutes les stations enregistrées."""
        for station in self.stations.values():
            if not station.is_running:
                station.start()
                logger.info(f"Station démarrée: {station.name} sur http://localhost:{station.port}")

    def stop_all_stations(self):
        """Arrête toutes les stations enregistrées."""
        for station in self.stations.values():
            if station.is_running:
                station.stop()
                logger.info(f"Station arrêtée: {station.name}")

    def simulate_interruption(self, station_name: str, duration_seconds: int = 10):
        """
        Simule une interruption de flux sur une station.
        
        Args:
            station_name: Nom de la station
            duration_seconds: Durée de l'interruption en secondes
        """
        station = self.stations.get(station_name)
        if not station:
            logger.error(f"Station non trouvée: {station_name}")
            return
        
        if station.is_running:
            logger.info(f"Simulation d'une interruption sur {station_name} pendant {duration_seconds}s")
            
            # Marquer l'interruption comme active
            station.interruption_active = True
            
            # Enregistrer l'événement dans les logs
            self._log_event(
                station_name=station_name,
                event_type="interruption_start",
                track_name="N/A",
                timestamp=datetime.now(),
                duration=0,
                details={"duration_seconds": duration_seconds}
            )
            
            # Arrêter temporairement la station
            station.stop()
            
            # Attendre la durée spécifiée
            time.sleep(duration_seconds)
            
            # Redémarrer la station
            station.start()
            station.interruption_active = False
            
            # Enregistrer la fin de l'interruption
            self._log_event(
                station_name=station_name,
                event_type="interruption_end",
                track_name="N/A",
                timestamp=datetime.now(),
                duration=duration_seconds,
                details={}
            )
            
            logger.info(f"Fin de l'interruption sur {station_name}")

    def select_track(self, station_name: str, track_index: int):
        """
        Sélectionne manuellement un morceau à jouer sur une station.
        
        Args:
            station_name: Nom de la station
            track_index: Index du morceau dans la playlist (0-based)
        """
        station = self.stations.get(station_name)
        if not station:
            logger.error(f"Station non trouvée: {station_name}")
            return
        
        if not station.playlist or track_index >= len(station.playlist):
            logger.error(f"Index de morceau invalide: {track_index}")
            return
        
        # Arrêter la lecture en cours
        was_running = station.is_running
        if was_running:
            station.stop()
        
        # Définir le morceau actuel
        station.current_track_index = track_index
        
        # Redémarrer la station si elle était en cours d'exécution
        if was_running:
            station.start()
        
        logger.info(f"Morceau sélectionné sur {station_name}: {station.playlist[track_index].name}")

    def start_logging(self, log_file: str = None):
        """
        Démarre l'enregistrement des logs dans un fichier CSV.
        
        Args:
            log_file: Chemin du fichier de log (optionnel)
        """
        if not log_file:
            log_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent / "logs"
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"radio_simulator_{timestamp}.csv"
        
        self.log_file = open(log_file, "w", newline="", encoding="utf-8")
        self.log_writer = csv.writer(self.log_file)
        
        # Écrire l'en-tête du fichier CSV
        self.log_writer.writerow([
            "Timestamp", "Station", "Event", "Track", "Duration", "Details"
        ])
        
        logger.info(f"Enregistrement des logs démarré dans {log_file}")

    def stop_logging(self):
        """Arrête l'enregistrement des logs."""
        if self.log_file:
            self.log_file.close()
            self.log_file = None
            self.log_writer = None
            logger.info("Enregistrement des logs arrêté")

    def start_monitoring(self, interval_seconds: int = 5):
        """
        Démarre le monitoring des stations en temps réel.
        
        Args:
            interval_seconds: Intervalle entre les vérifications en secondes
        """
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Le monitoring est déjà actif")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info(f"Monitoring démarré (intervalle: {interval_seconds}s)")

    def stop_monitoring(self):
        """Arrête le monitoring des stations."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_active = False
            self.monitoring_thread.join(timeout=2)
            logger.info("Monitoring arrêté")

    def get_play_logs(self, station_name: str = None, start_time: datetime = None, 
                     end_time: datetime = None) -> List[Dict]:
        """
        Récupère les logs de lecture filtrés.
        
        Args:
            station_name: Filtrer par nom de station (optionnel)
            start_time: Filtrer par heure de début (optionnel)
            end_time: Filtrer par heure de fin (optionnel)
            
        Returns:
            Liste des logs de lecture filtrés
        """
        filtered_logs = self.play_logs
        
        if station_name:
            filtered_logs = [log for log in filtered_logs if log["station_name"] == station_name]
        
        if start_time:
            filtered_logs = [log for log in filtered_logs if log["timestamp"] >= start_time]
        
        if end_time:
            filtered_logs = [log for log in filtered_logs if log["timestamp"] <= end_time]
        
        return filtered_logs

    def get_total_play_duration(self, station_name: str = None, track_name: str = None) -> float:
        """
        Calcule la durée totale de lecture pour une station ou un morceau.
        
        Args:
            station_name: Filtrer par nom de station (optionnel)
            track_name: Filtrer par nom de morceau (optionnel)
            
        Returns:
            Durée totale de lecture en secondes
        """
        filtered_logs = [
            log for log in self.play_logs 
            if log["event_type"] == "track_end"
            and (not station_name or log["station_name"] == station_name)
            and (not track_name or log["track_name"] == track_name)
        ]
        
        total_duration = sum(log["duration"] for log in filtered_logs)
        return total_duration

    def register_detection(self, station_name: str, track_name: str, 
                          detection_method: str, confidence: float,
                          detected_at: datetime, play_duration: float,
                          fingerprint: str = None, metadata: Dict = None):
        """
        Enregistre une détection de morceau.
        
        Args:
            station_name: Nom de la station
            track_name: Nom du morceau détecté
            detection_method: Méthode de détection utilisée
            confidence: Score de confiance de la détection
            detected_at: Timestamp de la détection
            play_duration: Durée de lecture en secondes
            fingerprint: Empreinte acoustique (optionnel)
            metadata: Métadonnées supplémentaires (optionnel)
        """
        detection = {
            "station_name": station_name,
            "track_name": track_name,
            "detection_method": detection_method,
            "confidence": confidence,
            "detected_at": detected_at,
            "play_duration": play_duration,
            "fingerprint": fingerprint,
            "metadata": metadata or {}
        }
        
        self.detection_logs.append(detection)
        
        # Enregistrer dans le fichier de log
        self._log_event(
            station_name=station_name,
            event_type="detection",
            track_name=track_name,
            timestamp=detected_at,
            duration=play_duration,
            details={
                "method": detection_method,
                "confidence": confidence,
                "fingerprint": fingerprint[:20] + "..." if fingerprint else None
            }
        )
        
        logger.info(
            f"Détection enregistrée: {track_name} sur {station_name} "
            f"(méthode: {detection_method}, confiance: {confidence:.2f}, "
            f"durée: {play_duration:.2f}s)"
        )

    def export_logs(self, output_file: str, format: str = "csv"):
        """
        Exporte les logs dans un fichier.
        
        Args:
            output_file: Chemin du fichier de sortie
            format: Format d'export ('csv' ou 'json')
        """
        if format.lower() == "csv":
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                
                # En-tête pour les logs de lecture
                writer.writerow([
                    "Type", "Timestamp", "Station", "Event", "Track", 
                    "Duration", "Details"
                ])
                
                # Écrire les logs de lecture
                for log in self.play_logs:
                    writer.writerow([
                        "play",
                        log["timestamp"].isoformat(),
                        log["station_name"],
                        log["event_type"],
                        log["track_name"],
                        log["duration"],
                        json.dumps(log["details"])
                    ])
                
                # Écrire les logs de détection
                for log in self.detection_logs:
                    writer.writerow([
                        "detection",
                        log["detected_at"].isoformat(),
                        log["station_name"],
                        "detection",
                        log["track_name"],
                        log["play_duration"],
                        json.dumps({
                            "method": log["detection_method"],
                            "confidence": log["confidence"]
                        })
                    ])
        
        elif format.lower() == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump({
                    "play_logs": [
                        {**log, "timestamp": log["timestamp"].isoformat()}
                        for log in self.play_logs
                    ],
                    "detection_logs": [
                        {**log, "detected_at": log["detected_at"].isoformat()}
                        for log in self.detection_logs
                    ]
                }, f, indent=2)
        
        else:
            logger.error(f"Format d'export non pris en charge: {format}")
            return
        
        logger.info(f"Logs exportés dans {output_file} (format: {format})")

    def _track_change_callback(self, station_name: str, track_path: Path, start_time: float):
        """
        Callback appelé lorsqu'un morceau change sur une station.
        
        Args:
            station_name: Nom de la station
            track_path: Chemin du fichier audio
            start_time: Timestamp de début de lecture
        """
        station = self.stations.get(station_name)
        if not station:
            return
        
        # Si un morceau était en cours de lecture, enregistrer sa fin
        if station.current_track_start_time is not None:
            end_time = datetime.fromtimestamp(start_time)
            start_time_dt = datetime.fromtimestamp(station.current_track_start_time)
            duration = (end_time - start_time_dt).total_seconds()
            
            # Enregistrer la fin du morceau précédent
            self._log_event(
                station_name=station_name,
                event_type="track_end",
                track_name=station.current_track.name if hasattr(station, "current_track") else "Unknown",
                timestamp=end_time,
                duration=duration,
                details={}
            )
        
        # Enregistrer le début du nouveau morceau
        station.current_track = track_path
        station.current_track_start_time = start_time
        
        # Enregistrer l'événement dans les logs
        self._log_event(
            station_name=station_name,
            event_type="track_start",
            track_name=track_path.name,
            timestamp=datetime.fromtimestamp(start_time),
            duration=0,
            details={}
        )
        
        logger.info(f"[{station_name}] Nouveau morceau: {track_path.name}")
        logger.info(f"[{station_name}] Début de lecture: {time.strftime('%H:%M:%S', time.localtime(start_time))}")

    def _log_event(self, station_name: str, event_type: str, track_name: str, 
                  timestamp: datetime, duration: float, details: Dict):
        """
        Enregistre un événement dans les logs.
        
        Args:
            station_name: Nom de la station
            event_type: Type d'événement
            track_name: Nom du morceau
            timestamp: Timestamp de l'événement
            duration: Durée en secondes
            details: Détails supplémentaires
        """
        # Ajouter aux logs en mémoire
        log_entry = {
            "station_name": station_name,
            "event_type": event_type,
            "track_name": track_name,
            "timestamp": timestamp,
            "duration": duration,
            "details": details
        }
        
        self.play_logs.append(log_entry)
        
        # Écrire dans le fichier CSV si activé
        if self.log_writer:
            self.log_writer.writerow([
                timestamp.isoformat(),
                station_name,
                event_type,
                track_name,
                duration,
                json.dumps(details)
            ])

    def _monitoring_loop(self, interval_seconds: int):
        """
        Boucle de monitoring des stations.
        
        Args:
            interval_seconds: Intervalle entre les vérifications en secondes
        """
        while self.monitoring_active:
            # Afficher l'état de chaque station
            for station_name, station in self.stations.items():
                if station.is_running:
                    track_info = station.get_current_track_info()
                    
                    if track_info["status"] == "playing":
                        logger.info(
                            f"[{station_name}] En cours: {track_info['track']} - "
                            f"Écoulé: {track_info['elapsed']:.1f}s - "
                            f"Restant: {track_info['remaining']:.1f}s"
                        )
                    else:
                        logger.info(f"[{station_name}] Aucun morceau en cours de lecture")
                else:
                    logger.info(f"[{station_name}] Station arrêtée")
            
            # Attendre l'intervalle spécifié
            time.sleep(interval_seconds)


# Fonction utilitaire pour créer un simulateur avec plusieurs stations
def create_multi_station_simulator(audio_dirs: Dict[str, Dict]) -> EnhancedRadioSimulator:
    """
    Crée un simulateur avec plusieurs stations configurées.
    
    Args:
        audio_dirs: Dictionnaire avec les configurations des stations
                   {nom_station: {audio_dir: chemin, genre: genre, country: pays, language: langue}}
    
    Returns:
        Instance de EnhancedRadioSimulator configurée
    """
    simulator = EnhancedRadioSimulator()
    
    for station_name, config in audio_dirs.items():
        audio_dir = config.get("audio_dir")
        if not audio_dir:
            logger.error(f"Répertoire audio non spécifié pour la station {station_name}")
            continue
        
        simulator.create_station(
            name=station_name,
            audio_dir=audio_dir,
            genre=config.get("genre"),
            country=config.get("country"),
            language=config.get("language"),
            port=config.get("port")
        )
    
    return simulator


# Exemple d'utilisation
if __name__ == "__main__":
    # Répertoire des fichiers audio
    AUDIO_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "audio"
    
    # Créer un simulateur avec plusieurs stations
    simulator = create_multi_station_simulator({
        "Radio Sénégal": {
            "audio_dir": AUDIO_DIR / "senegal",
            "genre": "Hip-Hop/Rap",
            "country": "Sénégal",
            "language": "Wolof/Français"
        },
        "Radio Jazz": {
            "audio_dir": AUDIO_DIR / "jazz",
            "genre": "Jazz",
            "country": "International",
            "language": "Instrumental"
        }
    })
    
    # Démarrer l'enregistrement des logs
    simulator.start_logging()
    
    # Démarrer toutes les stations
    simulator.start_all_stations()
    
    # Démarrer le monitoring
    simulator.start_monitoring(interval_seconds=10)
    
    try:
        # Laisser les stations diffuser pendant un certain temps
        time.sleep(30)
        
        # Simuler une interruption sur une station
        simulator.simulate_interruption("Radio Sénégal", duration_seconds=5)
        
        # Laisser les stations diffuser encore un peu
        time.sleep(30)
        
        # Sélectionner manuellement un morceau sur une station
        stations = list(simulator.stations.values())
        if stations and stations[0].playlist:
            simulator.select_track(stations[0].name, 0)
        
        # Laisser les stations diffuser encore un peu
        time.sleep(30)
        
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
    finally:
        # Arrêter le monitoring
        simulator.stop_monitoring()
        
        # Arrêter toutes les stations
        simulator.stop_all_stations()
        
        # Exporter les logs
        simulator.export_logs("radio_simulator_logs.json", format="json")
        
        # Arrêter l'enregistrement des logs
        simulator.stop_logging()
        
        logger.info("Simulateur arrêté") 