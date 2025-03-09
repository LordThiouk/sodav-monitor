#!/usr/bin/env python
"""
Script pour tester la détection de morceaux à partir des données de station.
Ce script permet de tester la détection de morceaux à partir des données audio d'une station radio.
"""

import os
import sys
import asyncio
import argparse
import json
import time
from datetime import datetime
from pathlib import Path
import logging

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from backend.detection.audio_processor.track_manager import TrackManager
from backend.models.database import get_db
from backend.utils.logging_config import setup_logging, log_with_category

# Configurer le logging
logger = setup_logging(__name__)

async def test_station_detection(audio_file_path: str, station_id: int = 1, station_name: str = "Test Station", verbose: bool = False):
    """
    Tester la détection de morceaux à partir des données de station.
    
    Args:
        audio_file_path: Chemin vers le fichier audio à tester
        station_id: ID de la station
        station_name: Nom de la station
        verbose: Afficher des informations détaillées
    """
    print(f"=== Test de détection pour la station {station_name} (ID: {station_id}) ===")
    
    # Vérifier que le fichier existe
    if not os.path.exists(audio_file_path):
        print(f"❌ Le fichier {audio_file_path} n'existe pas")
        return False
    
    # Lire le fichier audio
    try:
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
        
        print(f"✅ Fichier audio lu : {len(audio_data)} octets")
        
        # Créer les données de station
        station_data = {
            "raw_audio": audio_data,
            "station_id": station_id,
            "station_name": station_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Initialiser le gestionnaire de pistes
        db_session = next(get_db())
        track_manager = TrackManager(db_session)
        
        # Mesurer le temps de traitement
        start_time = time.time()
        
        # Traiter les données de station
        print("\nTraitement des données de station...")
        result = await track_manager.process_station_data(station_data)
        
        # Calculer le temps de traitement
        processing_time = time.time() - start_time
        
        # Afficher les résultats
        print(f"\nRésultat : {json.dumps(result, indent=2, default=str)}")
        print(f"\nTemps de traitement : {processing_time:.2f} secondes")
        
        if result.get("success"):
            print("\n✅ Détection réussie !")
            detection = result.get("detection", {})
            print(f"   Titre : {detection.get('title', 'Inconnu')}")
            print(f"   Artiste : {detection.get('artist', 'Inconnu')}")
            print(f"   Album : {detection.get('album', 'Inconnu')}")
            print(f"   Source : {result.get('source', 'Inconnue')}")
            print(f"   Confiance : {detection.get('confidence', 0)}")
            print(f"   Méthode de détection : {detection.get('detection_method', 'Inconnue')}")
            
            # Afficher des informations supplémentaires en mode verbose
            if verbose:
                print("\nInformations supplémentaires :")
                print(f"   ISRC : {detection.get('isrc', 'Non disponible')}")
                print(f"   Label : {detection.get('label', 'Non disponible')}")
                print(f"   Date de sortie : {detection.get('release_date', 'Non disponible')}")
                print(f"   Genre : {detection.get('genre', 'Non disponible')}")
                print(f"   Durée : {detection.get('duration', 0)} secondes")
                print(f"   Durée de lecture : {detection.get('play_duration', 0)} secondes")
                print(f"   Détecté à : {detection.get('detected_at', 'Inconnu')}")
                print(f"   Type audio : {detection.get('audio_type', 'Inconnu')}")
                
                # Afficher l'empreinte si disponible
                if 'fingerprint' in detection:
                    fingerprint = detection.get('fingerprint', '')
                    print(f"   Empreinte : {fingerprint[:20]}... (longueur: {len(fingerprint)})")
            
            return True
        else:
            print(f"\n❌ Échec de la détection : {result.get('error', 'Erreur inconnue')}")
            
            # Afficher des informations supplémentaires en mode verbose
            if verbose and 'audio_type' in result:
                print(f"   Type audio : {result.get('audio_type', 'Inconnu')}")
                
            return False
    
    except Exception as e:
        print(f"❌ Erreur lors du test : {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False
    finally:
        # Fermer la session de base de données
        db_session.close()

def main():
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Tester la détection de morceaux à partir des données de station")
    parser.add_argument("audio_file", help="Chemin vers le fichier audio à tester")
    parser.add_argument("--station-id", type=int, default=1, help="ID de la station")
    parser.add_argument("--station-name", default="Test Station", help="Nom de la station")
    parser.add_argument("--verbose", "-v", action="store_true", help="Afficher des informations détaillées")
    args = parser.parse_args()
    
    # Exécuter le test
    asyncio.run(test_station_detection(args.audio_file, args.station_id, args.station_name, args.verbose))

if __name__ == "__main__":
    main() 