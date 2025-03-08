#!/usr/bin/env python
"""
Script simplifié pour tester la recherche avec MusicBrainz.
"""

import os
import sys
import asyncio
import logging
import musicbrainzngs
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_env_file(env_path):
    """Charge les variables d'environnement depuis un fichier .env."""
    if not env_path.exists():
        logger.error(f"Environment file not found: {env_path}")
        return {}
    
    env_vars = {}
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key] = value
    
    return env_vars

async def search_musicbrainz(artist, title):
    """
    Recherche une piste dans MusicBrainz.
    
    Args:
        artist: Nom de l'artiste
        title: Titre de la piste
        
    Returns:
        Dict contenant les informations de la piste ou None si aucune correspondance
    """
    try:
        logger.info(f"Searching for track: {title} by {artist}")
        
        # Initialiser MusicBrainz
        musicbrainzngs.set_useragent(
            "SODAV Monitor",
            "1.0",
            "https://sodav.sn"
        )
        
        # Rechercher la piste dans MusicBrainz
        query = f"recording:\"{title}\" AND artist:\"{artist}\""
        logger.info(f"MusicBrainz query: {query}")
        
        result = musicbrainzngs.search_recordings(query=query, limit=5)
        
        if not result or not result.get('recording-list'):
            logger.info(f"No results found for {title} by {artist}")
            return None
        
        # Extraire les informations de la première piste trouvée
        recording = result['recording-list'][0]
        
        logger.info(f"Found recording: {recording.get('title')} by {recording.get('artist-credit-phrase')}")
        
        # Construire le résultat
        return {
            "title": recording.get('title', title),
            "artist": recording.get('artist-credit-phrase', artist),
            "album": recording.get('release-list', [{}])[0].get('title', "Unknown Album") if recording.get('release-list') else "Unknown Album",
            "confidence": 0.7,  # Valeur par défaut pour les recherches par métadonnées
            "source": "musicbrainz",
            "id": recording.get('id', "")
        }
        
    except musicbrainzngs.WebServiceError as e:
        logger.error(f"MusicBrainz API error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in MusicBrainz search: {str(e)}")
        return None

async def test_musicbrainz_search():
    """Teste la recherche avec MusicBrainz."""
    # Liste de pistes à tester
    test_tracks = [
        {"artist": "Michael Jackson", "title": "Thriller"},
        {"artist": "Queen", "title": "Bohemian Rhapsody"},
        {"artist": "The Beatles", "title": "Hey Jude"},
        {"artist": "Youssou N'Dour", "title": "7 Seconds"},
        {"artist": "Baaba Maal", "title": "African Woman"}
    ]
    
    success_count = 0
    
    for track in test_tracks:
        artist = track["artist"]
        title = track["title"]
        
        logger.info(f"Testing search for: {title} by {artist}")
        
        result = await search_musicbrainz(artist, title)
        
        if result:
            logger.info(f"Search successful: {result}")
            success_count += 1
        else:
            logger.warning(f"No result found for: {title} by {artist}")
    
    logger.info(f"Test completed: {success_count}/{len(test_tracks)} tracks successfully found")
    
    return success_count > 0

async def main():
    """Fonction principale."""
    logger.info("Starting MusicBrainz search test")
    
    result = await test_musicbrainz_search()
    
    if result:
        logger.info("MusicBrainz search test passed successfully")
    else:
        logger.warning("MusicBrainz search test failed")

if __name__ == "__main__":
    asyncio.run(main()) 