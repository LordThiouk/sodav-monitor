#!/usr/bin/env python
"""
Script pour tester la détection de morceaux sur plusieurs stations en parallèle.
Ce script permet de tester la détection de morceaux à partir des données audio de plusieurs stations radio.
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
import glob
from typing import List, Dict, Any, Optional

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from backend.detection.audio_processor.track_manager import TrackManager
from backend.models.database import get_db
from backend.utils.logging_config import setup_logging, log_with_category

# Configurer le logging
logger = setup_logging(__name__)

async def process_station(
    audio_file_path: str, 
    station_id: int, 
    station_name: str, 
    track_manager: TrackManager
) -> Dict[str, Any]:
    """
    Traiter une station et détecter les morceaux.
    
    Args:
        audio_file_path: Chemin vers le fichier audio à tester
        station_id: ID de la station
        station_name: Nom de la station
        track_manager: Gestionnaire de pistes
        
    Returns:
        Dictionnaire contenant les résultats de la détection
    """
    try:
        # Vérifier que le fichier existe
        if not os.path.exists(audio_file_path):
            return {
                "success": False,
                "error": f"Le fichier {audio_file_path} n'existe pas",
                "station_id": station_id,
                "station_name": station_name,
                "file_path": audio_file_path
            }
        
        # Lire le fichier audio
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
        
        # Créer les données de station
        station_data = {
            "raw_audio": audio_data,
            "station_id": station_id,
            "station_name": station_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Mesurer le temps de traitement
        start_time = time.time()
        
        # Traiter les données de station
        result = await track_manager.process_station_data(station_data)
        
        # Simuler la fin de la détection en appelant _end_current_track
        # Cela permet de finaliser la détection et d'enregistrer les statistiques
        log_with_category(logger, "TEST", "info", f"Finalisation de la détection pour la station {station_name} (ID: {station_id})")
        track_manager._end_current_track(station_id)
        log_with_category(logger, "TEST", "info", f"Détection finalisée pour la station {station_name} (ID: {station_id})")
        
        # Calculer le temps de traitement
        processing_time = time.time() - start_time
        
        # Ajouter des informations supplémentaires au résultat
        result["processing_time"] = processing_time
        result["file_path"] = audio_file_path
        result["file_size"] = len(audio_data)
        result["detection_finalized"] = True
        
        return result
    
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "station_id": station_id,
            "station_name": station_name,
            "file_path": audio_file_path
        }

async def test_multiple_stations(
    audio_dir: str, 
    station_mapping: Optional[Dict[str, Dict[str, Any]]] = None,
    max_concurrent: int = 3
) -> List[Dict[str, Any]]:
    """
    Tester la détection de morceaux sur plusieurs stations en parallèle.
    
    Args:
        audio_dir: Répertoire contenant les fichiers audio à tester
        station_mapping: Dictionnaire de correspondance entre les noms de fichiers et les stations
        max_concurrent: Nombre maximum de détections en parallèle
        
    Returns:
        Liste des résultats de détection
    """
    print(f"=== Test de détection sur plusieurs stations (max_concurrent={max_concurrent}) ===")
    print(f"Répertoire audio : {audio_dir}")
    
    # Trouver tous les fichiers audio dans le répertoire
    audio_files = []
    for ext in ["*.mp3", "*.wav", "*.ogg", "*.flac"]:
        audio_files.extend(glob.glob(os.path.join(audio_dir, ext)))
    
    print(f"Nombre de fichiers audio trouvés : {len(audio_files)}")
    
    if not audio_files:
        print("❌ Aucun fichier audio trouvé dans le répertoire")
        return []
    
    # Créer une session de base de données
    db_session = next(get_db())
    
    try:
        # Initialiser le gestionnaire de pistes
        track_manager = TrackManager(db_session)
        
        # Créer les tâches pour chaque fichier audio
        tasks = []
        for i, audio_file in enumerate(audio_files):
            file_name = os.path.basename(audio_file)
            
            # Utiliser le mapping si disponible, sinon utiliser des valeurs par défaut
            if station_mapping and file_name in station_mapping:
                station_info = station_mapping[file_name]
                station_id = station_info.get("id", i + 1)
                station_name = station_info.get("name", f"Station {i + 1}")
            else:
                station_id = i + 1
                station_name = f"Station {i + 1}"
            
            # Créer la tâche
            task = process_station(audio_file, station_id, station_name, track_manager)
            tasks.append(task)
        
        # Exécuter les tâches avec une limite de concurrence
        results = []
        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i+max_concurrent]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)
            
            # Afficher la progression
            print(f"Progression : {min(i + max_concurrent, len(tasks))}/{len(tasks)} fichiers traités")
        
        return results
    
    finally:
        # Fermer la session de base de données
        db_session.close()

def print_results_summary(results: List[Dict[str, Any]]):
    """
    Afficher un résumé des résultats de détection.
    
    Args:
        results: Liste des résultats de détection
    """
    print("\n=== Résumé des résultats ===")
    
    # Compter les succès et les échecs
    success_count = sum(1 for r in results if r.get("success", False))
    failure_count = len(results) - success_count
    
    print(f"Total des fichiers traités : {len(results)}")
    print(f"Détections réussies : {success_count}")
    print(f"Détections échouées : {failure_count}")
    
    if success_count > 0:
        # Calculer le temps de traitement moyen
        avg_time = sum(r.get("processing_time", 0) for r in results if r.get("success", False)) / success_count
        print(f"Temps de traitement moyen : {avg_time:.2f} secondes")
        
        # Compter les méthodes de détection
        detection_methods = {}
        for r in results:
            if r.get("success", False) and "detection" in r:
                method = r["detection"].get("detection_method", "unknown")
                detection_methods[method] = detection_methods.get(method, 0) + 1
        
        print("\nMéthodes de détection :")
        for method, count in detection_methods.items():
            print(f"  - {method}: {count} ({count/success_count*100:.1f}%)")
    
    # Afficher les détails des échecs
    if failure_count > 0:
        print("\nDétails des échecs :")
        for i, r in enumerate(results):
            if not r.get("success", False):
                print(f"  {i+1}. Station: {r.get('station_name', 'Inconnue')}")
                print(f"     Fichier: {r.get('file_path', 'Inconnu')}")
                print(f"     Erreur: {r.get('error', 'Inconnue')}")
                print()

def main():
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Tester la détection de morceaux sur plusieurs stations")
    parser.add_argument("audio_dir", help="Répertoire contenant les fichiers audio à tester")
    parser.add_argument("--mapping", help="Fichier JSON de correspondance entre les noms de fichiers et les stations")
    parser.add_argument("--max-concurrent", type=int, default=3, help="Nombre maximum de détections en parallèle")
    parser.add_argument("--output", help="Fichier de sortie pour les résultats (JSON)")
    args = parser.parse_args()
    
    # Charger le mapping si disponible
    station_mapping = None
    if args.mapping and os.path.exists(args.mapping):
        try:
            with open(args.mapping, "r") as f:
                station_mapping = json.load(f)
            print(f"Mapping chargé depuis {args.mapping} : {len(station_mapping)} stations")
        except Exception as e:
            print(f"❌ Erreur lors du chargement du mapping : {str(e)}")
    
    # Exécuter le test
    results = asyncio.run(test_multiple_stations(args.audio_dir, station_mapping, args.max_concurrent))
    
    # Afficher le résumé des résultats
    print_results_summary(results)
    
    # Sauvegarder les résultats si demandé
    if args.output:
        try:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"✅ Résultats sauvegardés dans {args.output}")
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde des résultats : {str(e)}")

if __name__ == "__main__":
    main() 