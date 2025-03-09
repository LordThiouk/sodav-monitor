#!/usr/bin/env python
"""
Script pour la surveillance continue des stations radio.
Ce script permet de surveiller en continu plusieurs stations radio et de détecter les morceaux joués.
"""

import os
import sys
import asyncio
import argparse
import json
import time
import signal
from datetime import datetime
from pathlib import Path
import logging
import aiohttp
import tempfile
from typing import List, Dict, Any, Optional, Set

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from backend.detection.audio_processor.track_manager import TrackManager
from backend.models.database import get_db
from backend.utils.logging_config import setup_logging, log_with_category

# Configurer le logging
logger = setup_logging(__name__)

# Variable globale pour indiquer si le script doit s'arrêter
should_stop = False

class StationMonitor:
    """Classe pour surveiller une station radio."""
    
    def __init__(
        self, 
        station_id: int, 
        station_name: str, 
        stream_url: str,
        track_manager: TrackManager,
        sample_duration: int = 20,
        interval: int = 30,
        output_dir: Optional[str] = None
    ):
        """
        Initialiser le moniteur de station.
        
        Args:
            station_id: ID de la station
            station_name: Nom de la station
            stream_url: URL du flux audio de la station
            track_manager: Gestionnaire de pistes
            sample_duration: Durée de l'échantillon audio en secondes
            interval: Intervalle entre les échantillons en secondes
            output_dir: Répertoire de sortie pour les échantillons audio
        """
        self.station_id = station_id
        self.station_name = station_name
        self.stream_url = stream_url
        self.track_manager = track_manager
        self.sample_duration = sample_duration
        self.interval = interval
        self.output_dir = output_dir
        
        # Créer le répertoire de sortie si nécessaire
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        # Statistiques
        self.stats = {
            "samples_processed": 0,
            "detections_success": 0,
            "detections_failed": 0,
            "last_detection": None,
            "detected_tracks": set(),
            "start_time": datetime.now().isoformat()
        }
    
    async def capture_audio_sample(self) -> Optional[bytes]:
        """
        Capturer un échantillon audio du flux de la station.
        
        Returns:
            Données audio en bytes ou None en cas d'erreur
        """
        try:
            log_with_category(logger, "MONITOR", "info", 
                f"Capturing audio sample from {self.station_name} ({self.stream_url})")
            
            # Créer une session HTTP
            async with aiohttp.ClientSession() as session:
                # Ouvrir le flux audio
                async with session.get(self.stream_url, timeout=10) as response:
                    if response.status != 200:
                        log_with_category(logger, "MONITOR", "error", 
                            f"Error accessing stream {self.stream_url}: HTTP {response.status}")
                        return None
                    
                    # Lire les données audio pendant la durée spécifiée
                    start_time = time.time()
                    audio_data = bytearray()
                    
                    while time.time() - start_time < self.sample_duration:
                        # Vérifier si le script doit s'arrêter
                        if should_stop:
                            break
                            
                        # Lire un morceau de données
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        
                        audio_data.extend(chunk)
                    
                    # Vérifier si suffisamment de données ont été lues
                    if len(audio_data) < 8192:
                        log_with_category(logger, "MONITOR", "warning", 
                            f"Not enough audio data captured from {self.station_name}: {len(audio_data)} bytes")
                        return None
                    
                    log_with_category(logger, "MONITOR", "info", 
                        f"Captured {len(audio_data)} bytes from {self.station_name}")
                    
                    # Sauvegarder l'échantillon si demandé
                    if self.output_dir:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{self.station_name.replace(' ', '_')}_{timestamp}.mp3"
                        filepath = os.path.join(self.output_dir, filename)
                        
                        with open(filepath, "wb") as f:
                            f.write(audio_data)
                        
                        log_with_category(logger, "MONITOR", "info", 
                            f"Saved audio sample to {filepath}")
                    
                    return bytes(audio_data)
        
        except aiohttp.ClientError as e:
            log_with_category(logger, "MONITOR", "error", 
                f"Error capturing audio from {self.station_name}: {str(e)}")
            return None
        except asyncio.TimeoutError:
            log_with_category(logger, "MONITOR", "error", 
                f"Timeout capturing audio from {self.station_name}")
            return None
        except Exception as e:
            log_with_category(logger, "MONITOR", "error", 
                f"Unexpected error capturing audio from {self.station_name}: {str(e)}")
            import traceback
            log_with_category(logger, "MONITOR", "error", traceback.format_exc())
            return None
    
    async def process_audio_sample(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Traiter un échantillon audio et détecter les morceaux.
        
        Args:
            audio_data: Données audio en bytes
            
        Returns:
            Résultat de la détection
        """
        try:
            # Créer les données de station
            station_data = {
                "raw_audio": audio_data,
                "station_id": self.station_id,
                "station_name": self.station_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Traiter les données de station
            log_with_category(logger, "MONITOR", "info", 
                f"Processing audio sample from {self.station_name}")
            
            # Mesurer le temps de traitement
            start_time = time.time()
            result = await self.track_manager.process_station_data(station_data)
            processing_time = time.time() - start_time
            
            # Ajouter des informations supplémentaires au résultat
            result["processing_time"] = processing_time
            result["sample_size"] = len(audio_data)
            
            # Mettre à jour les statistiques
            self.stats["samples_processed"] += 1
            
            if result.get("success", False):
                self.stats["detections_success"] += 1
                self.stats["last_detection"] = datetime.now().isoformat()
                
                # Ajouter le morceau détecté à l'ensemble des morceaux détectés
                if "detection" in result:
                    track_id = result["detection"].get("id")
                    if track_id:
                        self.stats["detected_tracks"].add(track_id)
            else:
                self.stats["detections_failed"] += 1
            
            return result
        
        except Exception as e:
            log_with_category(logger, "MONITOR", "error", 
                f"Error processing audio from {self.station_name}: {str(e)}")
            import traceback
            log_with_category(logger, "MONITOR", "error", traceback.format_exc())
            
            return {
                "success": False,
                "error": str(e),
                "station_id": self.station_id,
                "station_name": self.station_name
            }
    
    async def monitor_loop(self):
        """
        Boucle principale de surveillance de la station.
        """
        log_with_category(logger, "MONITOR", "info", 
            f"Starting monitoring loop for {self.station_name} (interval: {self.interval}s)")
        
        while not should_stop:
            try:
                # Capturer un échantillon audio
                audio_data = await self.capture_audio_sample()
                
                if audio_data:
                    # Traiter l'échantillon audio
                    result = await self.process_audio_sample(audio_data)
                    
                    # Afficher le résultat
                    if result.get("success", False):
                        detection = result.get("detection", {})
                        log_with_category(logger, "MONITOR", "info", 
                            f"Detection successful for {self.station_name}: "
                            f"{detection.get('title', 'Unknown')} by {detection.get('artist', 'Unknown')}")
                    else:
                        log_with_category(logger, "MONITOR", "info", 
                            f"No detection for {self.station_name}: {result.get('error', 'Unknown error')}")
                
                # Attendre l'intervalle spécifié
                if not should_stop:
                    log_with_category(logger, "MONITOR", "info", 
                        f"Waiting {self.interval}s before next sample for {self.station_name}")
                    await asyncio.sleep(self.interval)
            
            except Exception as e:
                log_with_category(logger, "MONITOR", "error", 
                    f"Error in monitoring loop for {self.station_name}: {str(e)}")
                import traceback
                log_with_category(logger, "MONITOR", "error", traceback.format_exc())
                
                # Attendre avant de réessayer
                if not should_stop:
                    await asyncio.sleep(5)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtenir les statistiques de surveillance.
        
        Returns:
            Statistiques de surveillance
        """
        # Convertir l'ensemble des morceaux détectés en liste pour la sérialisation JSON
        stats = self.stats.copy()
        stats["detected_tracks"] = list(stats["detected_tracks"])
        stats["duration"] = (datetime.now() - datetime.fromisoformat(stats["start_time"])).total_seconds()
        
        return stats

async def monitor_stations(
    stations_config: List[Dict[str, Any]],
    output_dir: Optional[str] = None,
    sample_duration: int = 20,
    interval: int = 30
) -> None:
    """
    Surveiller plusieurs stations radio en parallèle.
    
    Args:
        stations_config: Liste des configurations de stations
        output_dir: Répertoire de sortie pour les échantillons audio
        sample_duration: Durée de l'échantillon audio en secondes
        interval: Intervalle entre les échantillons en secondes
    """
    print(f"=== Surveillance de {len(stations_config)} stations ===")
    
    # Créer une session de base de données
    db_session = next(get_db())
    
    try:
        # Initialiser le gestionnaire de pistes
        track_manager = TrackManager(db_session)
        
        # Créer les moniteurs de stations
        monitors = []
        for config in stations_config:
            station_id = config.get("id")
            station_name = config.get("name")
            stream_url = config.get("url")
            
            if not station_id or not station_name or not stream_url:
                print(f"❌ Configuration de station invalide : {config}")
                continue
            
            # Créer le moniteur de station
            monitor = StationMonitor(
                station_id=station_id,
                station_name=station_name,
                stream_url=stream_url,
                track_manager=track_manager,
                sample_duration=sample_duration,
                interval=interval,
                output_dir=output_dir
            )
            
            monitors.append(monitor)
        
        # Démarrer les boucles de surveillance
        tasks = [monitor.monitor_loop() for monitor in monitors]
        
        # Attendre que toutes les tâches soient terminées
        await asyncio.gather(*tasks)
        
        # Afficher les statistiques finales
        print("\n=== Statistiques finales ===")
        for monitor in monitors:
            stats = monitor.get_stats()
            print(f"Station: {monitor.station_name}")
            print(f"  Échantillons traités: {stats['samples_processed']}")
            print(f"  Détections réussies: {stats['detections_success']}")
            print(f"  Détections échouées: {stats['detections_failed']}")
            print(f"  Morceaux uniques détectés: {len(stats['detected_tracks'])}")
            print(f"  Durée de surveillance: {stats['duration']:.2f} secondes")
            print()
    
    finally:
        # Fermer la session de base de données
        db_session.close()

def signal_handler(sig, frame):
    """
    Gestionnaire de signal pour arrêter proprement le script.
    """
    global should_stop
    print("\nArrêt en cours, veuillez patienter...")
    should_stop = True

def main():
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Surveiller en continu plusieurs stations radio")
    parser.add_argument("config", help="Fichier de configuration des stations (JSON)")
    parser.add_argument("--output-dir", help="Répertoire de sortie pour les échantillons audio")
    parser.add_argument("--sample-duration", type=int, default=20, help="Durée de l'échantillon audio en secondes")
    parser.add_argument("--interval", type=int, default=30, help="Intervalle entre les échantillons en secondes")
    args = parser.parse_args()
    
    # Charger la configuration des stations
    try:
        with open(args.config, "r") as f:
            stations_config = json.load(f)
        
        print(f"Configuration chargée depuis {args.config} : {len(stations_config)} stations")
    except Exception as e:
        print(f"❌ Erreur lors du chargement de la configuration : {str(e)}")
        return
    
    # Configurer le gestionnaire de signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Démarrer la surveillance
    try:
        asyncio.run(monitor_stations(
            stations_config=stations_config,
            output_dir=args.output_dir,
            sample_duration=args.sample_duration,
            interval=args.interval
        ))
    except KeyboardInterrupt:
        print("\nSurveillance interrompue par l'utilisateur")

if __name__ == "__main__":
    main() 