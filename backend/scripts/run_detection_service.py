#!/usr/bin/env python3
"""
Script pour exécuter le service de détection musicale en tant que processus séparé.
Ce script s'exécute indépendamment du serveur web et gère la détection musicale
pour toutes les stations actives de manière contrôlée.

Usage:
    python run_detection_service.py [--max_concurrent 5] [--interval 60]
"""

import os
import sys
import asyncio
import argparse
import logging
import signal
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Importer les modules nécessaires
from backend.logs.log_manager import LogManager
from backend.models.database import init_db, get_db, SessionLocal
from backend.models.models import RadioStation, StationStatus
from backend.routers.channels.monitoring import detect_station_music
from backend.core.config import get_settings
from backend.utils.radio import fetch_and_save_senegal_stations
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Initialiser le logging
log_manager = LogManager()
logger = log_manager.get_logger("detection_service")

# Variable pour contrôler l'arrêt du service
running = True

def signal_handler(sig, frame):
    """Gestionnaire de signal pour arrêter proprement le service."""
    global running
    logger.info("Signal d'arrêt reçu, arrêt du service de détection...")
    running = False

class DetectionService:
    """Service de détection musicale."""
    
    def __init__(self, max_concurrent: int = 5, interval: int = 60):
        """
        Initialise le service de détection.
        
        Args:
            max_concurrent: Nombre maximum de stations à traiter simultanément
            interval: Intervalle en secondes entre les cycles de détection
        """
        self.max_concurrent = max_concurrent
        self.interval = interval
        self.db_session = SessionLocal()
        self.settings = get_settings()
        
        # Vérifier les clés API requises
        if not self.settings.ACOUSTID_API_KEY:
            logger.warning("ACOUSTID_API_KEY is not set. MusicBrainz recognition will be disabled.")
        if not self.settings.AUDD_API_KEY:
            logger.warning("AUDD_API_KEY is not set. AudD recognition will be disabled.")
    
    async def get_active_stations(self) -> List[RadioStation]:
        """Récupère toutes les stations actives."""
        try:
            active_stations = self.db_session.query(RadioStation).filter(
                RadioStation.status == StationStatus.ACTIVE
            ).all()
            return active_stations
        except Exception as e:
            logger.error(f"Error getting active stations: {str(e)}")
            return []
    
    async def process_station_group(self, stations: List[RadioStation]):
        """
        Traite un groupe de stations en parallèle.
        
        Args:
            stations: Liste des stations à traiter
        """
        tasks = []
        for station in stations:
            logger.info(f"Starting detection for station: {station.name} (ID: {station.id})")
            task = asyncio.create_task(detect_station_music(station.id))
            tasks.append(task)
        
        # Attendre que toutes les tâches soient terminées
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def run_detection_cycle(self):
        """Exécute un cycle complet de détection pour toutes les stations actives."""
        try:
            # Récupérer les stations actives
            active_stations = await self.get_active_stations()
            
            if not active_stations:
                logger.warning("No active stations found for music detection")
                return
            
            logger.info(f"Starting detection cycle for {len(active_stations)} active stations")
            
            # Diviser les stations en groupes
            station_groups = [active_stations[i:i+self.max_concurrent] 
                             for i in range(0, len(active_stations), self.max_concurrent)]
            
            # Traiter chaque groupe séquentiellement
            for group_index, station_group in enumerate(station_groups):
                logger.info(f"Processing station group {group_index+1}/{len(station_groups)} ({len(station_group)} stations)")
                await self.process_station_group(station_group)
                
                # Attendre un court délai entre les groupes
                if group_index < len(station_groups) - 1:
                    await asyncio.sleep(2)
            
            logger.info(f"Completed detection cycle for all {len(active_stations)} stations")
            
        except Exception as e:
            logger.error(f"Error during detection cycle: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def run(self):
        """Exécute le service de détection en continu."""
        global running
        
        logger.info(f"Starting detection service (max_concurrent={self.max_concurrent}, interval={self.interval}s)")
        
        try:
            # Boucle principale du service
            while running:
                start_time = time.time()
                
                # Exécuter un cycle de détection
                await self.run_detection_cycle()
                
                # Calculer le temps écoulé et attendre jusqu'au prochain intervalle
                elapsed = time.time() - start_time
                wait_time = max(0, self.interval - elapsed)
                
                if wait_time > 0 and running:
                    logger.info(f"Waiting {wait_time:.1f} seconds until next detection cycle")
                    # Utiliser une boucle avec de courts délais pour pouvoir réagir rapidement aux signaux
                    for _ in range(int(wait_time / 0.5)):
                        if not running:
                            break
                        await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error in detection service: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        finally:
            # Nettoyage
            logger.info("Shutting down detection service")
            self.db_session.close()

async def main():
    """Fonction principale."""
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Run the music detection service")
    parser.add_argument("--max_concurrent", type=int, default=5,
                        help="Maximum number of stations to process concurrently")
    parser.add_argument("--interval", type=int, default=60,
                        help="Interval in seconds between detection cycles")
    args = parser.parse_args()
    
    # Initialiser la base de données
    init_db()
    logger.info("Database initialized successfully")
    
    # Configurer le gestionnaire de signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Créer et exécuter le service de détection
    service = DetectionService(max_concurrent=args.max_concurrent, interval=args.interval)
    await service.run()

if __name__ == "__main__":
    asyncio.run(main()) 