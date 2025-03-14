#!/usr/bin/env python3
"""
Script pour récupérer les stations de radio sénégalaises pour les tests d'intégration.
"""

import logging
from typing import Any, Dict, List

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Radio Browser API endpoint
API_URL = "https://de1.api.radio-browser.info/json/stations/bycountry/senegal"


def fetch_senegal_stations() -> List[Dict[str, Any]]:
    """
    Récupère les stations de radio sénégalaises depuis l'API Radio Browser.

    Returns:
        List[Dict]: Liste des stations avec leurs informations
    """
    try:
        # Fetch stations from the API
        logger.info("Récupération des stations de radio sénégalaises...")
        headers = {"User-Agent": "SODAV-Monitor/1.0", "Content-Type": "application/json"}
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status()

        stations = response.json()
        logger.info(f"Trouvé {len(stations)} stations de radio sénégalaises.")

        # Convertir au format attendu par les tests
        formatted_stations = []
        for station in stations:
            if not station.get("url"):
                continue

            formatted_stations.append(
                {
                    "name": station.get("name", "Station inconnue"),
                    "url": station.get("url", ""),
                    "location": station.get("country", "Dakar"),
                    "language": station.get("language", "Wolof/Français"),
                    "genre": station.get("tags", "").split(",")[0]
                    if station.get("tags")
                    else "Généraliste",
                }
            )

        logger.info(f"Formaté {len(formatted_stations)} stations avec des URLs valides.")
        return formatted_stations

    except requests.RequestException as e:
        logger.error(f"Erreur lors de la récupération des stations: {e}")
        return []
    except Exception as e:
        logger.error(f"Erreur lors du traitement des stations: {e}")
        return []


if __name__ == "__main__":
    stations = fetch_senegal_stations()
    print(f"Récupéré {len(stations)} stations de radio sénégalaises.")
