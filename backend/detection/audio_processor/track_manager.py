"""Module for managing track detection and storage."""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models.models import Track, TrackDetection, RadioStation, StationTrackStats, Artist
from backend.utils.logging_config import setup_logging, log_with_category
from backend.utils.analytics.stats_updater import StatsUpdater
import numpy as np
from backend.detection.audio_processor.external_services import MusicBrainzService, AuddService, ExternalServiceHandler, AcoustIDService
import io
from pydub import AudioSegment
import hashlib
import json

logger = setup_logging(__name__)

class TrackManager:
    """Gestionnaire des pistes audio."""
    
    def __init__(self, db_session: Session, feature_extractor=None):
        """Initialise le gestionnaire de pistes."""
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        self.current_tracks = {}
        
        # If feature_extractor is not provided, create a new one
        if feature_extractor is None:
            from .feature_extractor import FeatureExtractor
            self.feature_extractor = FeatureExtractor()
        
        # Ensure we have a database connection
        if self.db_session is None:
            from backend.models.database import get_db
            self.db_session = get_db()
    
    async def process_track(self, features: Dict[str, Any], station_id: Optional[int] = None) -> Dict[str, Any]:
        """Traite une piste détectée."""
        try:
            # Vérifie si une piste est déjà en cours de lecture
            if station_id in self.current_tracks:
                current_track = self.current_tracks[station_id]
                # Si c'est la même piste, met à jour la durée
                if self._is_same_track(features, current_track):
                    return self._update_current_track(station_id, features)
                else:
                    # Si c'est une nouvelle piste, termine l'ancienne
                    self._end_current_track(station_id)
            
            # Crée ou récupère la piste
            track = self._get_or_create_track(features)
            if not track:
                return {"error": "Impossible de créer la piste"}
            
            # Démarre le suivi de la nouvelle piste
            detection_info = self._start_track_detection(track, station_id, features)
            
            return {
                "status": "success",
                "track": track.to_dict(),
                "detection": detection_info
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la piste: {str(e)}")
            return {"error": str(e)}
    
    def _is_same_track(self, features: Dict[str, Any], current_track: Dict[str, Any]) -> bool:
        """Vérifie si les caractéristiques correspondent à la piste en cours."""
        try:
            # Compare les caractéristiques principales
            threshold = 0.85
            similarity = self._calculate_similarity(features, current_track["features"])
            return similarity >= threshold
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la comparaison des pistes: {str(e)}")
            return False
    
    def _update_current_track(self, station_id: int, features: Dict[str, Any]) -> Dict[str, Any]:
        """Met à jour les informations de la piste en cours."""
        try:
            current = self.current_tracks[station_id]
            current["play_duration"] += timedelta(seconds=features.get("play_duration", 0))
            current["features"] = features
            
            return {
                "status": "playing",
                "track": current["track"].to_dict(),
                "play_duration": current["play_duration"].total_seconds()
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour de la piste: {str(e)}")
            return {"error": str(e)}
    
    def _end_current_track(self, station_id: int):
        """Termine le suivi de la piste en cours."""
        try:
            if station_id in self.current_tracks:
                current = self.current_tracks[station_id]
                
                # Enregistre la détection
                detection = TrackDetection(
                    track_id=current["track"].id,
                    station_id=station_id,
                    detected_at=current["start_time"],
                    end_time=datetime.utcnow(),
                    play_duration=current["play_duration"],
                    fingerprint=current["features"].get("fingerprint", ""),
                    audio_hash=current["features"].get("audio_hash", ""),
                    confidence=current["features"].get("confidence", 0)
                )
                self.db_session.add(detection)
                
                # Met à jour les statistiques
                self._update_station_track_stats(
                    station_id,
                    current["track"].id,
                    current["play_duration"]
                )
                
                # Supprime la piste courante
                del self.current_tracks[station_id]
                
                # Commit les changements
                self.db_session.commit()
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la fin de la piste: {str(e)}")
            self.db_session.rollback()
    
    def _get_or_create_track(self, features: Dict[str, Any]) -> Optional[Track]:
        """Récupère ou crée une piste dans la base de données."""
        try:
            # Recherche la piste existante
            track = self.db_session.query(Track).filter_by(
                title=features.get("title"),
                artist_name=features.get("artist")
            ).first()
            
            if track:
                return track
            
            # Crée l'artiste s'il n'existe pas
            artist = self.db_session.query(Artist).filter_by(
                name=features.get("artist")
            ).first()
            
            if not artist:
                artist = Artist(
                    name=features.get("artist"),
                    country=features.get("country"),
                    genre=features.get("genre")
                )
                self.db_session.add(artist)
            
            # Crée la nouvelle piste
            track = Track(
                title=features.get("title"),
                artist_id=artist.id,
                artist_name=artist.name,
                duration=features.get("play_duration", 0),
                genre=features.get("genre"),
                release_date=features.get("release_date"),
                fingerprint=features.get("fingerprint")
            )
            
            self.db_session.add(track)
            self.db_session.commit()
            
            return track
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la création de la piste: {str(e)}")
            self.db_session.rollback()
            return None
    
    def _start_track_detection(self, track: Track, station_id: int, features: Dict[str, Any]) -> Dict[str, Any]:
        """Démarre le suivi d'une nouvelle piste."""
        try:
            start_time = datetime.utcnow()
            self.current_tracks[station_id] = {
                "track": track,
                "start_time": start_time,
                "play_duration": timedelta(seconds=features.get("play_duration", 0)),
                "features": features
            }
            
            return {
                "track_id": track.id,
                "start_time": start_time.isoformat(),
                "confidence": features.get("confidence", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage de la détection: {str(e)}")
            return {}
    
    def _update_station_track_stats(self, station_id: int, track_id: int, play_duration: timedelta):
        """Met à jour les statistiques de diffusion."""
        try:
            stats = self.db_session.query(StationTrackStats).filter_by(
                station_id=station_id,
                track_id=track_id
            ).first()
            
            if stats:
                stats.play_count += 1
                # Convertir la durée existante en secondes, ajouter la nouvelle durée, puis reconvertir en timedelta
                current_seconds = stats.total_play_time.total_seconds() if stats.total_play_time else 0
                new_seconds = play_duration.total_seconds()
                stats.total_play_time = timedelta(seconds=current_seconds + new_seconds)
                stats.last_played = datetime.utcnow()
            else:
                stats = StationTrackStats(
                    station_id=station_id,
                    track_id=track_id,
                    play_count=1,
                    total_play_time=play_duration,  # Utiliser directement timedelta
                    last_played=datetime.utcnow()
                )
                self.db_session.add(stats)
            
            self.db_session.commit()
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour des statistiques: {str(e)}")
            self.db_session.rollback()
    
    def _calculate_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """Calcule la similarité entre deux ensembles de caractéristiques."""
        try:
            # Caractéristiques à comparer
            keys = [
                "mfcc_mean",
                "chroma_mean",
                "spectral_centroid_mean",
                "rhythm_strength"
            ]
            
            total_weight = 0
            similarity_score = 0
            
            for key in keys:
                if key in features1 and key in features2:
                    weight = 1.0
                    if isinstance(features1[key], list) and isinstance(features2[key], list):
                        # Pour les vecteurs (MFCC, chroma)
                        vec1 = np.array(features1[key])
                        vec2 = np.array(features2[key])
                        if len(vec1) == len(vec2):
                            similarity = 1 - np.mean(np.abs(vec1 - vec2))
                            similarity_score += weight * similarity
                            total_weight += weight
                    else:
                        # Pour les scalaires
                        val1 = float(features1[key])
                        val2 = float(features2[key])
                        max_val = max(abs(val1), abs(val2))
                        if max_val > 0:
                            similarity = 1 - abs(val1 - val2) / max_val
                            similarity_score += weight * similarity
                            total_weight += weight
            
            return similarity_score / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de similarité: {str(e)}")
            return 0.0
            
    # Implémentation des méthodes manquantes
    
    async def find_local_match(self, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Recherche une correspondance locale dans la base de données."""
        try:
            logger.info("[TRACK_MANAGER] Attempting to find local match")
            
            # Extraire l'empreinte audio
            fingerprint = self._extract_fingerprint(features)
            if not fingerprint:
                logger.warning("[TRACK_MANAGER] Failed to extract fingerprint for local match")
                return None
            
            logger.info("[TRACK_MANAGER] Fingerprint extracted, searching in database")
            
            # Rechercher dans la base de données
            tracks = self.db_session.query(Track).filter(
                Track.fingerprint.isnot(None)
            ).all()
            
            logger.info(f"[TRACK_MANAGER] Found {len(tracks)} tracks with fingerprints in database")
            
            if not tracks:
                logger.info("[TRACK_MANAGER] No tracks with fingerprints found in database")
                return None
            
            # Calculer la similarité avec chaque piste
            best_match = None
            best_score = 0.0
            
            # D'abord, essayer une correspondance exacte
            exact_match = self.db_session.query(Track).filter(
                Track.fingerprint == fingerprint
            ).first()
            
            if exact_match:
                # Récupérer le nom de l'artiste via la relation
                artist_name = exact_match.artist.name if exact_match.artist else "Unknown Artist"
                logger.info(f"[TRACK_MANAGER] Exact fingerprint match found: {exact_match.title} by {artist_name}")
                return {
                    "title": exact_match.title,
                    "artist": artist_name,
                    "album": exact_match.album,
                    "id": exact_match.id,
                    "isrc": exact_match.isrc,
                    "label": exact_match.label,
                    "release_date": exact_match.release_date,
                    "fingerprint": exact_match.fingerprint[:20] + "..." if exact_match.fingerprint else None,
                    "confidence": 1.0,
                    "source": "local"
                }
            
            # Si pas de correspondance exacte, utiliser la similarité
            for track in tracks:
                if track.fingerprint:
                    similarity = self._calculate_similarity(
                        {"fingerprint": fingerprint}, 
                        {"fingerprint": track.fingerprint}
                    )
                    logger.debug(f"[TRACK_MANAGER] Similarity with track {track.id} ({track.title}): {similarity}")
                    
                    if similarity > best_score and similarity > 0.7:  # Seuil de similarité
                        best_score = similarity
                        best_match = track
            
            if best_match:
                # Récupérer le nom de l'artiste via la relation
                artist_name = best_match.artist.name if best_match.artist else "Unknown Artist"
                logger.info(f"[TRACK_MANAGER] Local match found: {best_match.title} by {artist_name} (score: {best_score})")
                return {
                    "title": best_match.title,
                    "artist": artist_name,
                    "album": best_match.album,
                    "id": best_match.id,
                    "isrc": best_match.isrc,
                    "label": best_match.label,
                    "release_date": best_match.release_date,
                    "fingerprint": best_match.fingerprint[:20] + "..." if best_match.fingerprint else None,
                    "confidence": best_score,
                    "source": "local"
                }
            else:
                logger.info("[TRACK_MANAGER] No local match found with sufficient confidence")
                return None
                
        except Exception as e:
            logger.error(f"[TRACK_MANAGER] Error finding local match: {str(e)}")
            return None
    
    async def find_acoustid_match(self, audio_features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a match using AcoustID service.
        
        Args:
            audio_features: Audio features dictionary
            
        Returns:
            Dictionary with track information or None if not found
        """
        try:
            # Check if raw audio is available in features
            if "raw_audio" not in audio_features or not audio_features["raw_audio"]:
                log_with_category(logger, "TRACK_MANAGER", "info", "No raw audio data in features, cannot use AcoustID")
                return None
                
            # Get raw audio data
            raw_audio = audio_features["raw_audio"]
            log_with_category(logger, "TRACK_MANAGER", "info", f"Using raw audio data from features ({len(raw_audio)} bytes)")
            
            # Initialize AcoustID service
            acoustid_service = AcoustIDService()
            log_with_category(logger, "TRACK_MANAGER", "info", f"AcoustID API key: {acoustid_service.api_key[:3]}...{acoustid_service.api_key[-3:]}")
            
            # Send audio data to AcoustID
            log_with_category(logger, "TRACK_MANAGER", "info", "Sending audio data to AcoustID for detection")
            result = await acoustid_service.detect_track_with_retry(raw_audio, max_retries=2)
            
            if not result:
                log_with_category(logger, "TRACK_MANAGER", "info", "No track detected by AcoustID")
                return None
                
            log_with_category(logger, "TRACK_MANAGER", "info", f"AcoustID detected track: {result.get('title', 'Unknown')} by {result.get('artist', 'Unknown')}")
            
            # Add detection method to result
            result["detection_method"] = "acoustid"
            
            return result
            
        except Exception as e:
            log_with_category(logger, "TRACK_MANAGER", "error", f"Error finding AcoustID match: {str(e)}")
            import traceback
            log_with_category(logger, "TRACK_MANAGER", "error", f"Traceback: {traceback.format_exc()}")
            return None
    
    async def find_musicbrainz_match(self, metadata, station_id=None):
        """Find a match using MusicBrainz metadata search."""
        self.logger.info("Attempting to find MusicBrainz match using metadata")
        
        try:
            # Check if we have artist and title in metadata
            artist_name = metadata.get("artist")
            title = metadata.get("title")
            
            if not artist_name or not title:
                self.logger.warning("No artist or title in metadata for MusicBrainz search")
                return None
            
            # Initialize AcoustID service (which includes MusicBrainz functionality)
            api_key = os.environ.get("ACOUSTID_API_KEY")
            if not api_key:
                self.logger.warning("AcoustID API key not found for MusicBrainz search")
                return None
            
            acoustid_service = AcoustIDService(api_key)
            
            # Search by metadata
            result = await acoustid_service.search_by_metadata(artist_name, title)
            
            if not result:
                self.logger.warning("No MusicBrainz match found")
                return None
            
            album = result.get("album")
            
            # Capture additional information
            isrc = result.get("isrc")
            label = result.get("label")
            release_date = result.get("release_date")
            
            # Log the additional information
            self.logger.info(f"Track details - ISRC: {isrc}, Label: {label}, Release date: {release_date}")
            
            # Check if artist exists
            artist = self.db_session.query(Artist).filter(Artist.name == artist_name).first()
            if not artist:
                self.logger.info(f"Created new artist: {artist_name}")
                artist = Artist(name=artist_name)
                
                # Add label information if available
                if label:
                    artist.label = label
                
                self.db_session.add(artist)
                self.db_session.flush()
            elif label and not artist.label:
                # Update artist label if it was previously unknown
                artist.label = label
                self.db_session.flush()
            
            # Check if track exists
            track = self.db_session.query(Track).filter(
                Track.title == title,
                Track.artist_id == artist.id
            ).first()
            
            # Calculate exact play duration
            play_duration = metadata.get("play_duration", 0)
            self.logger.info(f"Exact play duration: {play_duration} seconds")
            
            # Convert duration to timedelta
            duration = timedelta(seconds=play_duration)
            
            # Generate fingerprint if not already available
            fingerprint = metadata.get("fingerprint")
            if not fingerprint:
                # Try to create a simple fingerprint from metadata
                fingerprint = hashlib.md5(f"{title}:{artist_name}:{album or ''}".encode()).hexdigest()
                self.logger.info(f"Generated metadata-based fingerprint: {fingerprint[:20]}...")
            
            if not track:
                # Create new track
                track = Track(
                    title=title,
                    artist_id=artist.id,
                    isrc=isrc,
                    album=album,
                    duration=duration,
                    fingerprint=fingerprint,
                    label=label,
                    release_date=release_date
                )
                self.db_session.add(track)
                self.db_session.flush()
                self.logger.info(f"Created new track: {title} by {artist_name} (ISRC: {isrc})")
            else:
                # Update track with new information if available
                if isrc and not track.isrc:
                    track.isrc = isrc
                if label and not track.label:
                    track.label = label
                if release_date and not track.release_date:
                    track.release_date = release_date
                if fingerprint and not track.fingerprint:
                    track.fingerprint = fingerprint
                if album and not track.album:
                    track.album = album
                
                track.updated_at = datetime.utcnow()
                self.db_session.flush()
                self.logger.info(f"Updated existing track: {title} by {artist_name} (ISRC: {isrc})")
            
            # Record play time if station_id is provided
            if station_id:
                self._record_play_time(station_id, track.id, play_duration)
            
            # Return result with enhanced information
            return {
                "track": {
                    "title": title,
                    "artist": artist_name,
                    "album": album,
                    "id": result.get("id", ""),
                    "isrc": isrc,
                    "label": label,
                    "release_date": release_date,
                    "fingerprint": fingerprint[:20] + "..." if fingerprint else None  # Truncated for logging
                },
                "confidence": 0.9,  # High confidence for metadata match
                "source": "musicbrainz",
                "play_duration": play_duration
            }
        except Exception as e:
            self.logger.error(f"Error finding MusicBrainz match: {e}")
            return None
    
    async def find_audd_match(self, audio_features, station_id=None):
        """Find a match using AudD service."""
        self.logger.info("Attempting to find AudD match")
        
        try:
            # Convert audio features to audio data
            audio_data = self._convert_features_to_audio(audio_features)
            if not audio_data:
                self.logger.warning("Failed to convert features to audio for AudD match")
                return None
            
            # Check if API key is available
            api_key = os.environ.get("AUDD_API_KEY")
            if not api_key:
                self.logger.warning("AudD API key not found")
                return None
            
            # Initialize AudD service
            audd_service = AuddService(api_key)
            
            # Send audio to AudD
            self.logger.info("Features converted to audio, sending to AudD")
            result = await audd_service.detect_track_with_retry(audio_data)
            
            if not result or not result.get("track"):
                self.logger.warning("No track information in AudD result")
                return None
            
            track_info = result["track"]
            title = track_info.get("title")
            artist_name = track_info.get("artist")
            album = track_info.get("album")
            
            # Capture additional information
            isrc = track_info.get("isrc")
            label = track_info.get("label")
            release_date = track_info.get("release_date")
            
            # Log the additional information
            self.logger.info(f"Track details - ISRC: {isrc}, Label: {label}, Release date: {release_date}")
            
            if not title or not artist_name:
                self.logger.warning("Missing title or artist in AudD result")
                return None
            
            # Check if artist exists
            artist = self.db_session.query(Artist).filter(Artist.name == artist_name).first()
            if not artist:
                self.logger.info(f"Created new artist: {artist_name}")
                artist = Artist(name=artist_name)
                
                # Add label information if available
                if label:
                    artist.label = label
                
                self.db_session.add(artist)
                self.db_session.flush()
            elif label and not artist.label:
                # Update artist label if it was previously unknown
                artist.label = label
                self.db_session.flush()
            
            # Check if track exists
            track = self.db_session.query(Track).filter(
                Track.title == title,
                Track.artist_id == artist.id
            ).first()
            
            # Calculate exact play duration
            play_duration = audio_features.get("play_duration", 0)
            self.logger.info(f"Exact play duration: {play_duration} seconds")
            
            # Convert duration to timedelta
            duration = timedelta(seconds=play_duration)
            
            # Generate fingerprint if not already available
            fingerprint = audio_features.get("fingerprint")
            if not fingerprint:
                fingerprint = self._extract_fingerprint(audio_features)
                self.logger.info(f"Generated new fingerprint: {fingerprint[:20]}...")
            
            if not track:
                # Create new track
                track = Track(
                    title=title,
                    artist_id=artist.id,
                    isrc=isrc,
                    album=album,
                    duration=duration,
                    fingerprint=fingerprint,
                    label=label,
                    release_date=release_date
                )
                self.db_session.add(track)
                self.db_session.flush()
                self.logger.info(f"Created new track: {title} by {artist_name} (ISRC: {isrc})")
            else:
                # Update track with new information if available
                if isrc and not track.isrc:
                    track.isrc = isrc
                if label and not track.label:
                    track.label = label
                if release_date and not track.release_date:
                    track.release_date = release_date
                if fingerprint and not track.fingerprint:
                    track.fingerprint = fingerprint
                
                track.updated_at = datetime.utcnow()
                self.db_session.flush()
                self.logger.info(f"Updated existing track: {title} by {artist_name} (ISRC: {isrc})")
            
            # Record play time if station_id is provided
            if station_id:
                self._record_play_time(station_id, track.id, play_duration)
            
            # Return result with enhanced information
            return {
                "track": {
                    "title": title,
                    "artist": artist_name,
                    "album": album,
                    "id": track_info.get("id", ""),
                    "isrc": isrc,
                    "label": label,
                    "release_date": release_date,
                    "fingerprint": fingerprint[:20] + "..." if fingerprint else None  # Truncated for logging
                },
                "confidence": 0.8,
                "source": "audd",
                "play_duration": play_duration
            }
        except Exception as e:
            self.logger.error(f"Error finding AudD match: {e}")
            return None
            
    def _record_play_time(self, station_id: int, track_id: int, play_duration: float):
        """
        Record the exact play time of a track on a station.
        
        Args:
            station_id: ID of the radio station
            track_id: ID of the track
            play_duration: Duration of play in seconds
        """
        try:
            # Get the station
            station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
            if not station:
                self.logger.warning(f"Station with ID {station_id} not found")
                return
            
            # Create a new track detection record
            detection = TrackDetection(
                track_id=track_id,
                station_id=station_id,
                detected_at=datetime.utcnow(),
                play_duration=timedelta(seconds=play_duration),
                confidence=0.8,
                detection_method="audd"
            )
            self.db_session.add(detection)
            
            # Update station track stats
            self._update_station_track_stats(station_id, track_id, timedelta(seconds=play_duration))
            
            self.db_session.commit()
            self.logger.info(f"Recorded play time for track ID {track_id} on station ID {station_id}: {play_duration} seconds")
        except Exception as e:
            self.logger.error(f"Error recording play time: {e}")
            self.db_session.rollback()

    def _extract_fingerprint(self, features: Dict[str, Any]) -> Optional[str]:
        """
        Extrait une empreinte digitale à partir des caractéristiques audio.
        
        Args:
            features: Caractéristiques audio extraites
            
        Returns:
            Empreinte digitale sous forme de chaîne de caractères ou None si l'extraction échoue
        """
        try:
            # Simuler l'extraction d'empreinte (à implémenter avec un algorithme réel)
            # Dans une implémentation réelle, on utiliserait un algorithme comme Chromaprint
            
            # Vérifier si l'empreinte est déjà calculée
            if "fingerprint" in features and features["fingerprint"]:
                return features["fingerprint"]
                
            # Extraire les caractéristiques pertinentes pour l'empreinte
            import json
            import hashlib
            
            # Utiliser les caractéristiques MFCC et chroma si disponibles
            fingerprint_data = {}
            if "mfcc_mean" in features:
                fingerprint_data["mfcc"] = features["mfcc_mean"]
            if "chroma_mean" in features:
                fingerprint_data["chroma"] = features["chroma_mean"]
            if "spectral_centroid_mean" in features:
                fingerprint_data["spectral"] = features["spectral_centroid_mean"]
                
            # Si aucune caractéristique pertinente n'est disponible, utiliser une valeur aléatoire
            if not fingerprint_data:
                import random
                fingerprint_data["random"] = random.random()
                
            # Convertir en chaîne JSON et calculer le hash MD5
            fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
            return hashlib.md5(fingerprint_str.encode('utf-8')).hexdigest()
            
        except Exception as e:
            logger.error(f"[TRACK_MANAGER] Error extracting fingerprint: {str(e)}")
            
            # En cas d'erreur, générer une empreinte aléatoire
            import random
            import hashlib
            random_data = str(random.random()).encode('utf-8')
            return hashlib.md5(random_data).hexdigest()

    def _convert_features_to_audio(self, features: Dict[str, Any]) -> Optional[bytes]:
        """
        Convertit les caractéristiques audio en données audio brutes.
        
        Args:
            features: Caractéristiques audio extraites
            
        Returns:
            Données audio brutes ou None en cas d'erreur
        """
        try:
            # Vérifier si les caractéristiques contiennent déjà des données audio brutes
            if "raw_audio" in features and features["raw_audio"] is not None:
                log_with_category(logger, "TRACK_MANAGER", "info", f"Using raw audio data from features ({len(features['raw_audio'])} bytes)")
                return features["raw_audio"]
            
            # Si nous avons un fingerprint, essayons de l'utiliser directement
            if "fingerprint" in features and features["fingerprint"] is not None:
                log_with_category(logger, "TRACK_MANAGER", "info", f"Using fingerprint from features")
                # Nous pourrions retourner directement le fingerprint, mais AcoustID s'attend à des données audio
                # Nous allons donc générer un signal audio plus représentatif
                
                # Utiliser une durée plus longue pour améliorer la détection
                sample_rate = 44100
                duration = min(30, features.get("play_duration", 30))  # Utiliser la durée réelle, max 30 secondes
                
                log_with_category(logger, "TRACK_MANAGER", "info", f"Generating audio representation with duration: {duration} seconds")
                
                # Créer un signal plus complexe basé sur les caractéristiques
                t = np.linspace(0, duration, int(sample_rate * duration), False)
                
                # Utiliser les caractéristiques spectrales si disponibles
                if "spectral_centroid_mean" in features and features["spectral_centroid_mean"] is not None:
                    # Utiliser le centroïde spectral comme fréquence de base
                    base_freq = max(220, min(880, features["spectral_centroid_mean"] * 10))
                else:
                    base_freq = 440  # La4 par défaut
                
                # Créer un signal plus riche avec plusieurs harmoniques
                signal = np.sin(2 * np.pi * base_freq * t)  # Fondamentale
                
                # Ajouter des harmoniques si nous avons des informations chromatiques
                if "chroma_mean" in features and features["chroma_mean"] is not None:
                    chroma = features["chroma_mean"]
                    for i, strength in enumerate(chroma):
                        if strength > 0.1:  # Seuil pour inclure cette note
                            # Ajouter cette note avec son amplitude relative
                            freq = base_freq * (2 ** (i/12))  # Échelle chromatique
                            signal += strength * np.sin(2 * np.pi * freq * t)
                
                # Normaliser
                signal = signal * 32767 / np.max(np.abs(signal))
                signal = signal.astype(np.int16)
                
                # Convertir en bytes
                audio_segment = AudioSegment(
                    signal.tobytes(),
                    frame_rate=sample_rate,
                    sample_width=2,
                    channels=1
                )
                
                buffer = io.BytesIO()
                audio_segment.export(buffer, format="mp3", bitrate="192k")
                
                log_with_category(logger, "TRACK_MANAGER", "info", f"Generated audio data: {buffer.getbuffer().nbytes} bytes")
                return buffer.getvalue()
            
            # Si nous n'avons ni données audio brutes ni fingerprint, générer un signal simple
            log_with_category(logger, "TRACK_MANAGER", "warning", "No raw audio or fingerprint available, generating simple signal")
            sample_rate = 44100
            duration = 10  # secondes (augmenté de 5 à 10 secondes)
            
            # Créer un signal sinusoïdal simple
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            signal = np.sin(2 * np.pi * 440 * t)  # 440 Hz = La4
            
            # Normaliser
            signal = signal * 32767 / np.max(np.abs(signal))
            signal = signal.astype(np.int16)
            
            # Convertir en bytes
            audio_segment = AudioSegment(
                signal.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,
                channels=1
            )
            
            buffer = io.BytesIO()
            audio_segment.export(buffer, format="mp3", bitrate="192k")
            
            return buffer.getvalue()
            
        except Exception as e:
            log_with_category(logger, "TRACK_MANAGER", "error", f"Erreur lors de la conversion des caractéristiques en audio: {str(e)}")
            import traceback
            log_with_category(logger, "TRACK_MANAGER", "error", f"Traceback: {traceback.format_exc()}")
            return None

    async def _get_or_create_artist(self, artist_name: str) -> Optional[Artist]:
        """
        Récupère ou crée un artiste dans la base de données.
        
        Args:
            artist_name: Nom de l'artiste
            
        Returns:
            Objet Artist ou None en cas d'erreur
        """
        try:
            if not artist_name or artist_name == "Unknown Artist":
                log_with_category(logger, "TRACK_MANAGER", "warning", "Invalid artist name, using 'Unknown Artist'")
                artist_name = "Unknown Artist"
            
            # Rechercher l'artiste dans la base de données
            artist = self.db_session.query(Artist).filter(Artist.name == artist_name).first()
            
            if artist:
                log_with_category(logger, "TRACK_MANAGER", "info", f"Artist found in database: {artist_name} (ID: {artist.id})")
                return artist
            
            # Créer un nouvel artiste
            log_with_category(logger, "TRACK_MANAGER", "info", f"Creating new artist: {artist_name}")
            artist = Artist(
                name=artist_name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db_session.add(artist)
            self.db_session.flush()
            
            log_with_category(logger, "TRACK_MANAGER", "info", f"New artist created: {artist_name} (ID: {artist.id})")
            return artist
        except Exception as e:
            log_with_category(logger, "TRACK_MANAGER", "error", f"Error creating artist: {e}")
            return None

    async def _get_or_create_track(self, title: str, artist_id: int, album: Optional[str] = None, 
                              isrc: Optional[str] = None, label: Optional[str] = None, 
                              release_date: Optional[str] = None) -> Optional[Track]:
        """
        Récupère ou crée une piste dans la base de données.
        
        Args:
            title: Titre de la piste
            artist_id: ID de l'artiste
            album: Nom de l'album (optionnel)
            isrc: Code ISRC (optionnel)
            label: Label (optionnel)
            release_date: Date de sortie (optionnel)
            
        Returns:
            Objet Track ou None en cas d'erreur
        """
        try:
            if not title or title == "Unknown Track":
                log_with_category(logger, "TRACK_MANAGER", "warning", "Invalid track title, using 'Unknown Track'")
                title = "Unknown Track"
            
            # Rechercher la piste dans la base de données
            query = self.db_session.query(Track).filter(
                Track.title == title,
                Track.artist_id == artist_id
            )
            
            # Ajouter l'ISRC à la recherche s'il est disponible
            if isrc:
                query = query.filter(Track.isrc == isrc)
            
            track = query.first()
            
            if track:
                log_with_category(logger, "TRACK_MANAGER", "info", f"Track found in database: {title} (ID: {track.id})")
                
                # Mettre à jour les informations manquantes
                updated = False
                
                if isrc and not track.isrc:
                    track.isrc = isrc
                    updated = True
                
                if label and not track.label:
                    track.label = label
                    updated = True
                
                if album and not track.album:
                    track.album = album
                    updated = True
                
                if release_date and not track.release_date:
                    track.release_date = release_date
                    updated = True
                
                if updated:
                    track.updated_at = datetime.utcnow()
                    self.db_session.flush()
                    log_with_category(logger, "TRACK_MANAGER", "info", f"Track updated: {title} (ID: {track.id})")
                
                return track
            
            # Créer une nouvelle piste
            log_with_category(logger, "TRACK_MANAGER", "info", f"Creating new track: {title}")
            track = Track(
                title=title,
                artist_id=artist_id,
                album=album,
                isrc=isrc,
                label=label,
                release_date=release_date,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db_session.add(track)
            self.db_session.flush()
            
            log_with_category(logger, "TRACK_MANAGER", "info", f"New track created: {title} (ID: {track.id})")
            return track
        except Exception as e:
            log_with_category(logger, "TRACK_MANAGER", "error", f"Error creating track: {e}")
            return None

    async def process_station_data(self, station_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process audio data from a station and detect tracks.
        
        Args:
            station_data: Dictionary containing station data with at least:
                - raw_audio: Raw audio data as bytes
                - station_id: ID of the station
                - station_name: Name of the station
                - timestamp: Timestamp of the recording
                
        Returns:
            Dictionary with detection results
        """
        station_id = station_data.get("station_id")
        station_name = station_data.get("station_name", "Unknown Station")
        
        log_with_category(logger, "TRACK_MANAGER", "info", f"Processing audio data from station {station_name} (ID: {station_id})")
        
        # Check if we have raw audio data
        if "raw_audio" not in station_data or not station_data["raw_audio"]:
            log_with_category(logger, "TRACK_MANAGER", "error", f"No raw audio data in station data for {station_name}")
            return {"success": False, "error": "No raw audio data in station data"}
        
        # Try to find a local match first
        log_with_category(logger, "TRACK_MANAGER", "info", f"Attempting to find local match for station {station_name}")
        
        # Extract features from raw audio
        audio_features = {
            "raw_audio": station_data["raw_audio"],
            "station_id": station_id,
            "station_name": station_name,
            "timestamp": station_data.get("timestamp")
        }
        
        # Try to find a local match
        local_match = await self.find_local_match(audio_features)
        if local_match:
            log_with_category(logger, "TRACK_MANAGER", "info", f"Local match found for station {station_name}: {local_match.get('title')} by {local_match.get('artist')}")
            
            # Add station data to the result
            local_match["station_id"] = station_id
            local_match["station_name"] = station_name
            local_match["timestamp"] = station_data.get("timestamp")
            
            # Start track detection
            track = self._get_or_create_track(local_match)
            if track:
                detection_result = self._start_track_detection(track, station_id, local_match)
                return {
                    "success": True,
                    "detection": detection_result,
                    "source": "local"
                }
            else:
                log_with_category(logger, "TRACK_MANAGER", "error", f"Failed to get or create track for local match for station {station_name}")
                return {"success": False, "error": "Failed to get or create track for local match"}
        
        # If no local match, try AcoustID
        log_with_category(logger, "TRACK_MANAGER", "info", f"No local match found for station {station_name}, trying AcoustID")
        
        # Initialize external service handler if not already initialized
        if not hasattr(self, "external_service_handler"):
            from .external_services import ExternalServiceHandler
            self.external_service_handler = ExternalServiceHandler(self.db_session)
            
            # Ensure acoustid_service is initialized
            if not hasattr(self.external_service_handler, "acoustid_service") or self.external_service_handler.acoustid_service is None:
                from .external_services import AcoustIDService
                self.external_service_handler.acoustid_service = AcoustIDService()
                log_with_category(logger, "TRACK_MANAGER", "info", f"AcoustID service initialized manually for station {station_name}")
        
        # Try to recognize with AcoustID
        acoustid_match = await self.external_service_handler.recognize_with_acoustid_from_station(station_data)
        if acoustid_match:
            log_with_category(logger, "TRACK_MANAGER", "info", f"AcoustID match found for station {station_name}: {acoustid_match.get('title')} by {acoustid_match.get('artist')}")
            
            # Start track detection
            track = self._get_or_create_track(acoustid_match)
            if track:
                detection_result = self._start_track_detection(track, station_id, acoustid_match)
                return {
                    "success": True,
                    "detection": detection_result,
                    "source": "acoustid"
                }
            else:
                log_with_category(logger, "TRACK_MANAGER", "error", f"Failed to get or create track for AcoustID match for station {station_name}")
                return {"success": False, "error": "Failed to get or create track for AcoustID match"}
        
        # If no AcoustID match, try other services (Audd, etc.)
        # ...
        
        # No match found
        log_with_category(logger, "TRACK_MANAGER", "info", f"No match found for station {station_name}")
        return {"success": False, "error": "No match found"} 