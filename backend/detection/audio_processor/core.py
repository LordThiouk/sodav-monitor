"""Core audio processing functionality for music detection."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import asyncio
import numpy as np
import io
from scipy.io.wavfile import write as write_wav
from backend.models.models import RadioStation, Track, TrackDetection
from backend.utils.logging_config import setup_logging, log_with_category
from backend.utils.analytics.stats_updater import StatsUpdater
from .stream_handler import StreamHandler
from .feature_extractor import FeatureExtractor
from .track_manager import TrackManager
from .station_monitor import StationMonitor

# Configure logging
logger = setup_logging(__name__)

class AudioProcessor:
    """Class for processing audio streams and detecting music."""
    
    def __init__(self, db_session: Session, sample_rate: int = 44100):
        """Initialize the audio processor.
        
        Args:
            db_session: SQLAlchemy database session
            sample_rate: Sampling frequency in Hz
            
        Raises:
            ValueError: If sample_rate is less than or equal to 0
        """
        if sample_rate <= 0:
            raise ValueError("Sample rate must be greater than 0")
        self.db = db_session
        self.sample_rate = sample_rate
        self.stream_handler = StreamHandler()
        self.feature_extractor = FeatureExtractor()
        self.track_manager = TrackManager(db_session)
        self.station_monitor = StationMonitor(db_session)
        self.stats_updater = StatsUpdater(db_session)
        
        log_with_category(logger, "AUDIO_PROCESSOR", "info", f"AudioProcessor initialized with sample_rate={sample_rate}")
        
    async def process_stream(self, audio_data: np.ndarray, station_id: Optional[int] = None, features: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Traite un segment audio pour détecter la présence de musique.
        
        Cette méthode implémente le processus de détection hiérarchique:
        1. Identifie le type de contenu (musique ou parole)
        2. Si c'est de la musique, tente une détection locale
        3. Si la détection locale échoue, tente une détection via MusicBrainz
        4. Si MusicBrainz échoue, tente une détection via AudD
        
        Args:
            audio_data: Données audio sous forme de tableau numpy
            station_id: ID de la station (optionnel)
            features: Caractéristiques audio pré-calculées (optionnel)
            
        Returns:
            Dictionnaire contenant les résultats de la détection avec:
            - type: "music" ou "speech"
            - source: "local", "musicbrainz", "audd" ou "unknown"
            - confidence: Score de confiance entre 0 et 1
            - track: Informations sur la piste (si détectée)
            - play_duration: Durée de lecture en secondes
            - station_id: ID de la station
        """
        try:
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Processing audio stream for station_id={station_id}")
            
            # 1. Extraire les caractéristiques audio si elles ne sont pas fournies
            if features is None:
                features = self.feature_extractor.extract_features(audio_data)
                
                # Stocker les données audio brutes dans les caractéristiques
                # Convertir le tableau numpy en bytes pour pouvoir l'envoyer aux services externes
                
                # Créer un buffer en mémoire
                buffer = io.BytesIO()
                
                # Normaliser les données audio si nécessaire
                if audio_data.dtype != np.int16:
                    audio_data_normalized = audio_data * 32767 / np.max(np.abs(audio_data))
                    audio_data_normalized = audio_data_normalized.astype(np.int16)
                else:
                    audio_data_normalized = audio_data
                
                # Écrire les données audio au format WAV dans le buffer
                write_wav(buffer, 44100, audio_data_normalized)
                
                # Récupérer les bytes du buffer
                buffer.seek(0)
                raw_audio = buffer.getvalue()
                
                # Stocker les données audio brutes dans les caractéristiques
                features["raw_audio"] = raw_audio
                log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Stored raw audio in features: {len(raw_audio)} bytes")
                
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Features extracted: {features.keys()}")
            
            # Récupérer la durée de lecture
            play_duration = features.get("play_duration", 0.0)
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Play duration: {play_duration} seconds")
            
            # Vérifier si c'est de la musique
            is_music = features.get("is_music", False)
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Is music: {is_music}")
            
            if not is_music:
                log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Speech detected for station_id={station_id}")
                return {
                    "type": "speech",
                    "confidence": 0.0,
                    "station_id": station_id,
                    "play_duration": play_duration
                }
            
            # 2. Détection hiérarchique
            # a) Détection locale
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Attempting local detection for station_id={station_id}")
            local_match = await self.track_manager.find_local_match(features)
            if local_match:
                log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Local match found: {local_match}")
                # Ajouter la durée de lecture au résultat
                local_match["play_duration"] = play_duration
                return {
                    "type": "music",
                    "source": "local",
                    "confidence": local_match["confidence"],
                    "track": local_match,
                    "station_id": station_id,
                    "play_duration": play_duration
                }
            
            # b) Détection MusicBrainz par métadonnées
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Local match not found, attempting MusicBrainz metadata detection for station_id={station_id}")
            
            # Extraire les métadonnées si disponibles
            metadata = {}
            if hasattr(audio_data, "metadata") and audio_data.metadata:
                metadata = audio_data.metadata
            
            # Ajouter les métadonnées aux caractéristiques
            features["metadata"] = metadata
            
            # Tenter la détection par métadonnées
            musicbrainz_match = await self.track_manager.find_musicbrainz_match(features)
            if musicbrainz_match:
                log_with_category(logger, "AUDIO_PROCESSOR", "info", f"MusicBrainz metadata match found: {musicbrainz_match}")
                # Ajouter la durée de lecture au résultat
                musicbrainz_match["play_duration"] = play_duration
                return {
                    "type": "music",
                    "source": "musicbrainz",
                    "confidence": musicbrainz_match["confidence"],
                    "track": musicbrainz_match["track"],
                    "station_id": station_id,
                    "play_duration": play_duration
                }
            
            # c) Détection AcoustID
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"MusicBrainz metadata match not found, attempting AcoustID detection for station_id={station_id}")
            acoustid_match = await self.track_manager.find_acoustid_match(features)
            if acoustid_match:
                log_with_category(logger, "AUDIO_PROCESSOR", "info", f"AcoustID match found: {acoustid_match}")
                # Ajouter la durée de lecture au résultat
                acoustid_match["play_duration"] = play_duration
                
                # S'assurer que les changements sont validés dans la base de données
                if not station_id and hasattr(self.track_manager, 'db_session'):
                    try:
                        # Vérifier si la session a des changements en attente
                        if self.track_manager.db_session.dirty or self.track_manager.db_session.new:
                            self.track_manager.db_session.commit()
                            log_with_category(logger, "AUDIO_PROCESSOR", "info", "Committed changes to database after AcoustID detection")
                    except Exception as e:
                        log_with_category(logger, "AUDIO_PROCESSOR", "error", f"Error committing changes: {e}")
                        self.track_manager.db_session.rollback()
                
                return {
                    "type": "music",
                    "source": "acoustid",
                    "confidence": acoustid_match["confidence"],
                    "track": acoustid_match["track"],
                    "station_id": station_id,
                    "play_duration": play_duration
                }
            
            # d) Détection AudD
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"AcoustID match not found, attempting AudD detection for station_id={station_id}")
            audd_match = await self.track_manager.find_audd_match(features)
            if audd_match:
                log_with_category(logger, "AUDIO_PROCESSOR", "info", f"AudD match found: {audd_match}")
                # Ajouter la durée de lecture au résultat
                audd_match["play_duration"] = play_duration
                
                # S'assurer que les changements sont validés dans la base de données
                if not station_id and hasattr(self.track_manager, 'db_session'):
                    try:
                        # Vérifier si la session a des changements en attente
                        if self.track_manager.db_session.dirty or self.track_manager.db_session.new:
                            self.track_manager.db_session.commit()
                            log_with_category(logger, "AUDIO_PROCESSOR", "info", "Committed changes to database after AudD detection")
                    except Exception as e:
                        log_with_category(logger, "AUDIO_PROCESSOR", "error", f"Error committing changes: {e}")
                        self.track_manager.db_session.rollback()
                
                return {
                    "type": "music",
                    "source": "audd",
                    "confidence": audd_match["confidence"],
                    "track": audd_match["track"],
                    "station_id": station_id,
                    "play_duration": play_duration
                }
            
            # Aucune correspondance trouvée
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"No match found for station_id={station_id}")
            return {
                "type": "music",
                "source": "unknown",
                "confidence": 0.0,
                "station_id": station_id,
                "play_duration": play_duration
            }
        except Exception as e:
            log_with_category(logger, "AUDIO_PROCESSOR", "error", f"Error processing audio stream: {e}")
            import traceback
            log_with_category(logger, "AUDIO_PROCESSOR", "error", f"Traceback: {traceback.format_exc()}")
            return {
                "type": "error",
                "error": str(e),
                "station_id": station_id
            }
    
    async def start_monitoring(self, station_id: int) -> bool:
        """Start monitoring a station.
        
        Args:
            station_id: ID of the station to monitor
            
        Returns:
            True if monitoring started successfully
        """
        try:
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Starting monitoring for station_id={station_id}")
            return await self.station_monitor.start_monitoring(
                self.stream_handler,
                self.feature_extractor,
                self.track_manager
            )
        except Exception as e:
            log_with_category(logger, "AUDIO_PROCESSOR", "error", f"Error starting monitoring: {str(e)}")
            return False
    
    async def stop_monitoring(self, station_id: int) -> bool:
        """Stop monitoring a station.
        
        Args:
            station_id: ID of the station
            
        Returns:
            True if monitoring stopped successfully
        """
        try:
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Stopping monitoring for station_id={station_id}")
            return await self.station_monitor.stop_monitoring()
        except Exception as e:
            log_with_category(logger, "AUDIO_PROCESSOR", "error", f"Error stopping monitoring: {str(e)}")
            return False
    
    def _check_memory_usage(self) -> bool:
        """Check memory usage.
        
        Returns:
            True if memory usage is acceptable
        """
        # TODO: Implement memory usage check
        log_with_category(logger, "AUDIO_PROCESSOR", "debug", "Checking memory usage")
        return True

    def detect_music_in_stream(self, audio_data: np.ndarray) -> Tuple[bool, float]:
        """Process an audio segment to detect the presence of music.
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            Tuple containing:
                - bool: True if music is detected
                - float: Confidence score between 0 and 1
                
        Raises:
            ValueError: If audio_data is empty
            TypeError: If audio_data is not a np.ndarray
        """
        if not isinstance(audio_data, np.ndarray):
            raise TypeError("Audio data must be a numpy array")
        if audio_data.size == 0:
            raise ValueError("Audio data cannot be empty")
            
        # Detection simulation for now
        confidence = np.random.random()
        is_music = confidence > 0.5
        
        logger.debug(f"Audio processing: music={is_music}, confidence={confidence:.2f}")
        return is_music, confidence
        
    def extract_features(self, audio_data: np.ndarray) -> np.ndarray:
        """Extract audio features for fingerprinting.
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            Numpy array of extracted features
            
        Raises:
            ValueError: If audio_data is empty
            TypeError: If audio_data is not a np.ndarray
        """
        if not isinstance(audio_data, np.ndarray):
            raise TypeError("Audio data must be a numpy array")
        if audio_data.size == 0:
            raise ValueError("Audio data cannot be empty")
            
        # Feature extraction simulation
        features = np.random.random((128,))
        logger.debug(f"Features extracted: shape={features.shape}")
        return features
        
    def match_fingerprint(self, features: np.ndarray, database: List[np.ndarray]) -> Optional[int]:
        """Compare a fingerprint with a database.
        
        Args:
            features: Features of the audio to identify
            database: List of reference fingerprints
            
        Returns:
            Index of the found match or None
            
        Raises:
            ValueError: If features don't have the correct shape
            TypeError: If arguments are not of the correct type
        """
        if not isinstance(features, np.ndarray):
            raise TypeError("Features must be a numpy array")
        if not isinstance(database, list):
            raise TypeError("Database must be a list")
        if features.shape != (128,):
            raise ValueError("Features must have shape (128,)")
            
        # Match simulation
        if len(database) > 0 and np.random.random() > 0.5:
            match_idx = np.random.randint(0, len(database))
            logger.info(f"Match found at index {match_idx}")
            return match_idx
        return None

    async def detect_music(self, audio_features, station_id=None, metadata=None):
        """
        Détecte la musique à partir des caractéristiques audio.
        
        Args:
            audio_features: Caractéristiques audio extraites
            station_id: ID de la station (optionnel)
            metadata: Métadonnées de la piste (optionnel)
            
        Returns:
            Dict contenant les informations de détection
        """
        try:
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Detecting music for station_id={station_id}")
            
            # Vérifier si les caractéristiques audio sont valides
            if not audio_features:
                log_with_category(logger, "AUDIO_PROCESSOR", "warning", "No audio features provided for music detection")
                return {"error": "No audio features provided"}
            
            # Rechercher une correspondance locale
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Attempting to find local match for station_id={station_id}")
            local_match = await self.track_manager.find_local_match(audio_features)
            
            if local_match and local_match.get("confidence", 0) >= self.local_match_threshold:
                log_with_category(logger, "AUDIO_PROCESSOR", "info", 
                    f"Local match found with sufficient confidence: {local_match.get('title')} by {local_match.get('artist')}, "
                    f"confidence: {local_match.get('confidence')}"
                )
                
                # Enregistrer la détection dans la base de données
                detection_id = await self._save_detection(station_id, audio_features, local_match)
                
                # Mettre à jour les statistiques
                if station_id and detection_id:
                    await self._update_stats(station_id, local_match.get("track_id"), audio_features.get("play_duration", 0))
                
                return {
                    "status": "success",
                    "match_type": "local",
                    "track": local_match,
                    "detection_id": detection_id
                }
            
            # Si aucune correspondance locale avec confiance suffisante n'est trouvée, essayer AcoustID
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"Local match not found with sufficient confidence, attempting AcoustID detection for station_id={station_id}")
            acoustid_match = await self.track_manager.find_acoustid_match(audio_features, station_id)
            
            if acoustid_match:
                log_with_category(logger, "AUDIO_PROCESSOR", "info", 
                    f"AcoustID match found: {acoustid_match.get('title')} by {acoustid_match.get('artist')}, "
                    f"confidence: {acoustid_match.get('confidence')}"
                )
                
                # Mettre à jour les statistiques
                if station_id and acoustid_match.get("track_id"):
                    await self._update_stats(station_id, acoustid_match.get("track_id"), audio_features.get("play_duration", 0))
                
                return {
                    "status": "success",
                    "match_type": "acoustid",
                    "track": acoustid_match,
                    "detection_id": acoustid_match.get("detection_id")
                }
            
            # Si aucune correspondance n'est trouvée avec AcoustID, essayer AudD
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"AcoustID match not found, attempting AudD detection for station_id={station_id}")
            audd_match = await self.track_manager.find_audd_match(audio_features, station_id)
            
            if audd_match:
                log_with_category(logger, "AUDIO_PROCESSOR", "info", 
                    f"AudD match found: {audd_match.get('title')} by {audd_match.get('artist')}, "
                    f"confidence: {audd_match.get('confidence')}"
                )
                
                # Mettre à jour les statistiques
                if station_id and audd_match.get("track_id"):
                    await self._update_stats(station_id, audd_match.get("track_id"), audio_features.get("play_duration", 0))
                
                return {
                    "status": "success",
                    "match_type": "audd",
                    "track": audd_match,
                    "detection_id": audd_match.get("detection_id")
                }
            
            # Si aucune correspondance n'est trouvée, retourner un résultat vide
            log_with_category(logger, "AUDIO_PROCESSOR", "info", f"No match found for station_id={station_id}")
            return {
                "status": "no_match",
                "match_type": None,
                "track": None,
                "detection_id": None
            }
            
        except Exception as e:
            log_with_category(logger, "AUDIO_PROCESSOR", "error", f"Error detecting music: {str(e)}")
            import traceback
            log_with_category(logger, "AUDIO_PROCESSOR", "error", f"Traceback: {traceback.format_exc()}")
            return {"error": str(e)}

    async def _update_stats(self, station_id: int, track_id: int, play_duration: float):
        """
        Met à jour les statistiques après une détection réussie.
        
        Cette méthode utilise le StatsUpdater pour mettre à jour toutes les statistiques
        pertinentes, y compris les statistiques de piste, d'artiste et de station.
        
        Args:
            station_id: ID de la station radio
            track_id: ID de la piste détectée
            play_duration: Durée de lecture en secondes
            
        Returns:
            None
        """
        try:
            # Convertir la durée de lecture en timedelta
            play_duration_td = timedelta(seconds=play_duration)
            
            # Récupérer la piste
            track = self.db.query(Track).filter(Track.id == track_id).first()
            if not track:
                log_with_category(logger, "AUDIO_PROCESSOR", "warning", f"Track with ID {track_id} not found, cannot update stats")
                return
                
            # Créer un dictionnaire de résultat de détection pour StatsUpdater
            detection_result = {
                "track_id": track_id,
                "confidence": 0.8,  # Valeur par défaut
                "detection_method": "audd"  # Méthode par défaut
            }
            
            # Utiliser le StatsUpdater pour mettre à jour toutes les statistiques
            log_with_category(logger, "AUDIO_PROCESSOR", "info", 
                f"Updating stats for track_id={track_id}, station_id={station_id}, play_duration={play_duration} seconds")
            
            self.stats_updater.update_all_stats(detection_result, station_id, track, play_duration_td)
            log_with_category(logger, "AUDIO_PROCESSOR", "info", "Stats updated successfully")
            
        except Exception as e:
            log_with_category(logger, "AUDIO_PROCESSOR", "error", f"Error updating stats: {str(e)}")
            import traceback
            log_with_category(logger, "AUDIO_PROCESSOR", "error", f"Traceback: {traceback.format_exc()}") 