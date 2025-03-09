#!/usr/bin/env python
"""
Script pour lancer la détection sur les stations radio sénégalaises.
Ce script combine la récupération des stations et le lancement de la détection.
"""

import os
import sys
import asyncio
import argparse
import json
import time
from pathlib import Path
import logging
from datetime import datetime

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from backend.utils.logging_config import setup_logging, log_with_category

# Configurer le logging
logger = setup_logging(__name__)

async def run_detection():
    """
    Lancer la détection sur les stations radio sénégalaises.
    """
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Lancer la détection sur les stations radio sénégalaises")
    parser.add_argument("--fetch", action="store_true", help="Récupérer les stations avant de lancer la détection")
    parser.add_argument("--stations-file", default="backend/config/senegal_stations.json", help="Fichier de configuration des stations")
    parser.add_argument("--output-dir", default=f"samples_{datetime.now().strftime('%Y%m%d_%H%M%S')}", help="Répertoire de sortie pour les échantillons audio")
    parser.add_argument("--sample-duration", type=int, default=20, help="Durée de l'échantillon audio en secondes")
    parser.add_argument("--interval", type=int, default=30, help="Intervalle entre les échantillons en secondes")
    parser.add_argument("--limit", type=int, default=5, help="Nombre maximum de stations à surveiller")
    parser.add_argument("--min-bitrate", type=int, default=64, help="Bitrate minimum (kbps) pour les stations")
    parser.add_argument("--min-votes", type=int, default=1, help="Nombre minimum de votes pour les stations")
    parser.add_argument("--continuous", action="store_true", help="Surveillance continue des stations")
    args = parser.parse_args()
    
    # Récupérer les stations si demandé
    if args.fetch:
        print("=== Récupération des stations radio sénégalaises ===")
        
        # Importer le script de récupération des stations
        sys.path.insert(0, str(current_dir))
        from fetch_senegal_stations import fetch_senegal_stations, convert_to_sodav_format, filter_stations
        
        # Récupérer les stations
        stations_data = await fetch_senegal_stations()
        
        if not stations_data:
            print("❌ Aucune station trouvée")
            return
        
        # Convertir au format SODAV
        sodav_stations = convert_to_sodav_format(stations_data)
        
        # Filtrer les stations
        filtered_stations = filter_stations(sodav_stations, args.min_bitrate, args.min_votes)
        print(f"Stations après filtrage : {len(filtered_stations)}/{len(sodav_stations)}")
        
        # Limiter le nombre de stations si demandé
        if args.limit > 0 and args.limit < len(filtered_stations):
            filtered_stations = filtered_stations[:args.limit]
            print(f"Stations limitées à {args.limit}")
        
        # Sauvegarder les stations
        os.makedirs(os.path.dirname(args.stations_file), exist_ok=True)
        with open(args.stations_file, "w", encoding="utf-8") as f:
            json.dump(filtered_stations, f, indent=2, ensure_ascii=False)
        
        print(f"✅ {len(filtered_stations)} stations sauvegardées dans {args.stations_file}")
        
        # Utiliser les stations récupérées
        stations = filtered_stations
    else:
        # Charger les stations depuis le fichier
        try:
            with open(args.stations_file, "r", encoding="utf-8") as f:
                stations = json.load(f)
            
            print(f"✅ {len(stations)} stations chargées depuis {args.stations_file}")
            
            # Limiter le nombre de stations si demandé
            if args.limit > 0 and args.limit < len(stations):
                stations = stations[:args.limit]
                print(f"Stations limitées à {args.limit}")
        except Exception as e:
            print(f"❌ Erreur lors du chargement des stations : {str(e)}")
            return
    
    # Créer le répertoire de sortie
    os.makedirs(args.output_dir, exist_ok=True)
    print(f"✅ Répertoire de sortie créé : {args.output_dir}")
    
    # Lancer la détection
    print("\n=== Lancement de la détection sur les stations ===")
    
    if args.continuous:
        # Surveillance continue
        from monitor_stations import monitor_stations
        
        # Lancer la surveillance des stations
        await monitor_stations(
            stations_config=stations,
            output_dir=args.output_dir,
            sample_duration=args.sample_duration,
            interval=args.interval
        )
    else:
        # Test unique
        from test_multiple_stations import test_multiple_stations, print_results_summary
        
        # Créer un fichier de mapping pour les stations
        station_mapping = {}
        for station in stations:
            # Extraire le nom de fichier de l'URL
            url = station["url"]
            filename = url.split("/")[-1]
            if "?" in filename:
                filename = filename.split("?")[0]
            
            # Ajouter au mapping
            station_mapping[filename] = {
                "id": station["id"],
                "name": station["name"]
            }
        
        # Sauvegarder le mapping
        mapping_file = os.path.join(args.output_dir, "station_mapping.json")
        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(station_mapping, f, indent=2, ensure_ascii=False)
        
        # Lancer le test
        results = await test_multiple_stations(
            audio_dir=args.output_dir,
            station_mapping=station_mapping,
            max_concurrent=min(3, len(stations))
        )
        
        # Afficher le résumé des résultats
        print_results_summary(results)
        
        # Sauvegarder les résultats
        results_file = os.path.join(args.output_dir, "detection_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"✅ Résultats sauvegardés dans {results_file}")

if __name__ == "__main__":
    try:
        asyncio.run(run_detection())
    except KeyboardInterrupt:
        print("\nDétection interrompue par l'utilisateur") 