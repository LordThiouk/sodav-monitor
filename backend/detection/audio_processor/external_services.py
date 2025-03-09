"""
External music recognition services integration for SODAV Monitor.
Handles AcoustID and Audd API integration.
"""

import logging
import os
import subprocess
import json
import tempfile
from typing import Dict, Any, Optional
import requests
import musicbrainzngs
import aiohttp
from backend.utils.logging_config import setup_logging, log_with_category, LOG_CATEGORIES
from .audio_analysis import AudioAnalyzer
from sqlalchemy.orm import Session
import asyncio
from pathlib import Path
import io

logger = setup_logging(__name__)

# Définir le chemin vers fpcalc dans le dossier bin du projet
FPCALC_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "bin", "fpcalc")
# Vérifier si fpcalc est disponible et exécutable
FPCALC_AVAILABLE = os.path.exists(FPCALC_PATH) and os.access(FPCALC_PATH, os.X_OK)

def get_fpcalc_path():
    """
    Retourne le chemin vers l'exécutable fpcalc.
    
    Returns:
        str: Chemin vers fpcalc ou None si non trouvé
    """
    global FPCALC_PATH, FPCALC_AVAILABLE
    
    # Utiliser le chemin défini en haut du fichier (bin/fpcalc)
    if FPCALC_AVAILABLE:
        logger.info(f"Using fpcalc at: {FPCALC_PATH}")
        return FPCALC_PATH
    
    # Si le chemin défini n'est pas disponible, essayer de trouver fpcalc dans le PATH
    try:
        result = subprocess.run(["which", "fpcalc"], capture_output=True, text=True)
        if result.returncode == 0:
            path = result.stdout.strip()
            if os.path.exists(path) and os.access(path, os.X_OK):
                FPCALC_PATH = path
                FPCALC_AVAILABLE = True
                logger.info(f"Found fpcalc in PATH: {path}")
                return path
    except Exception as e:
        logger.warning(f"Error checking for fpcalc in PATH: {str(e)}")
    
    # Vérifier dans les chemins alternatifs
    alt_paths = [
        "/Users/cex/Downloads/chromaprint-fpcalc-1.5.1-macos-x86_64/fpcalc",
        "/usr/local/bin/fpcalc",
        "/opt/homebrew/bin/fpcalc"
    ]
    
    for path in alt_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            FPCALC_PATH = path
            FPCALC_AVAILABLE = True
            logger.info(f"Using alternative fpcalc at: {path}")
            return path
    
    logger.warning("fpcalc not available, falling back to metadata search")
    return None

class ExternalServiceError(Exception):
    """Exception raised for errors in external service calls."""
    pass

class AcoustIDService:
    """Service for AcoustID music recognition."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.acoustid.org/v2"):
        self.api_key = api_key
        self.base_url = base_url
    
    async def _generate_fingerprint(self, audio_data: bytes) -> tuple:
        """
        Generate fingerprint using fpcalc.
        
        Args:
            audio_data: Audio data as bytes
            
        Returns:
            Tuple of (fingerprint, duration)
        """
        try:
            # Vérifier si fpcalc est disponible
            fpcalc_path = get_fpcalc_path()
            if not fpcalc_path:
                log_with_category(logger, "ACOUSTID", "warning", "fpcalc not available, cannot generate fingerprint")
                return None, 0
            
            # Sauvegarder les données audio dans un fichier temporaire
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # Générer l'empreinte avec fpcalc
                log_with_category(logger, "ACOUSTID", "info", f"Generating fingerprint with fpcalc for file: {temp_file_path}")
                result = subprocess.run(
                    [fpcalc_path, "-json", temp_file_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    log_with_category(logger, "ACOUSTID", "error", f"fpcalc failed with error: {result.stderr}")
                    return None, 0
                
                # Analyser la sortie JSON
                fpcalc_output = json.loads(result.stdout)
                fingerprint = fpcalc_output.get("fingerprint")
                duration = fpcalc_output.get("duration")
                
                if not fingerprint or not duration:
                    log_with_category(logger, "ACOUSTID", "error", "Failed to generate fingerprint or duration")
                    return None, 0
                
                log_with_category(logger, "ACOUSTID", "info", f"Generated fingerprint: {fingerprint[:20]}... (length: {len(fingerprint)})")
                log_with_category(logger, "ACOUSTID", "info", f"Duration: {duration} seconds")
                
                return fingerprint, float(duration)
            
            finally:
                # Supprimer le fichier temporaire
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
        
        except Exception as e:
            log_with_category(logger, "ACOUSTID", "error", f"Error generating fingerprint: {str(e)}")
            import traceback
            log_with_category(logger, "ACOUSTID", "error", f"Traceback: {traceback.format_exc()}")
            return None, 0
    
    async def detect_track(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Detect track using AcoustID service.
        
        Args:
            audio_data: Audio data as bytes
            
        Returns:
            Dictionary with track information or None if not found
        """
        try:
            # Generate fingerprint
            fingerprint_result = await self._generate_fingerprint(audio_data)
            if not fingerprint_result:
                log_with_category(logger, "ACOUSTID", "error", "Failed to generate fingerprint")
                return None
                
            fingerprint, duration = fingerprint_result
            
            # Prepare request parameters
            params = {
                "client": self.api_key,
                "meta": "recordings releasegroups releases tracks compress",
                "fingerprint": fingerprint,
                "duration": str(int(duration))
            }
            
            # Send request to AcoustID
            url = f"{self.base_url}/lookup"
            
            # Log request details
            log_with_category(logger, "ACOUSTID", "info", f"Sending request to AcoustID: {url} with fingerprint length {len(fingerprint)}")
            log_with_category(logger, "ACOUSTID", "debug", f"AcoustID request parameters: {params}")
            
            async with aiohttp.ClientSession() as session:
                # Utiliser POST au lieu de GET pour les grandes quantités de données
                async with session.post(url, data=params, timeout=30) as response:
                    # Log response status
                    log_with_category(logger, "ACOUSTID", "info", f"AcoustID response status: {response.status}")
                    
                    # Get response text for logging
                    response_text = await response.text()
                    log_with_category(logger, "ACOUSTID", "info", f"AcoustID response text: {response_text[:500]}...")
                    
                    if response.status != 200:
                        log_with_category(logger, "ACOUSTID", "error", f"AcoustID error: {response_text}")
                        return None
                    
                    try:
                        data = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        log_with_category(logger, "ACOUSTID", "error", f"Failed to parse AcoustID response as JSON: {e}")
                        log_with_category(logger, "ACOUSTID", "error", f"Response text: {response_text[:1000]}")
                        return None
                    
                    # Log complete response for debugging
                    log_with_category(logger, "ACOUSTID", "debug", f"AcoustID complete response: {json.dumps(data)}")
                    
                    # Check if results are found
                    if "results" not in data or not data["results"]:
                        log_with_category(logger, "ACOUSTID", "info", "No AcoustID results found")
                        return None
                    
                    # Get the best result (highest score)
                    best_result = max(data["results"], key=lambda x: x.get("score", 0))
                    score = best_result.get("score", 0)
                    
                    log_with_category(logger, "ACOUSTID", "info", f"AcoustID best result score: {score}")
                    
                    # Check if recordings are found
                    if "recordings" not in best_result or not best_result["recordings"]:
                        log_with_category(logger, "ACOUSTID", "info", "No recordings found in AcoustID result")
                        return None
                    
                    # Get the best recording (first one)
                    recording = best_result["recordings"][0]
                    
                    # Extract track information
                    title = recording.get("title", "Unknown Track")
                    
                    # Extract artist information
                    artist = "Unknown Artist"
                    if "artists" in recording and recording["artists"]:
                        artist = recording["artists"][0].get("name", "Unknown Artist")
                    
                    # Extract album information
                    album = "Unknown Album"
                    if "releasegroups" in recording and recording["releasegroups"]:
                        album = recording["releasegroups"][0].get("title", "Unknown Album")
                    
                    # Extract additional information
                    isrc = None
                    label = None
                    release_date = None
                    
                    if "releases" in recording and recording["releases"]:
                        release = recording["releases"][0]
                        
                        # Extract ISRC
                        if "isrcs" in release and release["isrcs"]:
                            isrc = release["isrcs"][0]
                        
                        # Extract label
                        if "label-info" in release and release["label-info"]:
                            label_info = release["label-info"][0]
                            if "label" in label_info and "name" in label_info["label"]:
                                label = label_info["label"]["name"]
                        
                        # Extract release date
                        if "date" in release:
                            release_date = release["date"]
                    
                    # Create result dictionary
                    result = {
                        "title": title,
                        "artist": artist,
                        "album": album,
                        "isrc": isrc,
                        "label": label,
                        "release_date": release_date,
                        "id": recording.get("id"),
                        "confidence": score,
                        "source": "acoustid"
                    }
                    
                    log_with_category(logger, "ACOUSTID", "info", f"AcoustID detection result: {title} by {artist}, confidence: {score}")
                    
                    return result
        
        except asyncio.TimeoutError:
            log_with_category(logger, "ACOUSTID", "error", "AcoustID request timed out after 30 seconds")
            return None
        except Exception as e:
            log_with_category(logger, "ACOUSTID", "error", f"Error detecting track with AcoustID: {str(e)}")
            import traceback
            log_with_category(logger, "ACOUSTID", "error", f"Traceback: {traceback.format_exc()}")
            return None
    
    async def search_by_metadata(self, artist: str, title: str) -> Optional[Dict[str, Any]]:
        """
        Search for a track using MusicBrainz API with artist and title.
        
        Args:
            artist: Artist name
            title: Track title
            
        Returns:
            Dict containing track information or None if no match found
            
        Raises:
            ExternalServiceError: If API request fails
        """
        try:
            logger.info(f"Searching for track: {title} by {artist}")
            
            # Initialiser MusicBrainz
            musicbrainzngs.set_useragent(
                os.getenv('MUSICBRAINZ_APP_NAME', "SODAV Monitor"),
                os.getenv('MUSICBRAINZ_VERSION', "1.0"),
                os.getenv('MUSICBRAINZ_CONTACT', "https://sodav.sn")
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
            raise ExternalServiceError(f"MusicBrainz API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in MusicBrainz search: {str(e)}")
            raise ExternalServiceError(f"Unexpected error in MusicBrainz search: {str(e)}")
    
    async def detect_track_with_retry(
        self, 
        audio_data: bytes, 
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Detect a track with automatic retry on failure.
        
        Args:
            audio_data: Raw audio data bytes
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Dict containing track information or None if no match found
        """
        for attempt in range(max_retries):
            try:
                return await self.detect_track(audio_data)
            except ExternalServiceError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"AcoustID detection failed (attempt {attempt + 1}): {str(e)}")
                await asyncio.sleep(retry_delay * (attempt + 1))
        return None
    
    async def search_by_metadata_with_retry(
        self, 
        artist: str, 
        title: str, 
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Search for a track by metadata with automatic retry on failure.
        
        Args:
            artist: Artist name
            title: Track title
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Dict containing track information or None if no match found
        """
        for attempt in range(max_retries):
            try:
                return await self.search_by_metadata(artist, title)
            except ExternalServiceError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"MusicBrainz search failed (attempt {attempt + 1}): {str(e)}")
                await asyncio.sleep(retry_delay * (attempt + 1))
        return None

# Alias for backward compatibility
MusicBrainzService = AcoustIDService

class AuddService:
    """Service for AudD music recognition."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.audd.io"):
        self.api_key = api_key
        self.base_url = base_url
    
    async def detect_track(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Detect track using AudD service.
        
        Args:
            audio_data: Audio data as bytes
            
        Returns:
            Dictionary with track information or None if not found
        """
        try:
            # Prepare the audio data for sending
            audio_file = io.BytesIO(audio_data)
            
            data = {
                'api_token': self.api_key,
                'return': 'spotify,apple_music,musicbrainz,deezer'
            }
            
            files = {
                'file': ('audio.mp3', audio_file, 'audio/mpeg')
            }
            
            log_with_category(logger, "AUDD", "info", f"Sending audio data to AudD API: {len(audio_data)} bytes")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, data=data, files=files) as response:
                    # Log response status
                    log_with_category(logger, "AUDD", "info", f"AudD response status: {response.status}")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        log_with_category(logger, "AUDD", "error", f"AudD error: {error_text}")
                        return None
                    
                    result = await response.json()
                    
                    # Log complete response for debugging
                    log_with_category(logger, "AUDD", "debug", f"AudD complete response: {json.dumps(result)}")
                    
                    # Check if track is found
                    if "result" not in result or not result["result"]:
                        log_with_category(logger, "AUDD", "info", "No AudD results found")
                        return None
                    
                    # Extract track information
                    track_data = result["result"]
                    
                    # Log track details
                    log_with_category(logger, "AUDD", "info", f"AudD found track: {track_data.get('title', 'Unknown')} by {track_data.get('artist', 'Unknown')}")
                    
                    # Create result dictionary
                    detection_result = {
                        "title": track_data.get("title", "Unknown Track"),
                        "artist": track_data.get("artist", "Unknown Artist"),
                        "album": track_data.get("album", "Unknown Album"),
                        "release_date": track_data.get("release_date"),
                        "label": track_data.get("label"),
                        "isrc": track_data.get("isrc"),
                        "confidence": 0.8,  # AudD doesn't provide confidence, so we use a default value
                        "source": "audd"
                    }
                    
                    # Add external IDs if available
                    if "spotify" in track_data:
                        spotify_data = track_data["spotify"]
                        detection_result["spotify_id"] = spotify_data.get("id")
                        
                        # Add additional Spotify data if available
                        if "album" in spotify_data and "release_date" not in detection_result:
                            detection_result["release_date"] = spotify_data["album"].get("release_date")
                    
                    if "musicbrainz" in track_data:
                        musicbrainz_data = track_data["musicbrainz"]
                        detection_result["musicbrainz_id"] = musicbrainz_data.get("id")
                    
                    if "deezer" in track_data:
                        deezer_data = track_data["deezer"]
                        detection_result["deezer_id"] = deezer_data.get("id")
                    
                    log_with_category(logger, "AUDD", "info", f"AudD detection result: {detection_result['title']} by {detection_result['artist']}")
                    
                    return detection_result
        
        except Exception as e:
            log_with_category(logger, "AUDD", "error", f"Error detecting track with AudD: {str(e)}")
            return None
    
    async def detect_track_with_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Detect a track using Audd API with a URL instead of raw audio data.
        
        Args:
            url: URL of the audio file to analyze
            
        Returns:
            Dict containing track information or None if no match found
            
        Raises:
            ExternalServiceError: If API request fails
        """
        try:
            data = {
                "api_token": self.api_key,
                "url": url,
                "return": "apple_music,spotify"
            }
            
            logger.info(f"Sending URL request to AudD API: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    data=data,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        raise ExternalServiceError(f"Audd API error: {response.status}")
                    
                    result = await response.json()
                    logger.info(f"AudD API response: {result}")
                    
                    if result.get("status") == "error":
                        error_msg = result.get("error", {}).get("error_message", "Unknown error")
                        raise ExternalServiceError(f"Audd API error: {error_msg}")
                    
                    if not result.get("result"):
                        return None
                    
                    track = result["result"]
                    return {
                        "title": track.get("title", "Unknown"),
                        "artist": track.get("artist", "Unknown Artist"),
                        "album": track.get("album", "Unknown Album"),
                        "confidence": 0.8,  # Default confidence for URL-based detection
                        "source": "audd",
                        "id": track.get("song_link", "")
                    }
                    
        except asyncio.TimeoutError:
            raise ExternalServiceError("Audd request timed out")
        except aiohttp.ClientError as e:
            raise ExternalServiceError(f"Audd request failed: {str(e)}")
        except Exception as e:
            raise ExternalServiceError(f"Unexpected error in Audd request: {str(e)}")
    
    async def detect_track_with_retry(
        self, 
        audio_data: bytes, 
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Detect a track with automatic retry on failure.
        
        Args:
            audio_data: Raw audio data bytes
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Dict containing track information or None if no match found
        """
        for attempt in range(max_retries):
            try:
                return await self.detect_track(audio_data)
            except ExternalServiceError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Audd detection failed (attempt {attempt + 1}): {str(e)}")
                await asyncio.sleep(retry_delay * (attempt + 1))
        return None
    
    async def detect_track_with_url_retry(
        self, 
        url: str, 
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Detect a track with URL and automatic retry on failure.
        
        Args:
            url: URL of the audio file to analyze
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Dict containing track information or None if no match found
        """
        for attempt in range(max_retries):
            try:
                return await self.detect_track_with_url(url)
            except ExternalServiceError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Audd URL detection failed (attempt {attempt + 1}): {str(e)}")
                await asyncio.sleep(retry_delay * (attempt + 1))
        return None

class ExternalServiceHandler:
    def __init__(self, db_session: Session, audd_api_key: Optional[str] = None, acoustid_api_key: Optional[str] = None):
        """Initialize external services handler.
        
        Args:
            db_session: Database session
            audd_api_key: Optional API key for Audd service
            acoustid_api_key: Optional API key for AcoustID service
        """
        self.db_session = db_session
        self.audd_api_key = audd_api_key or os.getenv('AUDD_API_KEY')
        self.acoustid_api_key = acoustid_api_key or os.getenv('ACOUSTID_API_KEY')
        self.audio_analyzer = AudioAnalyzer()
        self.initialized = False
        self.initialize()
        
    def initialize(self):
        """Initialize external services"""
        if not self.audd_api_key:
            logger.warning("Audd API key not provided")
            
        if not self.acoustid_api_key:
            logger.warning("ACOUSTID_API_KEY not found in environment variables")
            
        # Initialize AcoustID/MusicBrainz
        musicbrainzngs.set_useragent(
            os.getenv('MUSICBRAINZ_APP_NAME', "SODAV Monitor"),
            os.getenv('MUSICBRAINZ_VERSION', "1.0"),
            os.getenv('MUSICBRAINZ_CONTACT', "https://sodav.sn")
        )
        
        self.initialized = True
        logger.info("ExternalServiceHandler initialized successfully")
        
    async def recognize_with_acoustid(self, audio_data: bytes, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Recognize music using AcoustID.
        
        Args:
            audio_data: Raw audio bytes
            max_retries: Maximum number of retries for rate limit errors
            
        Returns:
            Dictionary with recognition results or None if error/no match
        """
        if not self.acoustid_api_key:
            logger.warning("Cannot recognize with AcoustID: ACOUSTID_API_KEY not found")
            return None
            
        retries = 0
        while retries <= max_retries:
            try:
                # Extract audio features
                features = self.audio_analyzer.extract_features(audio_data)
                
                # Search AcoustID/MusicBrainz
                result = musicbrainzngs.search_recordings(
                    query=f"duration:{int(features['duration'])}",
                    limit=5
                )
                
                if not result['recordings']:
                    return None
                    
                recording = result['recording-list'][0]
                return {
                    'title': recording['title'],
                    'artist': recording['artist-credit'][0]['name'],
                    'duration': recording['duration'] / 1000.0,
                    'confidence': 0.7,
                    'source': 'acoustid'
                }
                
            except musicbrainzngs.WebServiceError as e:
                if 'Rate limit exceeded' in str(e) and retries < max_retries:
                    retries += 1
                    await asyncio.sleep(1)  # Wait before retrying
                    continue
                logger.error(f"Error recognizing with AcoustID: {str(e)}, caused by: {e.__cause__}")
                return None
            except Exception as e:
                logger.error(f"Error recognizing with AcoustID: {str(e)}")
                return None
    
    async def recognize_with_musicbrainz_metadata(self, artist: str, title: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Recognize music using MusicBrainz metadata search.
        
        Args:
            artist: Artist name
            title: Track title
            max_retries: Maximum number of retries for rate limit errors
            
        Returns:
            Dictionary with recognition results or None if error/no match
        """
        if not self.acoustid_api_key:
            logger.warning("Cannot recognize with MusicBrainz: ACOUSTID_API_KEY not found")
            return None
        
        try:
            # Créer une instance du service AcoustID/MusicBrainz
            acoustid_service = AcoustIDService(api_key=self.acoustid_api_key)
            
            # Utiliser la méthode de recherche par métadonnées
            return await acoustid_service.search_by_metadata_with_retry(
                artist=artist,
                title=title,
                max_retries=max_retries
            )
        except Exception as e:
            logger.error(f"Error recognizing with MusicBrainz metadata: {str(e)}")
            return None
    
    async def recognize_with_audd(self, audio_data: bytes, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Recognize music using Audd API.
        
        Args:
            audio_data: Raw audio bytes
            max_retries: Maximum number of retries for network errors
            
        Returns:
            Dictionary with recognition results or None if error/no match
        """
        if not self.audd_api_key:
            logger.error("No Audd API key provided")
            return None
            
        retries = 0
        while retries <= max_retries:
            try:
                data = {
                    'api_token': self.audd_api_key,
                    'return': 'apple_music,spotify'
                }
                files = {'file': ('audio.wav', audio_data)}
                
                async with aiohttp.ClientSession() as session:
                    async with session.post('https://api.audd.io/', data=data, files=files) as response:
                        if response.status != 200:
                            if retries < max_retries:
                                retries += 1
                                await asyncio.sleep(1)  # Wait before retrying
                                continue
                            logger.error(f"Audd API error: {response.status}")
                            return None
                            
                        result = await response.json()
                        
                        if not result.get('result'):
                            return None
                            
                        return {
                            'title': result['result']['title'],
                            'artist': result['result']['artist'],
                            'album': result['result'].get('album'),
                            'release_date': result['result'].get('release_date'),
                            'confidence': 0.9,
                            'source': 'audd'
                        }
                        
            except Exception as e:
                logger.error(f"Error recognizing with Audd: {str(e)}")
                if retries < max_retries:
                    retries += 1
                    await asyncio.sleep(1)  # Wait before retrying
                    continue
                return None
                
        return None
    
    async def recognize_with_audd_url(self, url: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Recognize music using Audd API with a URL.
        
        Args:
            url: URL of the audio file to analyze
            max_retries: Maximum number of retries for network errors
            
        Returns:
            Dictionary with recognition results or None if error/no match
        """
        if not self.audd_api_key:
            logger.error("No Audd API key provided")
            return None
        
        # Créer une instance du service AudD
        audd_service = AuddService(api_key=self.audd_api_key)
        
        try:
            # Utiliser la méthode de détection par URL avec retry
            return await audd_service.detect_track_with_url_retry(url, max_retries=max_retries)
        except Exception as e:
            logger.error(f"Error recognizing with Audd URL: {str(e)}")
            return None

class MusicBrainzService:
    """Service for MusicBrainz metadata search."""
    
    def __init__(self):
        """Initialize the MusicBrainz service."""
        # Set the user agent for MusicBrainz API
        musicbrainzngs.set_useragent("SODAV Monitor", "1.0", "contact@sodav.sn")
        logger.info("MusicBrainz service initialized")
    
    async def search_recording(self, artist: str, title: str) -> Optional[Dict[str, Any]]:
        """
        Search for a recording in MusicBrainz by artist and title.
        
        Args:
            artist: Artist name
            title: Track title
            
        Returns:
            Dictionary with track information or None if not found
        """
        try:
            # Log search parameters
            logger.info(f"Searching MusicBrainz for recording - Artist: {artist}, Title: {title}")
            
            if not artist or not title or artist == "Unknown Artist" or title == "Unknown Track":
                logger.warning("Invalid artist or title for MusicBrainz search")
                return None
            
            # Create a search query
            query = f'artist:"{artist}" AND recording:"{title}"'
            logger.info(f"MusicBrainz search query: {query}")
            
            # Execute the search in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: musicbrainzngs.search_recordings(query=query, limit=5)
            )
            
            # Log the complete response for debugging
            logger.info(f"MusicBrainz complete response: {json.dumps(result)}")
            
            # Check if recordings are found
            if "recording-list" not in result or not result["recording-list"]:
                logger.info("No recordings found in MusicBrainz")
                return None
            
            # Get the best match (first result)
            recording = result["recording-list"][0]
            
            # Log recording details
            logger.info(f"MusicBrainz recording: {recording.get('title', 'Unknown')} by {recording.get('artist-credit', [{'artist': {'name': 'Unknown'}}])[0]['artist'].get('name', 'Unknown')}")
            
            # Extract track information
            title = recording.get("title", "Unknown Track")
            
            # Extract artist information
            artist = "Unknown Artist"
            if "artist-credit" in recording and recording["artist-credit"]:
                artist = recording["artist-credit"][0]["artist"].get("name", "Unknown Artist")
            
            # Extract release information
            album = None
            isrc = None
            label = None
            release_date = None
            
            if "release-list" in recording and recording["release-list"]:
                release = recording["release-list"][0]
                album = release.get("title")
                
                # Get additional release details in a separate request
                try:
                    release_id = release.get("id")
                    if release_id:
                        logger.info(f"Fetching additional details for release: {release_id}")
                        
                        release_info = await loop.run_in_executor(
                            None,
                            lambda: musicbrainzngs.get_release_by_id(release_id, includes=["recordings", "isrcs", "labels"])
                        )
                        
                        # Log release details
                        logger.info(f"MusicBrainz release details: {json.dumps(release_info)}")
                        
                        if "release" in release_info:
                            release_data = release_info["release"]
                            
                            # Extract ISRC
                            if "medium-list" in release_data:
                                for medium in release_data["medium-list"]:
                                    if "track-list" in medium:
                                        for track in medium["track-list"]:
                                            if "recording" in track and "isrc-list" in track["recording"] and track["recording"]["isrc-list"]:
                                                isrc = track["recording"]["isrc-list"][0]
                                                break
                                        if isrc:
                                            break
                            
                            # Extract label
                            if "label-info-list" in release_data and release_data["label-info-list"]:
                                label_info = release_data["label-info-list"][0]
                                if "label" in label_info:
                                    label = label_info["label"].get("name")
                            
                            # Extract release date
                            release_date = release_data.get("date")
                except Exception as e:
                    logger.error(f"Error fetching release details: {e}")
            
            # Log extracted information
            logger.info(f"Extracted from MusicBrainz - Title: {title}, Artist: {artist}, Album: {album}, ISRC: {isrc}, Label: {label}, Release date: {release_date}")
            
            # Return track information
            return {
                "title": title,
                "artist": artist,
                "album": album,
                "id": recording.get("id", ""),
                "isrc": isrc,
                "label": label,
                "release_date": release_date,
                "confidence": 0.9,  # MusicBrainz doesn't provide confidence score
                "source": "musicbrainz"
            }
        except Exception as e:
            logger.error(f"Error searching MusicBrainz: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None 