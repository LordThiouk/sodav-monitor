#!/usr/bin/env python
"""
Script pour télécharger un morceau de test à partir d'une source publique.
Ce script télécharge un morceau libre de droits pour tester l'API AcoustID.
"""

import os
import sys
import argparse
import requests
from pathlib import Path

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from backend.utils.logging_config import setup_logging

# Configurer le logging
logger = setup_logging(__name__)

# Liste de morceaux libres de droits connus
FREE_SONGS = [
    {
        "name": "Gymnopedie No. 1",
        "artist": "Erik Satie",
        "url": "https://archive.org/download/ErikSatieGymnopedieNo.1/Erik%20Satie%20-%20Gymnopedie%20No.%201.mp3",
        "filename": "gymnopedie_no_1.mp3"
    },
    {
        "name": "Moonlight Sonata",
        "artist": "Ludwig van Beethoven",
        "url": "https://archive.org/download/BeethovenMoonlightSonata_201611/Beethoven-Moonlight-Sonata.mp3",
        "filename": "moonlight_sonata.mp3"
    },
    {
        "name": "Clair de Lune",
        "artist": "Claude Debussy",
        "url": "https://archive.org/download/ClairDeLune_655/Debussy-ClairDeLune.mp3",
        "filename": "clair_de_lune.mp3"
    }
]

def download_song(song_index: int, output_dir: str):
    """
    Télécharger un morceau de test.
    
    Args:
        song_index: Index du morceau à télécharger dans la liste FREE_SONGS
        output_dir: Répertoire de sortie pour le fichier téléchargé
    
    Returns:
        Chemin vers le fichier téléchargé
    """
    # Vérifier l'index
    if song_index < 0 or song_index >= len(FREE_SONGS):
        print(f"❌ Index de morceau invalide. Choisissez un index entre 0 et {len(FREE_SONGS) - 1}")
        return None
    
    # Récupérer les informations du morceau
    song = FREE_SONGS[song_index]
    print(f"=== Téléchargement de {song['name']} par {song['artist']} ===")
    
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    # Chemin de sortie
    output_path = os.path.join(output_dir, song["filename"])
    
    # Vérifier si le fichier existe déjà
    if os.path.exists(output_path):
        print(f"✅ Le fichier existe déjà : {output_path}")
        return output_path
    
    # Télécharger le fichier
    try:
        print(f"Téléchargement depuis {song['url']}...")
        response = requests.get(song["url"], stream=True)
        response.raise_for_status()
        
        # Écrire le fichier
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Téléchargement terminé : {output_path}")
        return output_path
    
    except Exception as e:
        print(f"❌ Erreur lors du téléchargement : {str(e)}")
        return None

def list_songs():
    """
    Afficher la liste des morceaux disponibles.
    """
    print("=== Morceaux disponibles ===")
    for i, song in enumerate(FREE_SONGS):
        print(f"{i}: {song['name']} par {song['artist']}")

def main():
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Télécharger un morceau de test")
    parser.add_argument("--list", action="store_true", help="Afficher la liste des morceaux disponibles")
    parser.add_argument("--index", type=int, default=0, help="Index du morceau à télécharger")
    parser.add_argument("--output-dir", default="tests/data/audio", help="Répertoire de sortie")
    args = parser.parse_args()
    
    # Afficher la liste des morceaux
    if args.list:
        list_songs()
        return
    
    # Télécharger le morceau
    output_dir = os.path.join(project_root, "backend", args.output_dir)
    download_song(args.index, output_dir)

if __name__ == "__main__":
    main() 