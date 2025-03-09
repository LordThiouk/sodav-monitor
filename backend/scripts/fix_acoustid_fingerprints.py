#!/usr/bin/env python3
"""
Script pour diagnostiquer et corriger les problèmes d'empreintes AcoustID.

Ce script vérifie que les empreintes générées par fpcalc sont correctement formatées
et peuvent être utilisées avec l'API AcoustID. Il teste également l'API AcoustID
avec différentes empreintes pour identifier les problèmes potentiels.

Usage:
    python fix_acoustid_fingerprints.py [--test_file path/to/audio.mp3]
"""

import os
import sys
import json
import asyncio
import argparse
import tempfile
import subprocess
import hashlib
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Importer les modules nécessaires
from backend.logs.log_manager import LogManager
from backend.detection.audio_processor.external_services import get_fpcalc_path, AcoustIDService
from backend.core.config import get_settings
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Initialiser le logging
log_manager = LogManager()
logger = log_manager.get_logger("acoustid_fix")

def log_info(message):
    """Log une information."""
    print(f"[INFO] {message}")
    logger.info(message)

def log_error(message):
    """Log une erreur."""
    print(f"[ERROR] {message}")
    logger.error(message)

def log_success(message):
    """Log un succès."""
    print(f"[SUCCESS] {message}")
    logger.info(message)

async def generate_fingerprint(audio_file_path: str) -> Tuple[Optional[str], Optional[float]]:
    """
    Génère une empreinte à partir d'un fichier audio en utilisant fpcalc.
    
    Args:
        audio_file_path: Chemin vers le fichier audio
        
    Returns:
        Tuple (empreinte, durée) ou (None, None) en cas d'erreur
    """
    try:
        # Vérifier si fpcalc est disponible
        fpcalc_path = get_fpcalc_path()
        if not fpcalc_path:
            log_error("fpcalc not available. Please install Chromaprint.")
            return None, None
        
        # Vérifier que le fichier existe
        if not os.path.exists(audio_file_path):
            log_error(f"File not found: {audio_file_path}")
            return None, None
        
        # Générer l'empreinte avec fpcalc
        log_info(f"Generating fingerprint with fpcalc for file: {audio_file_path}")
        result = subprocess.run(
            [fpcalc_path, "-json", audio_file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            log_error(f"fpcalc failed with error: {result.stderr}")
            return None, None
        
        # Analyser la sortie JSON
        try:
            fpcalc_output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            log_error(f"Error parsing fpcalc output: {str(e)}")
            log_error(f"fpcalc stdout: {result.stdout}")
            return None, None
        
        fingerprint = fpcalc_output.get("fingerprint")
        duration = fpcalc_output.get("duration")
        
        if not fingerprint or not duration:
            log_error("Failed to generate fingerprint or duration")
            log_error(f"fpcalc output: {fpcalc_output}")
            return None, None
        
        log_info(f"Generated fingerprint: {fingerprint[:20]}... (length: {len(fingerprint)})")
        log_info(f"Duration: {duration} seconds")
        
        return fingerprint, float(duration)
    
    except Exception as e:
        log_error(f"Error generating fingerprint: {str(e)}")
        import traceback
        log_error(f"Traceback: {traceback.format_exc()}")
        return None, None

async def test_acoustid_api(api_key: str, fingerprint: str, duration: float) -> Dict[str, Any]:
    """
    Teste l'API AcoustID avec une empreinte.
    
    Args:
        api_key: Clé API AcoustID
        fingerprint: Empreinte à tester
        duration: Durée en secondes
        
    Returns:
        Résultat de l'API ou dictionnaire d'erreur
    """
    try:
        # Préparer les paramètres de la requête
        params = {
            "client": api_key,
            "meta": "recordings releasegroups releases tracks compress",
            "fingerprint": fingerprint,
            "duration": str(int(duration))
        }
        
        # URL de l'API
        url = "https://api.acoustid.org/v2/lookup"
        
        # Log des détails de la requête
        log_info(f"Sending request to AcoustID: {url}")
        log_info(f"Fingerprint length: {len(fingerprint)}")
        log_info(f"Duration: {duration} seconds")
        
        # Envoyer la requête POST à AcoustID
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=params, timeout=30) as response:
                # Lire la réponse
                response_text = await response.text()
                
                # Vérifier le code de statut
                if response.status != 200:
                    log_error(f"AcoustID API returned status {response.status}: {response_text}")
                    return {"status": "error", "message": response_text}
                
                # Analyser la réponse JSON
                try:
                    response_data = json.loads(response_text)
                except json.JSONDecodeError as e:
                    log_error(f"Error parsing AcoustID response: {str(e)}")
                    log_error(f"Response text: {response_text}")
                    return {"status": "error", "message": "Invalid JSON response"}
                
                # Vérifier si la réponse contient une erreur
                if response_data.get("status") != "ok":
                    error_message = response_data.get("error", {}).get("message", "Unknown error")
                    log_error(f"AcoustID API returned error: {error_message}")
                    return {"status": "error", "message": error_message}
                
                # Vérifier si des résultats ont été trouvés
                results = response_data.get("results", [])
                if not results:
                    log_info("No matches found in AcoustID database")
                    return {"status": "ok", "message": "No matches found"}
                
                # Afficher les résultats
                log_success(f"Found {len(results)} matches in AcoustID database")
                for i, result in enumerate(results[:3]):  # Limiter à 3 résultats pour la lisibilité
                    score = result.get("score", 0)
                    recordings = result.get("recordings", [])
                    if recordings:
                        recording = recordings[0]
                        title = recording.get("title", "Unknown")
                        artists = recording.get("artists", [])
                        artist_name = artists[0].get("name", "Unknown") if artists else "Unknown"
                        log_success(f"Match {i+1}: {title} by {artist_name} (score: {score:.2f})")
                
                return {"status": "ok", "data": response_data}
    
    except aiohttp.ClientError as e:
        log_error(f"HTTP error: {str(e)}")
        return {"status": "error", "message": f"HTTP error: {str(e)}"}
    except Exception as e:
        log_error(f"Error testing AcoustID API: {str(e)}")
        import traceback
        log_error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}

async def test_with_audio_file(audio_file_path: str, api_key: str) -> None:
    """
    Teste l'API AcoustID avec un fichier audio.
    
    Args:
        audio_file_path: Chemin vers le fichier audio
        api_key: Clé API AcoustID
    """
    log_info(f"Testing AcoustID with file: {audio_file_path}")
    
    # Générer l'empreinte
    fingerprint, duration = await generate_fingerprint(audio_file_path)
    if not fingerprint or not duration:
        log_error("Failed to generate fingerprint. Cannot proceed with API test.")
        return
    
    # Tester l'API
    result = await test_acoustid_api(api_key, fingerprint, duration)
    
    if result.get("status") == "ok":
        if "data" in result:
            log_success("AcoustID API test successful!")
        else:
            log_info("AcoustID API test successful, but no matches found.")
    else:
        log_error(f"AcoustID API test failed: {result.get('message')}")

async def test_acoustid_service(audio_file_path: str, api_key: str) -> None:
    """
    Teste le service AcoustID intégré.
    
    Args:
        audio_file_path: Chemin vers le fichier audio
        api_key: Clé API AcoustID
    """
    log_info("Testing integrated AcoustID service...")
    
    # Créer une instance du service AcoustID
    acoustid_service = AcoustIDService(api_key=api_key)
    
    # Lire le fichier audio
    with open(audio_file_path, "rb") as f:
        audio_data = f.read()
    
    # Détecter la piste
    log_info("Calling detect_track method...")
    result = await acoustid_service.detect_track(audio_data)
    
    if result:
        log_success("AcoustID service test successful!")
        track = result.get("track", {})
        log_success(f"Detected track: {track.get('title', 'Unknown')} by {track.get('artist', 'Unknown')}")
        log_success(f"Album: {track.get('album', 'Unknown')}")
        log_success(f"ISRC: {track.get('isrc', 'Unknown')}")
    else:
        log_error("AcoustID service test failed: No track detected")

async def main():
    """Fonction principale."""
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Fix AcoustID fingerprint issues")
    parser.add_argument("--test_file", type=str, help="Path to audio file for testing")
    args = parser.parse_args()
    
    # Obtenir la clé API AcoustID
    settings = get_settings()
    api_key = settings.ACOUSTID_API_KEY
    
    if not api_key:
        log_error("ACOUSTID_API_KEY is not set. Please set it in your .env file.")
        return
    
    log_info(f"Using AcoustID API key: {api_key[:5]}...")
    
    # Vérifier si fpcalc est disponible
    fpcalc_path = get_fpcalc_path()
    if not fpcalc_path:
        log_error("fpcalc not found. Please install Chromaprint.")
        log_error("On Ubuntu/Debian: sudo apt-get install libchromaprint-tools")
        log_error("On macOS: brew install chromaprint")
        return
    
    log_success(f"Found fpcalc at: {fpcalc_path}")
    
    # Si un fichier de test est spécifié, l'utiliser
    if args.test_file:
        if not os.path.exists(args.test_file):
            log_error(f"Test file not found: {args.test_file}")
            return
        
        await test_with_audio_file(args.test_file, api_key)
        await test_acoustid_service(args.test_file, api_key)
    else:
        log_info("No test file specified. Please use --test_file to specify an audio file.")
        log_info("Example: python fix_acoustid_fingerprints.py --test_file path/to/audio.mp3")

if __name__ == "__main__":
    asyncio.run(main()) 