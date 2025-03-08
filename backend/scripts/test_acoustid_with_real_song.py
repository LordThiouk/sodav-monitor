#!/usr/bin/env python
"""
Script pour tester l'API AcoustID avec un fichier audio réel.
Ce script permet de tester la détection d'un morceau réel avec l'API AcoustID.
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from backend.detection.audio_processor.external_services import AcoustIDService, get_fpcalc_path
from backend.utils.logging_config import setup_logging

# Configurer le logging
logger = setup_logging(__name__)

async def test_with_real_song(audio_file_path: str):
    """
    Tester l'API AcoustID avec un fichier audio réel.
    
    Args:
        audio_file_path: Chemin vers le fichier audio à tester
    """
    print(f"=== Test de l'API AcoustID avec le fichier {audio_file_path} ===")
    
    # Vérifier que le fichier existe
    if not os.path.exists(audio_file_path):
        print(f"❌ Le fichier {audio_file_path} n'existe pas")
        return False
    
    # Vérifier que fpcalc est disponible
    fpcalc_path = get_fpcalc_path()
    if not fpcalc_path:
        print("❌ fpcalc n'est pas disponible sur le système")
        print("   Veuillez installer fpcalc ou vérifier qu'il est dans le PATH")
        return False
    
    print(f"✅ fpcalc est disponible à : {fpcalc_path}")
    
    # Initialiser le service AcoustID
    acoustid_service = AcoustIDService()
    
    # Vérifier que la clé API est configurée
    if not acoustid_service.api_key:
        print("❌ La clé API AcoustID n'est pas configurée")
        print("   Veuillez configurer la clé API dans le fichier .env.development")
        return False
    
    print(f"✅ Clé API AcoustID configurée : {acoustid_service.api_key[:3]}...{acoustid_service.api_key[-3:]}")
    
    # Lire le fichier audio
    try:
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
        
        print(f"✅ Fichier audio lu : {len(audio_data)} octets")
        
        # Générer l'empreinte
        fingerprint_result = await acoustid_service._generate_fingerprint(audio_data)
        if not fingerprint_result:
            print("❌ Impossible de générer l'empreinte")
            return False
        
        fingerprint, duration = fingerprint_result
        print(f"✅ Empreinte générée : {fingerprint[:50]}... (longueur: {len(fingerprint)})")
        print(f"✅ Durée : {duration} secondes")
        
        # Détecter le morceau
        print("\nDétection du morceau avec AcoustID...")
        result = await acoustid_service.detect_track(audio_data)
        
        if result:
            print("\n✅ Morceau détecté !")
            print(f"   Titre : {result.get('title', 'Inconnu')}")
            print(f"   Artiste : {result.get('artist', 'Inconnu')}")
            print(f"   Album : {result.get('album', 'Inconnu')}")
            print(f"   ISRC : {result.get('isrc', 'Non disponible')}")
            print(f"   Label : {result.get('label', 'Non disponible')}")
            print(f"   Date de sortie : {result.get('release_date', 'Non disponible')}")
            print(f"   Confiance : {result.get('confidence', 0)}")
            return True
        else:
            print("\n❌ Aucun morceau détecté")
            print("   Cela peut être normal si le morceau n'est pas dans la base de données AcoustID")
            print("   Essayez avec un morceau plus connu ou populaire")
            return False
    
    except Exception as e:
        print(f"❌ Erreur lors du test : {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Tester l'API AcoustID avec un fichier audio réel")
    parser.add_argument("audio_file", help="Chemin vers le fichier audio à tester")
    args = parser.parse_args()
    
    # Exécuter le test
    asyncio.run(test_with_real_song(args.audio_file))

if __name__ == "__main__":
    main()