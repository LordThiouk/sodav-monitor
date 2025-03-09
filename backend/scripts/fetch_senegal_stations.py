#!/usr/bin/env python
"""
Script pour récupérer les données des stations radio sénégalaises.
Ce script permet de récupérer les données des stations radio sénégalaises à partir d'une API
et de les sauvegarder dans un format compatible avec notre système de détection.
"""

import os
import sys
import asyncio
import argparse
import json
import aiohttp
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from backend.utils.logging_config import setup_logging, log_with_category

# Configurer le logging
logger = setup_logging(__name__)

# URL de l'API Radio Browser pour les stations sénégalaises
RADIO_BROWSER_API_URL = "https://de1.api.radio-browser.info/json/stations/bycountry/senegal"

async def fetch_senegal_stations() -> List[Dict[str, Any]]:
    """
    Récupérer les données des stations radio sénégalaises à partir de l'API Radio Browser.
    
    Returns:
        Liste des stations radio sénégalaises
    """
    try:
        log_with_category(logger, "FETCH", "info", "Fetching Senegal radio stations from Radio Browser API")
        
        async with aiohttp.ClientSession() as session:
            # Définir un User-Agent pour éviter d'être bloqué par l'API
            headers = {
                "User-Agent": "SODAV-Monitor/1.0",
                "Content-Type": "application/json"
            }
            
            # Récupérer les stations sénégalaises
            async with session.get(RADIO_BROWSER_API_URL, headers=headers) as response:
                if response.status != 200:
                    log_with_category(logger, "FETCH", "error", f"Error fetching stations: HTTP {response.status}")
                    return []
                
                # Analyser la réponse JSON
                stations_data = await response.json()
                log_with_category(logger, "FETCH", "info", f"Found {len(stations_data)} Senegal radio stations")
                
                return stations_data
    
    except aiohttp.ClientError as e:
        log_with_category(logger, "FETCH", "error", f"Client error: {str(e)}")
        return []
    except Exception as e:
        log_with_category(logger, "FETCH", "error", f"Unexpected error: {str(e)}")
        import traceback
        log_with_category(logger, "FETCH", "error", traceback.format_exc())
        return []

def convert_to_sodav_format(stations_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convertir les données des stations au format SODAV Monitor.
    
    Args:
        stations_data: Données des stations au format Radio Browser
        
    Returns:
        Données des stations au format SODAV Monitor
    """
    sodav_stations = []
    
    for i, station in enumerate(stations_data):
        # Vérifier que l'URL est valide
        url = station.get("url_resolved") or station.get("url")
        if not url:
            continue
        
        # Créer la station au format SODAV
        sodav_station = {
            "id": i + 1,
            "name": station.get("name", f"Unknown Station {i+1}"),
            "url": url,
            "country": station.get("country", "Sénégal"),
            "language": station.get("language", "Français"),
            "genre": station.get("tags", "").split(",")[0] if station.get("tags") else "Variété",
            "bitrate": station.get("bitrate", 0),
            "codec": station.get("codec", ""),
            "homepage": station.get("homepage", ""),
            "favicon": station.get("favicon", ""),
            "votes": station.get("votes", 0),
            "original_id": station.get("stationuuid", "")
        }
        
        sodav_stations.append(sodav_station)
    
    return sodav_stations

def filter_stations(stations: List[Dict[str, Any]], min_bitrate: int = 64, min_votes: int = 0) -> List[Dict[str, Any]]:
    """
    Filtrer les stations selon des critères de qualité.
    
    Args:
        stations: Liste des stations à filtrer
        min_bitrate: Bitrate minimum (kbps)
        min_votes: Nombre minimum de votes
        
    Returns:
        Liste des stations filtrées
    """
    filtered_stations = []
    
    for station in stations:
        # Convertir le bitrate en entier (peut être une chaîne ou None)
        bitrate = 0
        try:
            if station.get("bitrate"):
                bitrate = int(station["bitrate"])
        except (ValueError, TypeError):
            bitrate = 0
        
        # Convertir les votes en entier
        votes = 0
        try:
            if station.get("votes"):
                votes = int(station["votes"])
        except (ValueError, TypeError):
            votes = 0
        
        # Appliquer les filtres
        if bitrate >= min_bitrate and votes >= min_votes:
            filtered_stations.append(station)
    
    return filtered_stations

async def main():
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Récupérer les données des stations radio sénégalaises")
    parser.add_argument("--output", default="backend/config/senegal_stations.json", help="Fichier de sortie pour les stations")
    parser.add_argument("--min-bitrate", type=int, default=64, help="Bitrate minimum (kbps)")
    parser.add_argument("--min-votes", type=int, default=0, help="Nombre minimum de votes")
    parser.add_argument("--limit", type=int, default=0, help="Nombre maximum de stations à récupérer (0 = pas de limite)")
    parser.add_argument("--test-detection", action="store_true", help="Tester la détection sur les stations récupérées")
    parser.add_argument("--sample-duration", type=int, default=20, help="Durée de l'échantillon audio en secondes")
    parser.add_argument("--output-dir", help="Répertoire de sortie pour les échantillons audio")
    args = parser.parse_args()
    
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
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(filtered_stations, f, indent=2, ensure_ascii=False)
    
    print(f"✅ {len(filtered_stations)} stations sauvegardées dans {args.output}")
    
    # Tester la détection si demandé
    if args.test_detection:
        print("\n=== Test de détection sur les stations récupérées ===")
        
        # Importer le script de surveillance des stations
        sys.path.insert(0, str(current_dir))
        from monitor_stations import monitor_stations
        
        # Lancer la surveillance des stations
        await monitor_stations(
            stations_config=filtered_stations,
            output_dir=args.output_dir,
            sample_duration=args.sample_duration,
            interval=0  # Pas d'intervalle pour le test
        )

if __name__ == "__main__":
    asyncio.run(main()) 