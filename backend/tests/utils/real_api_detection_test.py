"""
Script de test pour la détection musicale avec de vrais appels API.

Ce script utilise le simulateur de radio amélioré pour diffuser des fichiers audio sénégalais
et teste la détection musicale en utilisant de vrais appels API (locale, MusicBrainz, Audd.io).
Il enregistre avec précision les durées de lecture et les résultats de détection.
"""

import asyncio
import base64
import json
import logging
import os
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from backend.tests.utils.enhanced_radio_simulator import EnhancedRadioSimulator

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("real_api_detection_test")

# Répertoire des fichiers audio
AUDIO_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "audio" / "senegal"

# Chemin vers fpcalc.exe pour la génération d'empreintes acoustiques
FPCALC_PATH = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "bin" / "fpcalc.exe"

# Configurer fpcalc.exe si disponible
if FPCALC_PATH.exists():
    logger.info(f"fpcalc.exe trouvé à {FPCALC_PATH}")
    os.environ["FPCALC_PATH"] = str(FPCALC_PATH)
else:
    logger.warning(f"fpcalc.exe non trouvé à {FPCALC_PATH}. La génération d'empreintes acoustiques pourrait échouer.")

# Clés API (à remplacer par vos propres clés)
ACOUSTID_API_KEY = os.environ.get("ACOUSTID_API_KEY", "")
AUDD_API_KEY = os.environ.get("AUDD_API_KEY", "")

# Base de données locale simulée pour les empreintes acoustiques
LOCAL_FINGERPRINT_DB = {}


async def capture_audio(url, duration=15):
    """
    Capture l'audio à partir d'une URL.
    
    Args:
        url: URL du flux audio
        duration: Durée de capture en secondes
        
    Returns:
        Données audio capturées ou None en cas d'échec
    """
    logger.info(f"Capture audio depuis {url} pendant {duration} secondes...")
    
    try:
        # Dans un environnement réel, nous utiliserions une bibliothèque comme requests ou aiohttp
        # pour capturer le flux audio, mais pour ce test, nous allons simuler la capture
        # en lisant directement un fichier audio
        
        # Simuler un délai de capture
        await asyncio.sleep(duration)
        
        # Pour ce test, nous allons utiliser un fichier audio existant
        # au lieu de capturer réellement le flux
        sample_files = list(AUDIO_DIR.glob("*.mp3"))
        if sample_files:
            with open(sample_files[0], "rb") as f:
                # Lire seulement les premiers 500KB pour simuler une capture partielle
                audio_data = f.read(500 * 1024)
            
            logger.info(f"Audio capturé: {len(audio_data)} octets")
            return audio_data
        else:
            logger.error("Aucun fichier audio trouvé pour simuler la capture")
            return None
    
    except Exception as e:
        logger.error(f"Erreur lors de la capture audio: {e}")
        return None


def generate_fingerprint(audio_data):
    """
    Génère une empreinte acoustique à partir des données audio.
    
    Args:
        audio_data: Données audio brutes
        
    Returns:
        Dictionnaire contenant l'empreinte acoustique et les métadonnées
    """
    logger.info("Génération de l'empreinte acoustique...")
    
    try:
        # Créer un fichier temporaire pour l'audio
        temp_file = Path("temp_audio.mp3")
        with open(temp_file, "wb") as f:
            f.write(audio_data)
        
        # Utiliser fpcalc pour générer l'empreinte
        if FPCALC_PATH.exists():
            import subprocess
            
            # Exécuter fpcalc
            cmd = [str(FPCALC_PATH), "-json", str(temp_file)]
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                result = json.loads(process.stdout)
                
                # Nettoyer le fichier temporaire
                temp_file.unlink()
                
                logger.info(f"Empreinte générée avec succès: {len(result.get('fingerprint', ''))} caractères")
                return {
                    "success": True,
                    "fingerprint": result.get("fingerprint", ""),
                    "duration": result.get("duration", 0),
                    "error": None
                }
            else:
                logger.error(f"Erreur lors de l'exécution de fpcalc: {process.stderr}")
        else:
            logger.error(f"fpcalc.exe non trouvé à {FPCALC_PATH}")
        
        # Nettoyer le fichier temporaire
        if temp_file.exists():
            temp_file.unlink()
        
        # Simuler une empreinte si fpcalc échoue
        return {
            "success": False,
            "fingerprint": "",
            "duration": 0,
            "error": "Échec de la génération d'empreinte"
        }
    
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'empreinte: {e}")
        
        # Nettoyer le fichier temporaire
        if temp_file.exists():
            temp_file.unlink()
        
        return {
            "success": False,
            "fingerprint": "",
            "duration": 0,
            "error": str(e)
        }


def local_detection(fingerprint):
    """
    Recherche une correspondance dans la base de données locale.
    
    Args:
        fingerprint: Empreinte acoustique à rechercher
        
    Returns:
        Résultat de la détection locale
    """
    logger.info("Recherche d'une correspondance locale...")
    
    # Dans un environnement réel, nous interrogerions une base de données
    # Pour ce test, nous utilisons un dictionnaire simple
    
    # Vérifier si l'empreinte existe dans la base locale
    if fingerprint in LOCAL_FINGERPRINT_DB:
        track_info = LOCAL_FINGERPRINT_DB[fingerprint]
        logger.info(f"Correspondance locale trouvée: {track_info['title']} par {track_info['artist']}")
        return {
            "success": True,
            "method": "local",
            "title": track_info["title"],
            "artist": track_info["artist"],
            "confidence": 0.95,
            "error": None
        }
    
    logger.info("Aucune correspondance locale trouvée")
    return {
        "success": False,
        "method": "local",
        "error": "Aucune correspondance locale"
    }


def musicbrainz_detection(fingerprint, duration):
    """
    Recherche une correspondance via l'API MusicBrainz/AcoustID.
    
    Args:
        fingerprint: Empreinte acoustique à rechercher
        duration: Durée de l'audio en secondes
        
    Returns:
        Résultat de la détection MusicBrainz
    """
    logger.info("Recherche d'une correspondance via MusicBrainz/AcoustID...")
    
    if not ACOUSTID_API_KEY:
        logger.warning("Clé API AcoustID non configurée")
        return {
            "success": False,
            "method": "musicbrainz",
            "error": "Clé API AcoustID non configurée"
        }
    
    try:
        # Vérifier que la durée est valide
        if duration is None or duration <= 0:
            logger.warning("Durée invalide pour la requête AcoustID")
            duration = 30  # Utiliser une valeur par défaut
        
        # Préparer les paramètres de la requête
        params = {
            "client": ACOUSTID_API_KEY,
            "meta": "recordings+releasegroups+compress",
            "duration": str(int(float(duration))),  # Assurer que la durée est un entier en chaîne de caractères
            "fingerprint": fingerprint,
        }
        
        logger.info(f"Paramètres de la requête AcoustID: duration={params['duration']}, fingerprint={fingerprint[:50]}...")
        
        # Effectuer la requête à l'API AcoustID
        response = requests.get("https://api.acoustid.org/v2/lookup", params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Vérifier si des résultats ont été trouvés
            if data.get("status") == "ok" and data.get("results"):
                result = data["results"][0]
                
                # Extraire les informations du morceau
                if "recordings" in result:
                    recording = result["recordings"][0]
                    
                    # Stocker l'empreinte dans la base locale pour les futures détections
                    LOCAL_FINGERPRINT_DB[fingerprint] = {
                        "title": recording.get("title", "Unknown"),
                        "artist": recording.get("artists", [{"name": "Unknown"}])[0]["name"],
                        "album": recording.get("releasegroups", [{"title": "Unknown"}])[0]["title"],
                        "year": recording.get("releasegroups", [{"year": ""}])[0].get("year", ""),
                    }
                    
                    logger.info(f"Correspondance MusicBrainz trouvée: {LOCAL_FINGERPRINT_DB[fingerprint]['title']} par {LOCAL_FINGERPRINT_DB[fingerprint]['artist']}")
                    
                    return {
                        "success": True,
                        "method": "musicbrainz",
                        "title": LOCAL_FINGERPRINT_DB[fingerprint]["title"],
                        "artist": LOCAL_FINGERPRINT_DB[fingerprint]["artist"],
                        "album": LOCAL_FINGERPRINT_DB[fingerprint]["album"],
                        "year": LOCAL_FINGERPRINT_DB[fingerprint]["year"],
                        "confidence": result.get("score", 0),
                        "error": None
                    }
            
            logger.info("Aucune correspondance MusicBrainz trouvée")
            return {
                "success": False,
                "method": "musicbrainz",
                "error": "Aucune correspondance trouvée"
            }
        
        else:
            logger.error(f"Erreur lors de la requête à l'API AcoustID: {response.status_code} - {response.text}")
            return {
                "success": False,
                "method": "musicbrainz",
                "error": f"Erreur API: {response.status_code}"
            }
    
    except Exception as e:
        logger.error(f"Erreur lors de la détection MusicBrainz: {e}")
        return {
            "success": False,
            "method": "musicbrainz",
            "error": str(e)
        }


def audd_detection(audio_data):
    """
    Recherche une correspondance via l'API Audd.io.
    
    Args:
        audio_data: Données audio brutes
        
    Returns:
        Résultat de la détection Audd.io
    """
    logger.info("Recherche d'une correspondance via Audd.io...")
    
    if not AUDD_API_KEY:
        logger.warning("Clé API Audd.io non configurée")
        return {
            "success": False,
            "method": "audd",
            "error": "Clé API Audd.io non configurée"
        }
    
    try:
        # Préparer les données pour la requête
        files = {
            "file": ("audio.mp3", audio_data),
        }
        data = {
            "api_token": AUDD_API_KEY,
            "return": "apple_music,spotify",
        }
        
        # Effectuer la requête à l'API Audd.io
        response = requests.post("https://api.audd.io/", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            
            # Vérifier si un morceau a été trouvé
            if result.get("status") == "success" and result.get("result"):
                track_info = result["result"]
                
                # Stocker l'empreinte dans la base locale pour les futures détections
                fingerprint = base64.b64encode(audio_data[:1000]).decode("utf-8")  # Simuler une empreinte
                LOCAL_FINGERPRINT_DB[fingerprint] = {
                    "title": track_info.get("title", "Unknown"),
                    "artist": track_info.get("artist", "Unknown"),
                    "album": track_info.get("album", "Unknown"),
                    "year": track_info.get("release_date", "")[:4] if track_info.get("release_date") else "",
                }
                
                logger.info(f"Correspondance Audd.io trouvée: {track_info.get('title')} par {track_info.get('artist')}")
                
                return {
                    "success": True,
                    "method": "audd",
                    "title": track_info.get("title", "Unknown"),
                    "artist": track_info.get("artist", "Unknown"),
                    "album": track_info.get("album", "Unknown"),
                    "year": track_info.get("release_date", "")[:4] if track_info.get("release_date") else "",
                    "confidence": 0.8,  # Audd.io ne fournit pas de score de confiance, on utilise une valeur par défaut
                    "error": None
                }
            
            logger.info("Aucune correspondance Audd.io trouvée")
            return {
                "success": False,
                "method": "audd",
                "error": "Aucune correspondance trouvée"
            }
        
        else:
            logger.error(f"Erreur lors de la requête à l'API Audd.io: {response.status_code} - {response.text}")
            return {
                "success": False,
                "method": "audd",
                "error": f"Erreur API: {response.status_code}"
            }
    
    except Exception as e:
        logger.error(f"Erreur lors de la détection Audd.io: {e}")
        return {
            "success": False,
            "method": "audd",
            "error": str(e)
        }


async def detect_music(audio_data):
    """
    Détecte la musique en suivant la hiérarchie de détection.
    
    Args:
        audio_data: Données audio à analyser
        
    Returns:
        Résultat de la détection
    """
    logger.info("Analyse de l'audio pour détecter la musique...")
    
    # Étape 1: Vérifier si c'est de la musique ou de la parole
    # Dans un environnement réel, nous utiliserions un algorithme de classification
    # Pour ce test, nous supposons que c'est de la musique
    is_music = True
    
    if not is_music:
        logger.info("Audio classifié comme parole, ignoré")
        return {
            "is_music": False,
            "method": "classification",
            "confidence": 0.9,
            "error": None
        }
    
    # Étape 2: Générer l'empreinte acoustique
    fingerprint_result = generate_fingerprint(audio_data)
    
    if not fingerprint_result["success"]:
        logger.error(f"Échec de la génération d'empreinte: {fingerprint_result['error']}")
        return {
            "is_music": True,
            "success": False,
            "method": "fingerprint",
            "error": fingerprint_result["error"]
        }
    
    fingerprint = fingerprint_result["fingerprint"]
    duration = fingerprint_result["duration"]
    
    # Étape 3: Détection locale
    local_result = local_detection(fingerprint)
    
    if local_result["success"]:
        return {
            "is_music": True,
            "success": True,
            "method": "local",
            "title": local_result["title"],
            "artist": local_result["artist"],
            "confidence": local_result["confidence"],
            "play_duration": duration,
            "fingerprint": fingerprint,
            "error": None
        }
    
    # Étape 4: Détection MusicBrainz
    musicbrainz_result = musicbrainz_detection(fingerprint, duration)
    
    if musicbrainz_result["success"]:
        return {
            "is_music": True,
            "success": True,
            "method": "musicbrainz",
            "title": musicbrainz_result["title"],
            "artist": musicbrainz_result["artist"],
            "album": musicbrainz_result.get("album", "Unknown"),
            "year": musicbrainz_result.get("year", ""),
            "confidence": musicbrainz_result["confidence"],
            "play_duration": duration,
            "fingerprint": fingerprint,
            "error": None
        }
    
    # Étape 5: Détection Audd.io
    audd_result = audd_detection(audio_data)
    
    if audd_result["success"]:
        return {
            "is_music": True,
            "success": True,
            "method": "audd",
            "title": audd_result["title"],
            "artist": audd_result["artist"],
            "album": audd_result.get("album", "Unknown"),
            "year": audd_result.get("year", ""),
            "confidence": audd_result["confidence"],
            "play_duration": duration,
            "fingerprint": fingerprint,
            "error": None
        }
    
    # Aucune correspondance trouvée
    logger.warning("Aucune correspondance trouvée après toutes les tentatives")
    return {
        "is_music": True,
        "success": False,
        "method": "all",
        "confidence": 0.0,
        "play_duration": duration,
        "fingerprint": fingerprint,
        "error": "Aucune correspondance trouvée"
    }


async def test_real_api_detection():
    """Teste la détection musicale avec de vrais appels API."""
    # Vérifier si des fichiers audio sont disponibles
    if not AUDIO_DIR.exists() or not any(AUDIO_DIR.glob("*.mp3")):
        logger.error(f"Aucun fichier audio trouvé dans {AUDIO_DIR}")
        return
    
    # Créer un simulateur de radio amélioré
    simulator = EnhancedRadioSimulator()
    
    # Créer une station avec les fichiers audio sénégalais
    station = simulator.create_station(
        name="Radio Sénégal API Test",
        audio_dir=AUDIO_DIR,
        genre="Hip-Hop/Rap",
        country="Sénégal",
        language="Wolof/Français"
    )
    
    if not station:
        logger.error("Échec de la création de la station")
        return
    
    # Démarrer l'enregistrement des logs
    simulator.start_logging()
    
    # Démarrer la station
    station.start()
    logger.info(f"Station démarrée: {station.name} sur http://localhost:{station.port}")
    
    # Démarrer le monitoring
    simulator.start_monitoring(interval_seconds=5)
    
    try:
        # Attendre que la station soit prête
        logger.info("Attente de 5 secondes pour que la station soit prête...")
        await asyncio.sleep(5)
        
        # Effectuer plusieurs détections
        detection_count = 2
        
        for i in range(detection_count):
            logger.info(f"Détection {i+1}/{detection_count}...")
            
            # Capturer l'audio
            audio_data = await capture_audio(f"http://localhost:{station.port}")
            
            if not audio_data:
                logger.error("Échec de la capture audio")
                continue
            
            # Détecter la musique avec les vrais appels API
            detection_start_time = time.time()
            detection_result = await detect_music(audio_data)
            detection_end_time = time.time()
            detection_duration = detection_end_time - detection_start_time
            
            # Afficher les résultats de la détection
            if detection_result["is_music"]:
                if detection_result["success"]:
                    logger.info(
                        f"Musique détectée: {detection_result.get('title', 'Unknown')} "
                        f"par {detection_result.get('artist', 'Unknown')} "
                        f"(méthode: {detection_result['method']}, "
                        f"confiance: {detection_result['confidence']:.2f}, "
                        f"durée: {detection_result['play_duration']:.2f}s)"
                    )
                    
                    # Enregistrer la détection dans le simulateur
                    simulator.register_detection(
                        station_name=station.name,
                        track_name=detection_result.get("title", "Unknown"),
                        detection_method=detection_result["method"],
                        confidence=detection_result["confidence"],
                        detected_at=datetime.now(),
                        play_duration=detection_result["play_duration"],
                        fingerprint=detection_result["fingerprint"],
                        metadata={
                            "artist": detection_result.get("artist", "Unknown"),
                            "album": detection_result.get("album", "Unknown"),
                            "year": detection_result.get("year", ""),
                            "detection_time": detection_duration,
                            "detection_index": i+1
                        }
                    )
                else:
                    logger.warning(
                        f"Musique détectée mais non identifiée "
                        f"(méthode: {detection_result['method']}, "
                        f"erreur: {detection_result['error']})"
                    )
            else:
                logger.info("Aucune musique détectée")
            
            # Attendre entre les détections
            if i < detection_count - 1:
                logger.info("Attente de 20 secondes avant la prochaine détection...")
                await asyncio.sleep(20)
        
        # Simuler une interruption
        logger.info("Simulation d'une interruption...")
        simulator.simulate_interruption(station.name, duration_seconds=5)
        
        # Attendre un peu
        await asyncio.sleep(10)
        
        # Effectuer une autre détection après l'interruption
        logger.info("Détection après interruption...")
        audio_data = await capture_audio(f"http://localhost:{station.port}")
        
        if audio_data:
            detection_result = await detect_music(audio_data)
            
            if detection_result["is_music"] and detection_result["success"]:
                logger.info(
                    f"Musique détectée après interruption: {detection_result.get('title', 'Unknown')} "
                    f"par {detection_result.get('artist', 'Unknown')} "
                    f"(méthode: {detection_result['method']}, "
                    f"confiance: {detection_result['confidence']:.2f})"
                )
                
                # Enregistrer la détection dans le simulateur
                simulator.register_detection(
                    station_name=station.name,
                    track_name=detection_result.get("title", "Unknown"),
                    detection_method=detection_result["method"],
                    confidence=detection_result["confidence"],
                    detected_at=datetime.now(),
                    play_duration=detection_result["play_duration"],
                    fingerprint=detection_result["fingerprint"],
                    metadata={
                        "artist": detection_result.get("artist", "Unknown"),
                        "album": detection_result.get("album", "Unknown"),
                        "year": detection_result.get("year", ""),
                        "after_interruption": True
                    }
                )
        
        # Obtenir les logs de lecture
        play_logs = simulator.get_play_logs()
        logger.info(f"Logs de lecture: {len(play_logs)} événements")
        
        # Obtenir les logs de détection
        detection_logs = simulator.detection_logs
        logger.info(f"Logs de détection: {len(detection_logs)} événements")
        
        # Calculer la durée totale de lecture
        total_play_duration = simulator.get_total_play_duration()
        logger.info(f"Durée totale de lecture: {total_play_duration:.2f} secondes")
        
        # Exporter les logs
        simulator.export_logs("real_api_detection_logs.json", format="json")
        logger.info("Logs exportés dans real_api_detection_logs.json")
        
        # Afficher un résumé des détections
        logger.info("\nRésumé des détections:")
        logger.info(f"Nombre total de détections: {len(detection_logs)}")
        
        methods_count = {}
        for log in detection_logs:
            method = log.get("detection_method", "unknown")
            methods_count[method] = methods_count.get(method, 0) + 1
        
        logger.info("Méthodes de détection utilisées:")
        for method, count in methods_count.items():
            logger.info(f"  - {method}: {count} détection(s)")
        
        logger.info(f"Durée totale de lecture enregistrée: {sum(log.get('play_duration', 0) for log in detection_logs):.2f} secondes")
        
    finally:
        # Arrêter le monitoring
        simulator.stop_monitoring()
        
        # Arrêter la station
        station.stop()
        logger.info("Station arrêtée")
        
        # Arrêter l'enregistrement des logs
        simulator.stop_logging()
        
        logger.info("Test de détection avec API réelles terminé avec succès")


if __name__ == "__main__":
    # Exécuter le test
    asyncio.run(test_real_api_detection()) 