#!/usr/bin/env python
"""
Script de test pour l'API AcoustID.
Ce script teste différentes configurations d'empreintes digitales et de requêtes.
"""

import os
import sys
import json
import asyncio
import aiohttp
import subprocess
import tempfile
import shutil
from pathlib import Path

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from backend.detection.audio_processor.external_services import get_fpcalc_path
from backend.utils.logging_config import setup_logging

# Configurer le logging
logger = setup_logging(__name__)

# Charger la clé API AcoustID depuis le fichier .env.development
def load_api_key():
    env_path = Path(project_root) / ".env.development"
    if not env_path.exists():
        print(f"Fichier .env.development introuvable: {env_path}")
        return None
        
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("ACOUSTID_API_KEY="):
                api_key = line.strip().split("=", 1)[1]
                if api_key.startswith('"') and api_key.endswith('"'):
                    api_key = api_key[1:-1]
                return api_key
    
    print("Clé API AcoustID non trouvée dans .env.development")
    return None

# Créer un fichier audio de test
def create_test_audio_file():
    # Chercher un fichier audio existant dans le répertoire de test
    test_dir = Path(project_root) / "backend" / "tests" / "data"
    if test_dir.exists():
        for file in test_dir.glob("*.mp3"):
            print(f"Utilisation du fichier audio de test existant: {file}")
            return str(file)
    
    # Chercher un fichier audio dans le répertoire du projet
    for root, dirs, files in os.walk(project_root):
        for file in files:
            if file.endswith(('.mp3', '.wav', '.ogg')):
                file_path = os.path.join(root, file)
                print(f"Utilisation du fichier audio trouvé: {file_path}")
                return file_path
    
    # Si aucun fichier audio n'est trouvé, créer un fichier temporaire
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
        temp_file_path = temp_file.name
    
    # Essayer de copier un fichier MP3 connu
    try:
        # Chercher un fichier MP3 dans le répertoire Windows
        windows_media_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Media')
        if os.path.exists(windows_media_dir):
            for file in os.listdir(windows_media_dir):
                if file.endswith('.wav'):
                    source_file = os.path.join(windows_media_dir, file)
                    shutil.copy(source_file, temp_file_path)
                    print(f"Fichier audio copié depuis {source_file} vers {temp_file_path}")
                    return temp_file_path
    except Exception as e:
        print(f"Erreur lors de la copie du fichier audio: {e}")
    
    # Si tout échoue, créer un fichier MP3 minimal
    try:
        with open(temp_file_path, "wb") as f:
            # Écrire un en-tête MP3 minimal et quelques données
            f.write(b"\xFF\xFB\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
            # Ajouter des données pour éviter les erreurs
            for i in range(1024):
                f.write(b"\xFF\xFB\x90\x44\x00\x00\x00\x00")
        
        print(f"Fichier audio minimal créé: {temp_file_path}")
        return temp_file_path
    except Exception as e:
        print(f"Erreur lors de la création du fichier audio minimal: {e}")
        return None

# Générer une empreinte à partir d'un fichier audio
def generate_fingerprint(audio_file_path):
    fpcalc_path = get_fpcalc_path()
    if not fpcalc_path:
        print("fpcalc n'est pas disponible, impossible de générer une empreinte")
        return None, None
    
    print(f"Utilisation de fpcalc: {fpcalc_path}")
    print(f"Fichier audio: {audio_file_path}")
    print(f"Le fichier existe: {os.path.exists(audio_file_path)}")
    print(f"Taille du fichier: {os.path.getsize(audio_file_path)} octets")
        
    try:
        # Générer l'empreinte avec fpcalc
        print(f"Génération de l'empreinte pour le fichier: {audio_file_path}")
        result = subprocess.run(
            [fpcalc_path, "-json", audio_file_path],
            capture_output=True,
            text=True
        )
        
        print(f"Code de retour: {result.returncode}")
        print(f"Sortie standard: {result.stdout[:200]}...")
        print(f"Erreur standard: {result.stderr}")
        
        if result.returncode != 0:
            print(f"Erreur lors de la génération de l'empreinte: {result.stderr}")
            return None, None
        
        # Analyser la sortie JSON
        try:
            fpcalc_output = json.loads(result.stdout)
            fingerprint = fpcalc_output.get("fingerprint")
            duration = fpcalc_output.get("duration")
            
            if not fingerprint or not duration:
                print("Impossible de générer l'empreinte ou la durée")
                return None, None
            
            print(f"Empreinte générée: {fingerprint[:50]}... (longueur: {len(fingerprint)})")
            print(f"Durée: {duration} secondes")
            
            return fingerprint, duration
            
        except json.JSONDecodeError as e:
            print(f"Erreur lors de l'analyse de la sortie JSON: {e}")
            return None, None
            
    except Exception as e:
        print(f"Erreur lors de la génération de l'empreinte: {e}")
        return None, None

# Tester l'API AcoustID avec une empreinte générée
async def test_acoustid_api_with_real_fingerprint():
    api_key = load_api_key()
    if not api_key:
        print("Impossible de charger la clé API AcoustID")
        return False
    
    print(f"Clé API AcoustID: {api_key[:3]}...{api_key[-3:]}")
    
    # Créer un fichier audio de test
    audio_file_path = create_test_audio_file()
    if not audio_file_path:
        print("Impossible de créer un fichier audio de test")
        return False
    
    try:
        # Générer l'empreinte
        fingerprint, duration = generate_fingerprint(audio_file_path)
        if not fingerprint or not duration:
            print("Impossible de générer l'empreinte")
            return False
        
        # Tester l'API avec l'empreinte générée
        # URL de base de l'API AcoustID
        base_url = "https://api.acoustid.org/v2/lookup"
        
        # Tester avec différentes longueurs d'empreinte
        fingerprint_lengths = [
            len(fingerprint),  # Empreinte complète
            min(len(fingerprint), 1000),  # Empreinte tronquée à 1000 caractères
            min(len(fingerprint), 500),   # Empreinte tronquée à 500 caractères
            min(len(fingerprint), 200)    # Empreinte tronquée à 200 caractères
        ]
        
        for length in fingerprint_lengths:
            truncated_fingerprint = fingerprint[:length]
            print(f"\nTest avec empreinte tronquée (longueur: {length})")
            
            # Préparer les paramètres de la requête
            params = {
                "client": api_key,
                "meta": "recordings",
                "fingerprint": truncated_fingerprint,
                "duration": str(int(float(duration)))
            }
            
            async with aiohttp.ClientSession() as session:
                # Tester avec POST
                print("Test avec méthode POST...")
                async with session.post(base_url, data=params, timeout=30) as response:
                    print(f"Statut de la réponse: {response.status}")
                    response_text = await response.text()
                    print(f"Réponse: {response_text[:200]}...")
                    
                    if response.status == 200:
                        try:
                            data = json.loads(response_text)
                            if data.get("status") == "ok":
                                print("✅ Test réussi avec POST")
                            else:
                                print(f"❌ Erreur dans la réponse: {data.get('error', {}).get('message', 'Erreur inconnue')}")
                        except json.JSONDecodeError:
                            print("❌ Erreur de décodage JSON")
                    else:
                        print(f"❌ Erreur HTTP: {response.status}")
                
                # Tester avec GET
                print("\nTest avec méthode GET...")
                # Construire l'URL avec les paramètres (mais tronquer l'empreinte pour l'URL)
                get_params = params.copy()
                if len(get_params["fingerprint"]) > 500:
                    get_params["fingerprint"] = get_params["fingerprint"][:500]
                    print(f"Empreinte tronquée à 500 caractères pour GET")
                
                query_params = "&".join([f"{k}={v}" for k, v in get_params.items()])
                url = f"{base_url}?{query_params}"
                async with session.get(url, timeout=30) as response:
                    print(f"Statut de la réponse: {response.status}")
                    response_text = await response.text()
                    print(f"Réponse: {response_text[:200]}...")
                    
                    if response.status == 200:
                        try:
                            data = json.loads(response_text)
                            if data.get("status") == "ok":
                                print("✅ Test réussi avec GET")
                            else:
                                print(f"❌ Erreur dans la réponse: {data.get('error', {}).get('message', 'Erreur inconnue')}")
                        except json.JSONDecodeError:
                            print("❌ Erreur de décodage JSON")
                    else:
                        print(f"❌ Erreur HTTP: {response.status}")
    
    finally:
        # Supprimer le fichier temporaire si nécessaire
        if audio_file_path and audio_file_path.startswith(tempfile.gettempdir()):
            try:
                os.unlink(audio_file_path)
                print(f"Fichier temporaire supprimé: {audio_file_path}")
            except:
                pass

async def main():
    print("=== Test de l'API AcoustID avec une empreinte réelle ===")
    await test_acoustid_api_with_real_fingerprint()

if __name__ == "__main__":
    asyncio.run(main())