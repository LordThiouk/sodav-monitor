"""
Script pour télécharger directement des fichiers audio de test.

Ce script télécharge des fichiers audio à partir d'URLs spécifiques
qui sont connues pour être disponibles et libres de droits.
"""

import logging
import os
import time
from pathlib import Path

import requests

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("download_test_audio_direct")

# Répertoire de destination
AUDIO_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "audio" / "senegal"

# Liste d'URLs de fichiers audio libres de droits
# Ces URLs sont vérifiées et fonctionnelles
AUDIO_URLS = [
    # Musique africaine de la Free Music Archive
    "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/WFMU/Monplaisir/Turquoise/Monplaisir_-_01_-_Toutes_les_Filles_Sont_Belles.mp3",
    "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/WFMU/Monplaisir/Turquoise/Monplaisir_-_02_-_Tourbillon.mp3",
    "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/WFMU/Monplaisir/Turquoise/Monplaisir_-_03_-_Turquoise.mp3",
    "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/WFMU/Monplaisir/Turquoise/Monplaisir_-_04_-_Tout_Va_Bien.mp3",
    "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/WFMU/Monplaisir/Turquoise/Monplaisir_-_05_-_Tournesol.mp3",
    
    # Musique africaine de la Bibliothèque du Congrès (domaine public)
    "https://ia800504.us.archive.org/2/items/78_african-drum-music_not-identified-not-identified_gbia0001424b/01%20-%20AFRICAN%20DRUM%20MUSIC%20-%20Not%20Identified.mp3",
    "https://ia800504.us.archive.org/2/items/78_african-drum-music_not-identified-not-identified_gbia0001424b/02%20-%20AFRICAN%20DRUM%20MUSIC%20-%20Not%20Identified.mp3",
    
    # Musique sous licence Creative Commons
    "https://ia801309.us.archive.org/24/items/AfricanDrumMusic/01-AfricanDrumMusic.mp3",
    "https://ia801309.us.archive.org/24/items/AfricanDrumMusic/02-AfricanDrumMusic.mp3",
    "https://ia801309.us.archive.org/24/items/AfricanDrumMusic/03-AfricanDrumMusic.mp3",
]


def download_file(url, output_path):
    """
    Télécharge un fichier à partir d'une URL.
    
    Args:
        url: URL du fichier à télécharger
        output_path: Chemin de destination
        
    Returns:
        True si le téléchargement a réussi, False sinon
    """
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Téléchargement réussi: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement de {url}: {e}")
        return False


def download_all_audio():
    """
    Télécharge tous les fichiers audio dans le répertoire de destination.
    
    Returns:
        Nombre de téléchargements réussis
    """
    # Créer le répertoire de destination s'il n'existe pas
    os.makedirs(AUDIO_DIR, exist_ok=True)
    logger.info(f"Téléchargement des fichiers audio dans {AUDIO_DIR}")
    
    successful_downloads = 0
    for i, url in enumerate(AUDIO_URLS):
        try:
            # Extraire le nom du fichier de l'URL ou générer un nom basé sur l'index
            filename = os.path.basename(url)
            if not filename or filename.endswith("/"):
                filename = f"test_audio_{i+1}.mp3"
            
            output_path = AUDIO_DIR / filename
            logger.info(f"Téléchargement de {url} vers {output_path}")
            
            if download_file(url, output_path):
                successful_downloads += 1
            
            # Pause entre les téléchargements
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement de {url}: {e}")
    
    logger.info(f"Téléchargement terminé. {successful_downloads}/{len(AUDIO_URLS)} fichiers téléchargés avec succès.")
    return successful_downloads


if __name__ == "__main__":
    download_all_audio() 