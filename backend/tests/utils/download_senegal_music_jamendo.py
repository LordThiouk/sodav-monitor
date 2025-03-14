"""
Script pour télécharger des morceaux de musique sénégalaise depuis Jamendo.

Ce script utilise l'API Jamendo pour rechercher et télécharger de la musique
sénégalaise ou africaine sous licence Creative Commons.
"""

import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

from backend.tests.utils.radio_simulator import download_test_audio

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("download_senegal_music_jamendo")

# Répertoire de destination
AUDIO_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "audio" / "senegal"

# Clé API Jamendo (vous devez vous inscrire pour obtenir une clé gratuite)
# https://devportal.jamendo.com/
JAMENDO_CLIENT_ID = "YOUR_JAMENDO_CLIENT_ID"  # Remplacez par votre clé API

# URL de base de l'API Jamendo
JAMENDO_API_URL = "https://api.jamendo.com/v3.0"


def search_jamendo_tracks(query, limit=10):
    """
    Recherche des morceaux sur Jamendo.
    
    Args:
        query: Termes de recherche
        limit: Nombre maximum de résultats
        
    Returns:
        Liste de morceaux trouvés
    """
    endpoint = f"{JAMENDO_API_URL}/tracks/"
    
    params = {
        "client_id": JAMENDO_CLIENT_ID,
        "format": "json",
        "limit": limit,
        "search": query,
        "include": "musicinfo",
        "audioformat": "mp32",
    }
    
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "results" in data:
            return data["results"]
        else:
            logger.warning(f"Aucun résultat trouvé pour la recherche: {query}")
            return []
            
    except Exception as e:
        logger.error(f"Erreur lors de la recherche Jamendo: {e}")
        return []


def download_jamendo_tracks():
    """
    Recherche et télécharge des morceaux de musique sénégalaise/africaine depuis Jamendo.
    
    Returns:
        Nombre de téléchargements réussis
    """
    os.makedirs(AUDIO_DIR, exist_ok=True)
    logger.info(f"Téléchargement des morceaux dans {AUDIO_DIR}")
    
    # Liste des termes de recherche liés à la musique sénégalaise
    search_terms = [
        "senegal music",
        "mbalax",
        "youssou ndour",
        "baaba maal",
        "african percussion",
        "west african",
        "dakar music",
        "senegalese traditional",
        "sabar",
        "african jazz",
    ]
    
    successful_downloads = 0
    all_tracks = []
    
    # Rechercher des morceaux pour chaque terme
    for term in search_terms:
        logger.info(f"Recherche de morceaux pour: {term}")
        tracks = search_jamendo_tracks(term, limit=3)
        all_tracks.extend(tracks)
        
        # Pause pour éviter de surcharger l'API
        time.sleep(1)
    
    # Télécharger les morceaux trouvés
    for i, track in enumerate(all_tracks):
        try:
            # Extraire les informations du morceau
            track_name = track.get("name", f"track_{i}")
            artist_name = track.get("artist_name", "unknown")
            audio_url = track.get("audio", "")
            
            if not audio_url:
                logger.warning(f"URL audio manquante pour {track_name}")
                continue
            
            # Générer un nom de fichier
            safe_name = "".join(c if c.isalnum() else "_" for c in f"{artist_name}_{track_name}")
            filename = f"{safe_name}.mp3"
            
            logger.info(f"Téléchargement de {track_name} par {artist_name}")
            output_path = download_test_audio(audio_url, AUDIO_DIR, filename)
            
            if output_path:
                successful_downloads += 1
                logger.info(f"Téléchargement réussi: {output_path}")
                
                # Enregistrer les métadonnées du morceau
                metadata_file = output_path.with_suffix(".json")
                with open(metadata_file, "w", encoding="utf-8") as f:
                    json.dump(track, f, indent=2)
                
                # Limiter le nombre de téléchargements pour éviter de surcharger
                if successful_downloads >= 10:
                    break
            else:
                logger.warning(f"Échec du téléchargement: {audio_url}")
                
            # Pause entre les téléchargements
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement: {e}")
    
    logger.info(f"Téléchargement terminé. {successful_downloads} fichiers téléchargés avec succès.")
    
    # Si Jamendo ne fonctionne pas, utiliser des sources alternatives
    if successful_downloads == 0:
        logger.info("Tentative avec des sources alternatives...")
        return download_alternative_tracks()
    
    return successful_downloads


def download_alternative_tracks():
    """
    Télécharge des morceaux à partir de sources alternatives.
    
    Returns:
        Nombre de téléchargements réussis
    """
    # URLs alternatives de musique africaine libre de droits
    alternative_urls = [
        # Musique africaine libre de droits
        "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/no_curator/Kel_Assouf/Live_at_Eurosonic_2016/Kel_Assouf_-_01_-_Tin_Tamana.mp3",
        "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/no_curator/Kel_Assouf/Live_at_Eurosonic_2016/Kel_Assouf_-_02_-_Tamatant.mp3",
        "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/no_curator/Kel_Assouf/Live_at_Eurosonic_2016/Kel_Assouf_-_03_-_Alyochan.mp3",
        
        # Musique africaine de la Bibliothèque du Congrès (domaine public)
        "https://www.loc.gov/static/programs/national-recording-preservation-board/documents/AfricanMusic.mp3",
        
        # Musique sous licence Creative Commons
        "https://ccmixter.org/content/texasradiofish/texasradiofish_-_Yoruba_Soul_1.mp3",
        "https://ccmixter.org/content/Seastyle/Seastyle_-_Africa.mp3",
        "https://ccmixter.org/content/Loveshadow/Loveshadow_-_Highlife.mp3",
    ]
    
    successful_downloads = 0
    for i, url in enumerate(alternative_urls):
        try:
            filename = f"african_music_{i+1}.mp3"
            logger.info(f"Téléchargement de {url}")
            output_path = download_test_audio(url, AUDIO_DIR, filename)
            
            if output_path:
                successful_downloads += 1
                logger.info(f"Téléchargement réussi: {output_path}")
            else:
                logger.warning(f"Échec du téléchargement: {url}")
                
            # Pause entre les téléchargements
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement: {e}")
    
    return successful_downloads


if __name__ == "__main__":
    if JAMENDO_CLIENT_ID == "YOUR_JAMENDO_CLIENT_ID":
        logger.warning("Veuillez configurer votre clé API Jamendo dans le script.")
        logger.info("Utilisation des sources alternatives...")
        download_alternative_tracks()
    else:
        download_jamendo_tracks() 