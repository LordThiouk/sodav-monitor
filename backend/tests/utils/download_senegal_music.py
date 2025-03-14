"""
Script pour télécharger des morceaux de musique sénégalaise pour les tests.

Ce script télécharge une sélection de morceaux de musique sénégalaise
à partir de sources libres de droits pour les tests du système de détection.
"""

import logging
import os
from pathlib import Path

from backend.tests.utils.radio_simulator import download_test_audio

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("download_senegal_music")

# Répertoire de destination
AUDIO_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "audio" / "senegal"

# Liste de morceaux sénégalais libres de droits
# Ces URL sont des exemples et doivent être remplacées par des URL réelles de musique sénégalaise
SENEGAL_MUSIC_URLS = [
    # Musique traditionnelle sénégalaise
    "https://freemusicarchive.org/track/Senegal_Rhythm/download",  # Exemple - à remplacer
    "https://freemusicarchive.org/track/Dakar_Drums/download",     # Exemple - à remplacer
    
    # Mbalax moderne
    "https://freemusicarchive.org/track/Senegal_Dance/download",   # Exemple - à remplacer
    
    # Afro-jazz sénégalais
    "https://freemusicarchive.org/track/Senegal_Jazz/download",    # Exemple - à remplacer
    
    # Musique urbaine sénégalaise
    "https://freemusicarchive.org/track/Dakar_Urban/download",     # Exemple - à remplacer
]

# URLs alternatives de musique africaine libre de droits (si les URLs ci-dessus ne fonctionnent pas)
ALTERNATIVE_MUSIC_URLS = [
    # Musique africaine libre de droits de la Free Music Archive
    "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/no_curator/Kel_Assouf/Live_at_Eurosonic_2016/Kel_Assouf_-_01_-_Tin_Tamana.mp3",
    "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/no_curator/Kel_Assouf/Live_at_Eurosonic_2016/Kel_Assouf_-_02_-_Tamatant.mp3",
    "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/no_curator/Kel_Assouf/Live_at_Eurosonic_2016/Kel_Assouf_-_03_-_Alyochan.mp3",
    
    # Musique africaine de la Bibliothèque du Congrès (domaine public)
    "https://www.loc.gov/static/programs/national-recording-preservation-board/documents/AfricanMusic.mp3",
    
    # Musique africaine de la BBC Sound Effects (usage éducatif)
    "https://sound-effects-media.bbcrewind.co.uk/mp3/07074264.mp3",
]

# URLs de musique Creative Commons
CREATIVE_COMMONS_URLS = [
    # Musique sous licence Creative Commons
    "https://ccmixter.org/content/texasradiofish/texasradiofish_-_Yoruba_Soul_1.mp3",
    "https://ccmixter.org/content/Seastyle/Seastyle_-_Africa.mp3",
    "https://ccmixter.org/content/Loveshadow/Loveshadow_-_Highlife.mp3",
]


def download_all_music():
    """Télécharge tous les morceaux de musique dans le répertoire de destination."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    logger.info(f"Téléchargement des morceaux dans {AUDIO_DIR}")
    
    # Combiner toutes les URLs
    all_urls = SENEGAL_MUSIC_URLS + ALTERNATIVE_MUSIC_URLS + CREATIVE_COMMONS_URLS
    
    successful_downloads = 0
    for i, url in enumerate(all_urls):
        try:
            # Générer un nom de fichier basé sur l'index si le téléchargement réussit
            filename = f"senegal_music_{i+1}.mp3"
            
            logger.info(f"Téléchargement de {url} vers {filename}")
            output_path = download_test_audio(url, AUDIO_DIR, filename)
            
            if output_path:
                successful_downloads += 1
                logger.info(f"Téléchargement réussi: {output_path}")
            else:
                logger.warning(f"Échec du téléchargement: {url}")
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement de {url}: {e}")
    
    logger.info(f"Téléchargement terminé. {successful_downloads}/{len(all_urls)} fichiers téléchargés avec succès.")
    
    # Vérifier si des fichiers ont été téléchargés
    if successful_downloads == 0:
        logger.error("Aucun fichier n'a été téléchargé. Veuillez vérifier les URLs ou votre connexion Internet.")
    
    return successful_downloads


if __name__ == "__main__":
    download_all_music() 