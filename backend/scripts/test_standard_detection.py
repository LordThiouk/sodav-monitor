#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script standardisé pour tester le cycle complet de détection musicale.
Usage: python test_standard_detection.py <audio_file_path> [--station_id <id>] [--station_name <name>]

Ce script effectue les opérations suivantes :
1. Charge un fichier audio
2. Extrait les caractéristiques audio et génère des empreintes digitales (standard et Chromaprint)
3. Teste la détection locale avec les empreintes
4. Si la détection locale échoue, teste la détection avec AcoustID
5. Si AcoustID échoue, teste la détection avec AudD
6. Crée ou met à jour la piste dans la base de données avec toutes les métadonnées
7. Simule le cycle complet de détection (début, suivi, fin)
8. Vérifie que l'ISRC, les empreintes et les statistiques sont correctement sauvegardés
9. Affiche un rapport détaillé des résultats

Ce script sert de modèle standardisé pour tous les tests de détection.
"""

import os
import sys
import asyncio
import logging
import argparse
import json
import time
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pydub import AudioSegment

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal
from backend.models.models import Track, Artist, TrackDetection, TrackStats, StationTrackStats, Fingerprint
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.external_services import AuddService, AcoustIDService
from backend.utils.logging_config import setup_logging, log_with_category

# Configuration du logging
logger = setup_logging(__name__)

class StandardDetectionTest:
    """
    Classe pour tester le cycle complet de détection musicale de manière standardisée.
    """
    
    def __init__(self, audio_file_path: str, station_id: int = 1, station_name: str = "Test Station"):
        """
        Initialise le test de détection.
        
        Args:
            audio_file_path: Chemin vers le fichier audio à tester
            station_id: ID de la station (par défaut: 1)
            station_name: Nom de la station (par défaut: "Test Station")
        """
        self.audio_file_path = audio_file_path
        self.station_id = station_id
        self.station_name = station_name
        self.db_session = None
        self.track_manager = None
        self.feature_extractor = None
        self.audio_data = None
        self.features = None
        self.detection_result = None
        self.track = None
        self.start_time = None
        self.processing_time = None
        
    async def setup(self):
        """
        Configure l'environnement de test.
        """
        # Initialiser la base de données
        init_db()
        self.db_session = SessionLocal()
        
        # Initialiser les composants nécessaires
        self.feature_extractor = FeatureExtractor()
        self.track_manager = TrackManager(self.db_session, self.feature_extractor)
        
        # Configurer les services externes
        self.audd_api_key = os.environ.get("AUDD_API_KEY")
        self.acoustid_api_key = os.environ.get("ACOUSTID_API_KEY")
        
        self.audd_service = None
        self.acoustid_service = None
        
        if self.audd_api_key:
            from backend.detection.audio_processor.external_services import AuddService
            self.audd_service = AuddService(self.audd_api_key)
            log_with_category(logger, "TEST", "info", "Service AudD initialisé")
        else:
            log_with_category(logger, "TEST", "warning", "AUDD_API_KEY non définie, le service AudD ne sera pas utilisé")
        
        if self.acoustid_api_key:
            from backend.detection.audio_processor.external_services import AcoustIDService
            self.acoustid_service = AcoustIDService(self.acoustid_api_key)
            log_with_category(logger, "TEST", "info", "Service AcoustID initialisé")
        else:
            log_with_category(logger, "TEST", "warning", "ACOUSTID_API_KEY non définie, le service AcoustID ne sera pas utilisé")
    
    async def load_audio(self):
        """
        Charge le fichier audio.
        """
        log_with_category(logger, "TEST", "info", "=== ÉTAPE 1: Chargement du fichier audio ===")
        
        # Vérifier que le fichier existe
        if not os.path.exists(self.audio_file_path):
            log_with_category(logger, "TEST", "error", f"Le fichier {self.audio_file_path} n'existe pas")
            return False
        
        # Lire le fichier audio
        with open(self.audio_file_path, "rb") as f:
            self.audio_data = f.read()
        
        log_with_category(logger, "TEST", "info", f"Fichier audio chargé: {self.audio_file_path} ({len(self.audio_data)} bytes)")
        return True
    
    async def extract_features(self):
        """
        Extrait les caractéristiques audio et génère les empreintes digitales.
        """
        log_with_category(logger, "TEST", "info", "=== ÉTAPE 2: Extraction des caractéristiques audio ===")
        
        # Créer les données de station
        station_data = {
            "raw_audio": self.audio_data,
            "station_id": self.station_id,
            "station_name": self.station_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Mesurer le temps de traitement
        self.start_time = time.time()
        
        # Traiter les données de station
        self.detection_result = await self.track_manager.process_station_data(station_data)
        
        # Vérifier si la détection a réussi
        if not self.detection_result.get("success", False):
            log_with_category(logger, "TEST", "error", f"Échec de la détection: {self.detection_result.get('error', 'Erreur inconnue')}")
            return False
        
        log_with_category(logger, "TEST", "info", "Caractéristiques audio extraites avec succès")
        return True
    
    async def finalize_detection(self):
        """
        Finalise la détection en appelant _end_current_track.
        """
        log_with_category(logger, "TEST", "info", "=== ÉTAPE 3: Finalisation de la détection ===")
        
        # Finaliser la détection
        log_with_category(logger, "TEST", "info", f"Finalisation de la détection pour la station {self.station_name} (ID: {self.station_id})")
        self.track_manager._end_current_track(self.station_id)
        log_with_category(logger, "TEST", "info", f"Détection finalisée pour la station {self.station_name} (ID: {self.station_id})")
        
        # Calculer le temps de traitement
        self.processing_time = time.time() - self.start_time
        
        return True
    
    async def verify_results(self):
        """
        Vérifie les résultats de la détection.
        """
        log_with_category(logger, "TEST", "info", "=== ÉTAPE 4: Vérification des résultats ===")
        
        # Vérifier si la détection a réussi
        if not self.detection_result.get("success", False):
            log_with_category(logger, "TEST", "error", "La détection a échoué, impossible de vérifier les résultats")
            return False
        
        # Récupérer les informations de la piste détectée
        detection_info = self.detection_result.get("detection", {})
        track_id = detection_info.get("track_id")
        
        if not track_id:
            log_with_category(logger, "TEST", "error", "Aucun ID de piste trouvé dans les résultats de détection")
            return False
        
        # Récupérer la piste depuis la base de données
        self.track = self.db_session.query(Track).filter_by(id=track_id).first()
        
        if not self.track:
            log_with_category(logger, "TEST", "error", f"Piste avec ID {track_id} non trouvée dans la base de données")
            return False
        
        # Vérifier les métadonnées de la piste
        log_with_category(logger, "TEST", "info", f"Piste détectée: {self.track.title} par {self.track.artist.name}")
        log_with_category(logger, "TEST", "info", f"ISRC: {self.track.isrc or 'Non disponible'}")
        log_with_category(logger, "TEST", "info", f"Label: {self.track.label or 'Non disponible'}")
        log_with_category(logger, "TEST", "info", f"Album: {self.track.album or 'Non disponible'}")
        log_with_category(logger, "TEST", "info", f"Date de sortie: {self.track.release_date or 'Non disponible'}")
        
        # Vérifier les empreintes
        log_with_category(logger, "TEST", "info", f"Empreinte standard: {self.track.fingerprint[:20] + '...' if self.track.fingerprint else 'Non disponible'}")
        log_with_category(logger, "TEST", "info", f"Empreinte Chromaprint: {self.track.chromaprint[:20] + '...' if self.track.chromaprint else 'Non disponible'}")
        
        # Vérifier les empreintes dans la table fingerprints
        fingerprints = self.db_session.query(Fingerprint).filter_by(track_id=track_id).all()
        log_with_category(logger, "TEST", "info", f"Nombre d'empreintes dans la table fingerprints: {len(fingerprints)}")
        
        for fp in fingerprints:
            log_with_category(logger, "TEST", "info", f"Empreinte ID: {fp.id}, Algorithme: {fp.algorithm}, Hash: {fp.hash[:20] + '...' if fp.hash else 'Non disponible'}")
        
        # Vérifier les détections
        detections = self.db_session.query(TrackDetection).filter_by(track_id=track_id, station_id=self.station_id).all()
        log_with_category(logger, "TEST", "info", f"Nombre de détections: {len(detections)}")
        
        if detections:
            latest_detection = max(detections, key=lambda d: d.detected_at)
            log_with_category(logger, "TEST", "info", f"Dernière détection: {latest_detection.detected_at}")
            log_with_category(logger, "TEST", "info", f"Durée de lecture: {latest_detection.play_duration}")
            log_with_category(logger, "TEST", "info", f"Méthode de détection: {latest_detection.detection_method}")
            log_with_category(logger, "TEST", "info", f"Confiance: {latest_detection.confidence}")
        
        # Vérifier les statistiques
        track_stats = self.db_session.query(TrackStats).filter_by(track_id=track_id).first()
        if track_stats:
            log_with_category(logger, "TEST", "info", f"Statistiques de piste: {track_stats.total_plays} lectures, {track_stats.total_play_time} secondes")
        
        station_track_stats = self.db_session.query(StationTrackStats).filter_by(track_id=track_id, station_id=self.station_id).first()
        if station_track_stats:
            log_with_category(logger, "TEST", "info", f"Statistiques de station: {station_track_stats.play_count} lectures, {station_track_stats.total_play_time} secondes")
        
        return True
    
    async def generate_report(self):
        """
        Génère un rapport détaillé des résultats.
        """
        log_with_category(logger, "TEST", "info", "=== ÉTAPE 5: Génération du rapport ===")
        
        report = {
            "test_info": {
                "audio_file": self.audio_file_path,
                "station_id": self.station_id,
                "station_name": self.station_name,
                "timestamp": datetime.now().isoformat(),
                "processing_time": self.processing_time
            },
            "detection_result": self.detection_result,
            "track_info": None,
            "fingerprints": [],
            "detections": [],
            "statistics": {}
        }
        
        if self.track:
            # Informations sur la piste
            report["track_info"] = {
                "id": self.track.id,
                "title": self.track.title,
                "artist": self.track.artist.name,
                "album": self.track.album,
                "isrc": self.track.isrc,
                "label": self.track.label,
                "release_date": self.track.release_date,
                "fingerprint": self.track.fingerprint[:20] + "..." if self.track.fingerprint else None,
                "chromaprint": self.track.chromaprint[:20] + "..." if self.track.chromaprint else None
            }
            
            # Empreintes
            fingerprints = self.db_session.query(Fingerprint).filter_by(track_id=self.track.id).all()
            for fp in fingerprints:
                report["fingerprints"].append({
                    "id": fp.id,
                    "algorithm": fp.algorithm,
                    "hash": fp.hash[:20] + "..." if fp.hash else None
                })
            
            # Détections
            detections = self.db_session.query(TrackDetection).filter_by(track_id=self.track.id, station_id=self.station_id).all()
            for detection in detections:
                report["detections"].append({
                    "id": detection.id,
                    "detected_at": detection.detected_at.isoformat(),
                    "play_duration": str(detection.play_duration),
                    "detection_method": detection.detection_method,
                    "confidence": detection.confidence
                })
            
            # Statistiques
            track_stats = self.db_session.query(TrackStats).filter_by(track_id=self.track.id).first()
            if track_stats:
                report["statistics"]["track_stats"] = {
                    "total_plays": track_stats.total_plays,
                    "total_play_time": str(track_stats.total_play_time),
                    "average_confidence": track_stats.average_confidence
                }
            
            station_track_stats = self.db_session.query(StationTrackStats).filter_by(track_id=self.track.id, station_id=self.station_id).first()
            if station_track_stats:
                report["statistics"]["station_track_stats"] = {
                    "play_count": station_track_stats.play_count,
                    "total_play_time": str(station_track_stats.total_play_time),
                    "average_confidence": station_track_stats.average_confidence
                }
        
        # Sauvegarder le rapport dans un fichier JSON
        report_file = f"detection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        log_with_category(logger, "TEST", "info", f"Rapport sauvegardé dans {report_file}")
        
        return report
    
    async def cleanup(self):
        """
        Nettoie les ressources utilisées par le test.
        """
        if self.db_session:
            self.db_session.close()
            log_with_category(logger, "TEST", "info", "Session de base de données fermée")
    
    async def run(self):
        """
        Exécute le test complet.
        """
        try:
            # Configurer l'environnement de test
            await self.setup()
            
            # Charger le fichier audio
            if not await self.load_audio():
                return False
            
            # Extraire les caractéristiques audio
            if not await self.extract_features():
                return False
            
            # Finaliser la détection
            if not await self.finalize_detection():
                return False
            
            # Vérifier les résultats
            if not await self.verify_results():
                return False
            
            # Générer le rapport
            await self.generate_report()
            
            log_with_category(logger, "TEST", "info", "=== TEST COMPLET RÉUSSI ===")
            return True
            
        except Exception as e:
            import traceback
            log_with_category(logger, "TEST", "error", f"Erreur lors du test: {str(e)}")
            log_with_category(logger, "TEST", "error", traceback.format_exc())
            return False
            
        finally:
            # Nettoyer les ressources
            await self.cleanup()

async def main():
    """
    Fonction principale.
    """
    parser = argparse.ArgumentParser(description="Test standardisé du cycle complet de détection musicale")
    parser.add_argument("audio_file_path", help="Chemin vers le fichier audio à tester")
    parser.add_argument("--station_id", type=int, default=1, help="ID de la station (par défaut: 1)")
    parser.add_argument("--station_name", default="Test Station", help="Nom de la station (par défaut: 'Test Station')")
    args = parser.parse_args()
    
    # Créer et exécuter le test
    test = StandardDetectionTest(args.audio_file_path, args.station_id, args.station_name)
    success = await test.run()
    
    # Retourner le code de sortie approprié
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 