#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester l'API AcoustID
"""

import os
import sys
import json
import asyncio
import aiohttp
import tempfile
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Récupérer la clé API AcoustID
ACOUSTID_API_KEY = os.getenv('ACOUSTID_API_KEY')

def get_fpcalc_path():
    """Récupère le chemin vers l'exécutable fpcalc"""
    # Vérifier si fpcalc est dans le PATH
    try:
        result = subprocess.run(['which', 'fpcalc'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    
    # Vérifier les chemins spécifiques
    paths_to_check = [
        '/usr/local/bin/fpcalc',
        '/usr/bin/fpcalc',
        '/opt/local/bin/fpcalc',
        '/Users/cex/Desktop/sodav-monitor/backend/bin/fpcalc',
    ]
    
    for path in paths_to_check:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    
    return None

async def generate_fingerprint(audio_file_path):
    """Génère une empreinte digitale à partir d'un fichier audio"""
    fpcalc_path = get_fpcalc_path()
    
    if not fpcalc_path:
        print("Erreur: fpcalc non trouvé. Veuillez installer Chromaprint.")
        return None, 0
    
    print(f"Utilisation de fpcalc: {fpcalc_path}")
    
    try:
        # Exécuter fpcalc pour générer l'empreinte
        result = subprocess.run(
            [fpcalc_path, "-json", audio_file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"Erreur fpcalc: {result.stderr}")
            return None, 0
        
        # Analyser la sortie JSON
        data = json.loads(result.stdout)
        fingerprint = data.get("fingerprint")
        duration = data.get("duration", 0)
        
        print(f"Empreinte générée: {fingerprint[:50]}...")
        print(f"Durée: {duration} secondes")
        
        return fingerprint, duration
    
    except Exception as e:
        print(f"Erreur lors de la génération de l'empreinte: {e}")
        return None, 0

async def test_acoustid_api(fingerprint, duration):
    """Teste l'API AcoustID avec une empreinte digitale"""
    if not ACOUSTID_API_KEY:
        print("Erreur: ACOUSTID_API_KEY non définie dans le fichier .env")
        return False
    
    if not fingerprint or not duration:
        print("Erreur: Empreinte ou durée non valide")
        return False
    
    print(f"Test de l'API AcoustID avec la clé: {ACOUSTID_API_KEY}")
    
    # Préparer les paramètres pour l'API AcoustID
    params = {
        'client': ACOUSTID_API_KEY,
        'meta': 'recordings releasegroups releases tracks compress',
        'fingerprint': fingerprint,
        'duration': str(int(duration))
    }
    
    url = "https://api.acoustid.org/v2/lookup"
    print(f"Envoi de la requête à {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=params, timeout=30) as response:
                print(f"Statut de la réponse: {response.status}")
                
                # Lire la réponse
                response_text = await response.text()
                
                # Vérifier le code de statut
                if response.status != 200:
                    print(f"Erreur HTTP: {response.status}")
                    print(f"Réponse: {response_text}")
                    return False
                
                # Analyser la réponse JSON
                try:
                    data = json.loads(response_text)
                    print(f"Réponse JSON analysée avec succès")
                except json.JSONDecodeError as e:
                    print(f"Erreur lors de l'analyse de la réponse JSON: {e}")
                    print(f"Réponse: {response_text}")
                    return False
                
                # Vérifier si la réponse contient une erreur
                if data.get("status") != "ok":
                    error_message = data.get("error", {}).get("message", "Erreur inconnue")
                    print(f"Erreur de l'API AcoustID: {error_message}")
                    return False
                
                # Vérifier si des résultats ont été trouvés
                results = data.get("results", [])
                if not results:
                    print("Aucune correspondance trouvée dans la base de données AcoustID")
                    return True  # L'API a répondu correctement, mais aucune correspondance n'a été trouvée
                
                # Afficher les résultats
                print(f"Nombre de correspondances trouvées: {len(results)}")
                
                # Afficher le meilleur résultat
                best_result = max(results, key=lambda x: x.get("score", 0))
                score = best_result.get("score", 0)
                
                print(f"Meilleur score: {score}")
                
                if "recordings" in best_result and best_result["recordings"]:
                    recording = best_result["recordings"][0]
                    title = recording.get("title", "Titre inconnu")
                    
                    artist = "Artiste inconnu"
                    if "artists" in recording and recording["artists"]:
                        artist = recording["artists"][0].get("name", "Artiste inconnu")
                    
                    print(f"Piste détectée: {title} par {artist}")
                    
                    # Extraire l'ISRC si disponible
                    isrc = None
                    if "releases" in recording and recording["releases"]:
                        release = recording["releases"][0]
                        if "isrcs" in release and release["isrcs"]:
                            isrc = release["isrcs"][0]
                    
                    if isrc:
                        print(f"ISRC: {isrc}")
                    else:
                        print("ISRC non disponible")
                    
                    # Extraire le label si disponible
                    label = None
                    if "releases" in recording and recording["releases"]:
                        release = recording["releases"][0]
                        if "label-info" in release and release["label-info"]:
                            label_info = release["label-info"][0]
                            if "label" in label_info and "name" in label_info["label"]:
                                label = label_info["label"]["name"]
                    
                    if label:
                        print(f"Label: {label}")
                    else:
                        print("Label non disponible")
                
                return True
    
    except aiohttp.ClientError as e:
        print(f"Erreur client AcoustID: {e}")
        return False
    except asyncio.TimeoutError:
        print("Timeout de la requête AcoustID après 30 secondes")
        return False
    except Exception as e:
        print(f"Erreur lors du test de l'API AcoustID: {e}")
        return False

async def main():
    """Fonction principale"""
    if len(sys.argv) < 2:
        print("Usage: python test_acoustid.py <chemin_fichier_audio>")
        return 1
    
    audio_file_path = sys.argv[1]
    
    if not os.path.exists(audio_file_path):
        print(f"Erreur: Le fichier {audio_file_path} n'existe pas")
        return 1
    
    print(f"Test de l'API AcoustID avec le fichier: {audio_file_path}")
    
    # Générer l'empreinte digitale
    fingerprint, duration = await generate_fingerprint(audio_file_path)
    
    if not fingerprint:
        print("Erreur: Impossible de générer l'empreinte digitale")
        return 1
    
    # Tester l'API AcoustID
    success = await test_acoustid_api(fingerprint, duration)
    
    if success:
        print("Test de l'API AcoustID réussi!")
        return 0
    else:
        print("Test de l'API AcoustID échoué")
        return 1

if __name__ == "__main__":
    asyncio.run(main()) 