"""Module for managing track detection and storage."""

import logging
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models.models import Track, TrackDetection, RadioStation, StationTrackStats, Artist, Fingerprint
from backend.utils.logging_config import setup_logging, log_with_category
from backend.utils.analytics.stats_updater import StatsUpdater
import numpy as np
from backend.detection.audio_processor.external_services import MusicBrainzService, AuddService, ExternalServiceHandler, AcoustIDService
import io
from pydub import AudioSegment
import hashlib
import json
from sqlalchemy import select, and_, or_
from sqlalchemy import inspect

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
        
        # Initialize external services
        acoustid_api_key = os.environ.get("ACOUSTID_API_KEY")
        audd_api_key = os.environ.get("AUDD_API_KEY")
        
        # Initialize AcoustID service
        if acoustid_api_key:
            try:
                self.acoustid_service = AcoustIDService(acoustid_api_key)
                self.logger.info("AcoustID service initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize AcoustID service: {e}")
                self.acoustid_service = None
        else:
            self.logger.warning("ACOUSTID_API_KEY not found in environment variables")
            self.acoustid_service = None
        
        # Initialize AudD service
        if audd_api_key:
            try:
                self.audd_service = AuddService(audd_api_key)
                self.logger.info("AudD service initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize AudD service: {e}")
                self.audd_service = None
        else:
            self.logger.warning("AUDD_API_KEY not found in environment variables")
            self.audd_service = None
    
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
            track = await self._get_or_create_track(features)
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
        """
        Termine la piste en cours pour une station donnée.
        """
        if station_id in self.current_tracks:
            current_track = self.current_tracks[station_id]
            
            # Calculer la durée de lecture
            start_time = current_track.get("start_time")
            if start_time:
                end_time = datetime.now()
                play_duration = end_time - start_time
                
                # Mettre à jour les statistiques
                track_id = current_track.get("track_id")
                if track_id:
                    self._update_station_track_stats(station_id, track_id, play_duration)
            
            # Supprimer la piste en cours
            del self.current_tracks[station_id]
            
            return current_track
        return None

    async def _get_or_create_artist(self, artist_name: str) -> Optional[int]:
        """
        Récupère ou crée un artiste dans la base de données.
        
        Args:
            artist_name: Nom de l'artiste
            
        Returns:
            ID de l'artiste ou None si échec
        """
        if not artist_name:
            log_with_category(logger, "TRACK_MANAGER", "warning", f"Empty artist name")
            # Utiliser "Unknown Artist" comme nom par défaut
            artist_name = "Unknown Artist"
            
        try:
            # Vérifier si l'artiste existe déjà
            artist = self.db_session.query(Artist).filter(Artist.name == artist_name).first()
            
            if artist:
                log_with_category(logger, "TRACK_MANAGER", "debug", f"Artist found in database: {artist_name} (ID: {artist.id})")
                return artist.id
                
            # Créer un nouvel artiste
            new_artist = Artist(name=artist_name)
            self.db_session.add(new_artist)
            self.db_session.commit()
            
            log_with_category(logger, "TRACK_MANAGER", "info", f"Created new artist: {artist_name} (ID: {new_artist.id})")
            return new_artist.id
            
        except Exception as e:
            log_with_category(logger, "TRACK_MANAGER", "error", f"Error creating artist: {str(e)}")
            self.db_session.rollback()
            return None

    async def _get_or_create_track(self, title: str = None, artist_name: str = None, features: Optional[Dict[str, Any]] = None) -> Optional[Track]:
        """
        Récupère ou crée une piste dans la base de données.
        
        Args:
            title: Titre de la piste
            artist_name: Nom de l'artiste
            features: Caractéristiques supplémentaires (album, isrc, label, etc.)
            
        Returns:
            Objet Track créé ou récupéré, ou None en cas d'erreur
        """
        try:
            if not title or not artist_name:
                self.logger.error("Title and artist_name are required")
                return None
            
            self.logger.info(f"Getting or creating track: {title} by {artist_name}")
            
            # Extraire les métadonnées des caractéristiques
            album = None
            isrc = None
            label = None
            release_date = None
            fingerprint_hash = None
            fingerprint_raw = None
            chromaprint = None
            
            if features:
                # Extraire l'album
                album = features.get("album")
                
                # Extraire l'ISRC - vérifier plusieurs sources possibles
                isrc = features.get("isrc")
                
                # Vérifier dans Apple Music
                if not isrc and "apple_music" in features and features["apple_music"]:
                    if "isrc" in features["apple_music"]:
                        isrc = features["apple_music"]["isrc"]
                        self.logger.info(f"ISRC found in Apple Music: {isrc}")
                
                # Vérifier dans Spotify
                if not isrc and "spotify" in features and features["spotify"]:
                    if "external_ids" in features["spotify"] and "isrc" in features["spotify"]["external_ids"]:
                        isrc = features["spotify"]["external_ids"]["isrc"]
                        self.logger.info(f"ISRC found in Spotify: {isrc}")
                
                # Vérifier dans Deezer
                if not isrc and "deezer" in features and features["deezer"]:
                    if "isrc" in features["deezer"]:
                        isrc = features["deezer"]["isrc"]
                        self.logger.info(f"ISRC found in Deezer: {isrc}")
                
                # Extraire le label
                label = features.get("label")
                
                # Extraire la date de sortie
                release_date = features.get("release_date")
                
                # Extraire l'empreinte digitale
                fingerprint_hash, fingerprint_raw = self._extract_fingerprint(features)
                
                # Extraire l'empreinte Chromaprint
                chromaprint = features.get("chromaprint")
            
            # Récupérer ou créer l'artiste
            artist_id = await self._get_or_create_artist(artist_name)
            
            if not artist_id:
                self.logger.error(f"Failed to get or create artist: {artist_name}")
                return None
            
            # Log des informations extraites
            self.logger.info(f"Track metadata - Title: {title}, Artist: {artist_name}, Album: {album}, ISRC: {isrc}, Label: {label}, Release date: {release_date}")
            if fingerprint_hash:
                self.logger.info(f"Fingerprint extracted: {fingerprint_hash[:20]}...")
            
            # Rechercher la piste dans la base de données
            query = self.db_session.query(Track).filter(
                Track.title == title,
                Track.artist_id == artist_id
            )
            
            # Ajouter l'ISRC à la recherche s'il est disponible
            if isrc:
                self.logger.info(f"Searching for track with ISRC: {isrc}")
                query = self.db_session.query(Track).filter(
                    or_(
                        and_(
                            Track.title == title,
                            Track.artist_id == artist_id
                        ),
                        Track.isrc == isrc
                    )
                )
            
            # Ajouter le fingerprint à la recherche s'il est disponible
            if fingerprint_hash:
                self.logger.info(f"Searching for track with fingerprint: {fingerprint_hash[:20]}...")
                
                # Vérifier si la table fingerprints existe
                from sqlalchemy import inspect
                inspector = inspect(self.db_session.bind)
                if "fingerprints" in inspector.get_table_names():
                    # Rechercher dans la table fingerprints
                    from backend.models.models import Fingerprint
                    fingerprint = self.db_session.query(Fingerprint).filter_by(hash=fingerprint_hash).first()
                    
                    if fingerprint:
                        # Si l'empreinte existe, récupérer la piste associée
                        track = self.db_session.query(Track).filter_by(id=fingerprint.track_id).first()
                        if track:
                            self.logger.info(f"Track found by fingerprint in fingerprints table: {track.title}")
                            return track
            
            # Fallback: rechercher dans la colonne fingerprint de la table tracks
            query = self.db_session.query(Track).filter(
                or_(
                    and_(
                        Track.title == title,
                        Track.artist_id == artist_id
                    ),
                    Track.isrc == isrc,
                    Track.fingerprint == fingerprint_hash
                )
            )
            
            track = query.first()
            
            # Utiliser _execute_with_transaction pour gérer les transactions
            if track:
                # Mettre à jour la piste existante avec les nouvelles informations
                def update_track():
                    updated = False
                    
                    if isrc and not track.isrc:
                        track.isrc = isrc
                        updated = True
                        self.logger.info(f"Updated track with ISRC: {isrc}")
                    
                    if label and not track.label:
                        track.label = label
                        updated = True
                        self.logger.info(f"Updated track with label: {label}")
                    
                    if album and not track.album:
                        track.album = album
                        updated = True
                        self.logger.info(f"Updated track with album: {album}")
                    
                    if release_date and not track.release_date:
                        track.release_date = release_date
                        updated = True
                        self.logger.info(f"Updated track with release date: {release_date}")
                    
                    if fingerprint_hash and not track.fingerprint:
                        track.fingerprint = fingerprint_hash
                        track.fingerprint_raw = fingerprint_raw
                        updated = True
                        self.logger.info(f"Updated track with fingerprint: {fingerprint_hash[:20]}...")
                    
                    if chromaprint and not track.chromaprint:
                        track.chromaprint = chromaprint
                        updated = True
                        self.logger.info(f"Updated track with chromaprint: {chromaprint[:20]}...")
                    
                    # Ajouter l'empreinte à la table fingerprints si elle existe
                    if fingerprint_hash:
                        from sqlalchemy import inspect
                        inspector = inspect(self.db_session.bind)
                        if "fingerprints" in inspector.get_table_names():
                            from backend.models.models import Fingerprint
                            
                            # Vérifier si l'empreinte existe déjà pour cette piste
                            existing_fingerprint = self.db_session.query(Fingerprint).filter_by(
                                track_id=track.id,
                                hash=fingerprint_hash
                            ).first()
                            
                            if not existing_fingerprint:
                                new_fingerprint = Fingerprint(
                                    track_id=track.id,
                                    hash=fingerprint_hash,
                                    raw_data=fingerprint_raw,
                                    offset=0.0,  # Position par défaut
                                    algorithm="md5"  # Algorithme par défaut
                                )
                                self.db_session.add(new_fingerprint)
                                updated = True
                                self.logger.info(f"Added fingerprint to fingerprints table for existing track {track.id}")
                    
                    if updated:
                        track.updated_at = datetime.utcnow()
                        self.db_session.flush()
                        self.logger.info(f"Track updated: {track.title} (ID: {track.id})")
                    
                    return track
                
                return self._execute_with_transaction(update_track)
            else:
                # Créer une nouvelle piste
                def create_track():
                    self.logger.info(f"Creating new track: {title} by {artist_name}")
                    
                    # Créer une nouvelle piste
                    track = Track(
                        title=title,
                        artist_id=artist_id,
                        isrc=isrc,
                        label=label,
                        album=album,
                        release_date=release_date,
                        fingerprint=fingerprint_hash,
                        fingerprint_raw=fingerprint_raw,
                        chromaprint=chromaprint
                    )
                    
                    self.db_session.add(track)
                    self.db_session.flush()
                    
                    # Ajouter l'empreinte à la table fingerprints si elle existe
                    if fingerprint_hash:
                        from sqlalchemy import inspect
                        inspector = inspect(self.db_session.bind)
                        if "fingerprints" in inspector.get_table_names():
                            from backend.models.models import Fingerprint
                            new_fingerprint = Fingerprint(
                                track_id=track.id,
                                hash=fingerprint_hash,
                                raw_data=fingerprint_raw,
                                offset=0.0,  # Position par défaut
                                algorithm="md5"  # Algorithme par défaut
                            )
                            self.db_session.add(new_fingerprint)
                            self.logger.info(f"Added fingerprint to fingerprints table for new track {track.id}")
                    
                    # Créer les statistiques de piste
                    from backend.models.models import TrackStats
                    track_stats = TrackStats(track_id=track.id)
                    self.db_session.add(track_stats)
                    
                    self.db_session.flush()
                    self.logger.info(f"New track created: {track.title} (ID: {track.id})")
                    
                    return track
                
                return self._execute_with_transaction(create_track)
        
        except Exception as e:
            self.logger.error(f"Error in _get_or_create_track: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
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
            # Vérifier si nous avons des empreintes Chromaprint
            if "chromaprint" in features1 and "chromaprint" in features2:
                return self._calculate_chromaprint_similarity(features1["chromaprint"], features2["chromaprint"])
            
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
            
    def _calculate_chromaprint_similarity(self, chromaprint1: str, chromaprint2: str) -> float:
        """
        Calcule la similarité entre deux empreintes Chromaprint.
        
        Args:
            chromaprint1: Première empreinte Chromaprint (chaîne hexadécimale)
            chromaprint2: Deuxième empreinte Chromaprint (chaîne hexadécimale)
            
        Returns:
            Score de similarité entre 0.0 et 1.0
        """
        try:
            # Vérifier que les empreintes sont valides
            if not chromaprint1 or not chromaprint2:
                return 0.0
                
            # Convertir les empreintes en séquences binaires
            try:
                # Prendre les 32 premiers caractères pour une comparaison rapide
                # Les empreintes Chromaprint sont généralement très longues
                cp1 = chromaprint1[:32]
                cp2 = chromaprint2[:32]
                
                # Calculer la distance de Hamming (nombre de bits différents)
                distance = sum(c1 != c2 for c1, c2 in zip(cp1, cp2))
                
                # Normaliser par la longueur
                max_length = max(len(cp1), len(cp2))
                if max_length == 0:
                    return 0.0
                    
                # Convertir la distance en similarité (1.0 = identique, 0.0 = complètement différent)
                similarity = 1.0 - (distance / max_length)
                
                self.logger.debug(f"Chromaprint similarity: {similarity:.4f} (distance: {distance}, length: {max_length})")
                return similarity
                
            except Exception as e:
                self.logger.warning(f"Erreur lors de la comparaison des empreintes Chromaprint: {str(e)}")
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de similarité Chromaprint: {str(e)}")
            return 0.0
            
    # Implémentation des méthodes manquantes
    
    async def find_local_match(self, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Recherche une correspondance locale dans la base de données en utilisant la table fingerprints."""
        try:
            logger.info("[TRACK_MANAGER] Attempting to find local match")
            
            # Vérifier si une empreinte Chromaprint est disponible
            chromaprint = features.get("chromaprint")
            if chromaprint:
                logger.info("[TRACK_MANAGER] Chromaprint fingerprint available, searching with it first")
                
                # Vérifier si la table fingerprints existe
                inspector = inspect(self.db_session.bind)
                if "fingerprints" in inspector.get_table_names():
                    # Rechercher d'abord dans la table fingerprints avec l'algorithme chromaprint
                    from backend.models.models import Fingerprint
                    
                    # Utiliser les 32 premiers caractères comme hash pour la recherche
                    chromaprint_hash = chromaprint[:32] if len(chromaprint) > 32 else chromaprint
                    
                    # Rechercher une correspondance exacte avec l'algorithme chromaprint
                    fingerprint = self.db_session.query(Fingerprint).filter_by(
                        hash=chromaprint_hash,
                        algorithm="chromaprint"
                    ).first()
                    
                    if fingerprint:
                        # Récupérer la piste associée
                        track = self.db_session.query(Track).filter_by(id=fingerprint.track_id).first()
                        
                        if track:
                            # Récupérer le nom de l'artiste via la relation
                            artist_name = track.artist.name if track.artist else "Unknown Artist"
                            logger.info(f"[TRACK_MANAGER] Exact Chromaprint match found: {track.title} by {artist_name}")
                            return {
                                "title": track.title,
                                "artist": artist_name,
                                "album": track.album,
                                "id": track.id,
                                "isrc": track.isrc,
                                "label": track.label,
                                "release_date": track.release_date,
                                "fingerprint": "chromaprint:" + chromaprint_hash[:20] + "...",
                                "confidence": 1.0,
                                "source": "local"
                            }
                    
                    # Si pas de correspondance exacte, rechercher dans la colonne chromaprint de la table tracks
                    track = self.db_session.query(Track).filter_by(chromaprint=chromaprint).first()
                    if track:
                        # Récupérer le nom de l'artiste via la relation
                        artist_name = track.artist.name if track.artist else "Unknown Artist"
                        logger.info(f"[TRACK_MANAGER] Exact Chromaprint match found in tracks table: {track.title} by {artist_name}")
                        return {
                            "title": track.title,
                            "artist": artist_name,
                            "album": track.album,
                            "id": track.id,
                            "isrc": track.isrc,
                            "label": track.label,
                            "release_date": track.release_date,
                            "fingerprint": "chromaprint:" + chromaprint[:20] + "...",
                            "confidence": 1.0,
                            "source": "local"
                        }
            
            # Extraire l'empreinte audio standard
            fingerprint_hash, fingerprint_raw = self._extract_fingerprint(features)
            if not fingerprint_hash:
                logger.warning("[TRACK_MANAGER] Failed to extract fingerprint for local match")
                return None
            
            logger.info("[TRACK_MANAGER] Fingerprint extracted, searching in database")
            
            # Vérifier si la table fingerprints existe
            inspector = inspect(self.db_session.bind)
            if "fingerprints" in inspector.get_table_names():
                # Rechercher d'abord dans la table fingerprints (nouvelle méthode)
                from backend.models.models import Fingerprint
                
                # Rechercher une correspondance exacte
                fingerprint = self.db_session.query(Fingerprint).filter_by(hash=fingerprint_hash).first()
                
                if fingerprint:
                    # Récupérer la piste associée
                    track = self.db_session.query(Track).filter_by(id=fingerprint.track_id).first()
                    
                    if track:
                        # Récupérer le nom de l'artiste via la relation
                        artist_name = track.artist.name if track.artist else "Unknown Artist"
                        logger.info(f"[TRACK_MANAGER] Exact fingerprint match found in fingerprints table: {track.title} by {artist_name}")
                        return {
                            "title": track.title,
                            "artist": artist_name,
                            "album": track.album,
                            "id": track.id,
                            "isrc": track.isrc,
                            "label": track.label,
                            "release_date": track.release_date,
                            "fingerprint": fingerprint_hash[:20] + "..." if fingerprint_hash else None,
                            "confidence": 1.0,
                            "source": "local"
                        }
                
                # Si pas de correspondance exacte, on pourrait implémenter une recherche par similarité
                # en comparant avec toutes les empreintes de la table fingerprints
                # Cette partie pourrait être optimisée avec des algorithmes de recherche plus avancés
                
                logger.info("[TRACK_MANAGER] No exact match found in fingerprints table, trying similarity search")
                
                # Récupérer toutes les empreintes
                all_fingerprints = self.db_session.query(Fingerprint).all()
                
                best_match = None
                best_score = 0.0
                
                for fp in all_fingerprints:
                    # Calculer la similarité entre les empreintes
                    similarity = self._calculate_similarity(
                        {"fingerprint": fingerprint_hash}, 
                        {"fingerprint": fp.hash}
                    )
                    
                    if similarity > best_score and similarity > 0.7:  # Seuil de similarité
                        best_score = similarity
                        best_match = fp
                
                if best_match:
                    # Récupérer la piste associée
                    track = self.db_session.query(Track).filter_by(id=best_match.track_id).first()
                    
                    if track:
                        # Récupérer le nom de l'artiste via la relation
                        artist_name = track.artist.name if track.artist else "Unknown Artist"
                        logger.info(f"[TRACK_MANAGER] Similar fingerprint match found: {track.title} by {artist_name} (score: {best_score})")
                        return {
                            "title": track.title,
                            "artist": artist_name,
                            "album": track.album,
                            "id": track.id,
                            "isrc": track.isrc,
                            "label": track.label,
                            "release_date": track.release_date,
                            "fingerprint": best_match.hash[:20] + "..." if best_match.hash else None,
                            "confidence": best_score,
                            "source": "local"
                        }
            
            # Fallback: rechercher dans la colonne fingerprint de la table tracks (ancienne méthode)
            logger.info("[TRACK_MANAGER] Falling back to legacy fingerprint search in tracks table")
            
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
                Track.fingerprint == fingerprint_hash
            ).first()
            
            if exact_match:
                # Récupérer le nom de l'artiste via la relation
                artist_name = exact_match.artist.name if exact_match.artist else "Unknown Artist"
                logger.info(f"[TRACK_MANAGER] Exact fingerprint match found in tracks table: {exact_match.title} by {artist_name}")
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
                        {"fingerprint": fingerprint_hash}, 
                        {"fingerprint": track.fingerprint}
                    )
                    logger.debug(f"[TRACK_MANAGER] Similarity with track {track.id} ({track.title}): {similarity}")
                    
                    if similarity > best_score and similarity > 0.7:  # Seuil de similarité
                        best_score = similarity
                        best_match = track
            
            if best_match:
                # Récupérer le nom de l'artiste via la relation
                artist_name = best_match.artist.name if best_match.artist else "Unknown Artist"
                logger.info(f"[TRACK_MANAGER] Local match found in tracks table: {best_match.title} by {artist_name} (score: {best_score})")
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
            logger.error(f"[TRACK_MANAGER] Error in find_local_match: {str(e)}")
            import traceback
            logger.error(f"[TRACK_MANAGER] Traceback: {traceback.format_exc()}")
            return None
    
    async def find_acoustid_match(self, audio_features: Dict[str, Any], station_id=None) -> Optional[Dict[str, Any]]:
        """
        Recherche une correspondance avec le service AcoustID.
        
        Args:
            audio_features: Caractéristiques audio extraites
            station_id: ID de la station (optionnel)
            
        Returns:
            Dictionnaire avec les informations de la piste ou None si aucune correspondance
        """
        if not self.acoustid_service:
            self.logger.warning("AcoustID service not initialized")
            return None
        
        try:
            # Convertir les caractéristiques en audio
            audio_data = self._convert_features_to_audio(audio_features)
            if not audio_data:
                self.logger.error("Failed to convert features to audio for AcoustID detection")
                return None
            
            # Détecter avec AcoustID
            self.logger.info(f"Detecting with AcoustID for station_id={station_id}")
            result = await self.acoustid_service.detect_track_with_retry(audio_data, max_retries=3)
            
            if not result:
                self.logger.info("No AcoustID match found")
                return None
            
            # Extraire les informations de base
            title = result.get("title", "Unknown Track")
            artist_name = result.get("artist", "Unknown Artist")
            album = result.get("album", "Unknown Album")
            
            # Extraire l'ISRC
            isrc = result.get("isrc")
            if isrc:
                self.logger.info(f"ISRC found in AcoustID result: {isrc}")
            
            # Extraire le label
            label = result.get("label")
            if label:
                self.logger.info(f"Label found in AcoustID result: {label}")
            
            # Extraire la date de sortie
            release_date = result.get("release_date")
            
            # Extraire l'empreinte digitale
            fingerprint = result.get("fingerprint")
            if not fingerprint and "fingerprint" in audio_features:
                fingerprint = audio_features["fingerprint"]
            
            # Calculer la durée de lecture
            play_duration = 0
            if "duration" in audio_features:
                play_duration = audio_features["duration"]
            elif "duration" in result:
                play_duration = result["duration"]
            
            # Créer ou récupérer la piste
            try:
                # Utiliser _get_or_create_track pour créer ou récupérer la piste
                track = await self._get_or_create_track(
                    title=title,
                    artist_name=artist_name,
                    features={
                        "album": album,
                        "isrc": isrc,
                        "label": label,
                        "release_date": release_date,
                        "fingerprint": fingerprint,
                        "source": "acoustid",
                        "detection_method": "acoustid"
                    }
                )
                
                if not track:
                    self.logger.error(f"Failed to get or create track for AcoustID match for station {station_id}")
                    return None
                
                # Mettre à jour les champs manquants si nécessaire
                updated = False
                if isrc and not track.isrc:
                    track.isrc = isrc
                    updated = True
                    self.logger.info(f"Updated track with ISRC: {isrc}")
                
                if label and not track.label:
                    track.label = label
                    updated = True
                
                if release_date and not track.release_date:
                    track.release_date = release_date
                    updated = True
                
                if fingerprint and not track.fingerprint:
                    track.fingerprint = fingerprint
                    updated = True
                
                if updated:
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
                        "id": track.id,
                        "isrc": isrc,
                        "label": label,
                        "release_date": release_date,
                        "fingerprint": fingerprint[:20] + "..." if fingerprint else None  # Truncated for logging
                    },
                    "confidence": result.get("confidence", 0.7),
                    "source": "acoustid",
                    "detection_method": "acoustid",
                    "play_duration": play_duration
                }
            except Exception as e:
                self.logger.error(f"Error finding AcoustID match: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return None
        except Exception as e:
            self.logger.error(f"Error in AcoustID detection: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
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
        """
        Recherche une correspondance avec le service AudD.
        
        Args:
            audio_features: Caractéristiques audio extraites
            station_id: ID de la station (optionnel)
            
        Returns:
            Dictionnaire avec les informations de la piste ou None si aucune correspondance
        """
        if not self.audd_service:
            self.logger.warning("AudD service not initialized")
            return None
        
        try:
            # Convertir les caractéristiques en audio
            audio_data = self._convert_features_to_audio(audio_features)
            if not audio_data:
                self.logger.error("Failed to convert features to audio for AudD detection")
                return None
            
            # Détecter avec AudD
            self.logger.info(f"Detecting with AudD for station_id={station_id}")
            result = await self.audd_service.detect_track_with_retry(audio_data, max_retries=3)
            
            if not result:
                self.logger.info("No AudD match found")
                return None
            
            # Extraire les informations de base
            title = result.get("title", "Unknown Track")
            artist_name = result.get("artist", "Unknown Artist")
            album = result.get("album", "Unknown Album")
            
            # Extraire l'ISRC - vérifier plusieurs sources possibles
            isrc = None
            # Vérifier dans le résultat principal
            if "isrc" in result:
                isrc = result["isrc"]
                self.logger.info(f"ISRC found in main result: {isrc}")
            
            # Vérifier dans Apple Music
            elif "apple_music" in result and result["apple_music"]:
                if "isrc" in result["apple_music"]:
                    isrc = result["apple_music"]["isrc"]
                    self.logger.info(f"ISRC found in Apple Music: {isrc}")
            
            # Vérifier dans Spotify
            elif "spotify" in result and result["spotify"]:
                if "external_ids" in result["spotify"] and "isrc" in result["spotify"]["external_ids"]:
                    isrc = result["spotify"]["external_ids"]["isrc"]
                    self.logger.info(f"ISRC found in Spotify: {isrc}")
            
            # Vérifier dans Deezer
            elif "deezer" in result and result["deezer"]:
                if "isrc" in result["deezer"]:
                    isrc = result["deezer"]["isrc"]
                    self.logger.info(f"ISRC found in Deezer: {isrc}")
            
            # Extraire le label - vérifier plusieurs sources possibles
            label = None
            if "label" in result:
                label = result["label"]
                self.logger.info(f"Label found in main result: {label}")
            elif "apple_music" in result and result["apple_music"] and "label" in result["apple_music"]:
                label = result["apple_music"]["label"]
                self.logger.info(f"Label found in Apple Music: {label}")
            elif "spotify" in result and result["spotify"] and "label" in result["spotify"]:
                label = result["spotify"]["label"]
                self.logger.info(f"Label found in Spotify: {label}")
            
            # Extraire la date de sortie
            release_date = None
            if "release_date" in result:
                release_date = result["release_date"]
            elif "apple_music" in result and result["apple_music"] and "release_date" in result["apple_music"]:
                release_date = result["apple_music"]["release_date"]
            elif "spotify" in result and result["spotify"] and "release_date" in result["spotify"]:
                release_date = result["spotify"]["release_date"]
            
            # Extraire l'empreinte digitale
            fingerprint = None
            if "fingerprint" in audio_features:
                fingerprint = audio_features["fingerprint"]
            
            # Calculer la durée de lecture
            play_duration = 0
            if "duration" in audio_features:
                play_duration = audio_features["duration"]
            
            # Créer ou récupérer la piste
            track_info = result
            try:
                # Utiliser _get_or_create_track pour créer ou récupérer la piste
                track = await self._get_or_create_track(
                    title=title,
                    artist_name=artist_name,
                    features={
                        "album": album,
                        "isrc": isrc,
                        "label": label,
                        "release_date": release_date,
                        "fingerprint": fingerprint,
                        "source": "audd",
                        "detection_method": "audd"
                    }
                )
                
                if not track:
                    self.logger.error(f"Failed to get or create track for AudD match for station {station_id}")
                    return None
                
                # Mettre à jour les champs manquants si nécessaire
                updated = False
                if isrc and not track.isrc:
                    track.isrc = isrc
                    updated = True
                    self.logger.info(f"Updated track with ISRC: {isrc}")
                
                if label and not track.label:
                    track.label = label
                    updated = True
                
                if release_date and not track.release_date:
                    track.release_date = release_date
                    updated = True
                
                if fingerprint and not track.fingerprint:
                    track.fingerprint = fingerprint
                    updated = True
                
                if updated:
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
                        "id": track.id,
                        "isrc": isrc,
                        "label": label,
                        "release_date": release_date,
                        "fingerprint": fingerprint[:20] + "..." if fingerprint else None  # Truncated for logging
                    },
                    "confidence": 0.8,
                    "source": "audd",
                    "detection_method": "audd",
                    "play_duration": play_duration
                }
            except Exception as e:
                self.logger.error(f"Error finding AudD match: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return None
        except Exception as e:
            self.logger.error(f"Error in AudD detection: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
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

    def _extract_fingerprint(self, features: Dict[str, Any]) -> Tuple[Optional[str], Optional[bytes]]:
        """
        Extrait une empreinte digitale à partir des caractéristiques audio.
        
        Args:
            features: Caractéristiques audio extraites
            
        Returns:
            Tuple contenant (empreinte_hash, empreinte_raw) où:
            - empreinte_hash: Empreinte digitale sous forme de chaîne hexadécimale (pour recherche rapide)
            - empreinte_raw: Données brutes de l'empreinte (pour stockage et comparaison précise)
        """
        try:
            # Vérifier si l'empreinte est déjà calculée
            if "fingerprint" in features and features["fingerprint"]:
                # Si nous avons déjà une empreinte hash, l'utiliser
                fingerprint_hash = features["fingerprint"]
                
                # Vérifier si nous avons aussi les données brutes
                fingerprint_raw = None
                if "fingerprint_raw" in features and features["fingerprint_raw"]:
                    # Si c'est une chaîne, la convertir en bytes
                    if isinstance(features["fingerprint_raw"], str):
                        fingerprint_raw = features["fingerprint_raw"].encode('utf-8')
                    else:
                        fingerprint_raw = features["fingerprint_raw"]
                else:
                    # Si pas de données brutes, utiliser le hash comme fallback
                    fingerprint_raw = fingerprint_hash.encode('utf-8')
                
                log_with_category(logger, "TRACK_MANAGER", "debug", f"Using existing fingerprint: {fingerprint_hash[:10]}...")
                return fingerprint_hash, fingerprint_raw
            
            # Vérifier si une empreinte Chromaprint est disponible
            if "chromaprint" in features and features["chromaprint"]:
                log_with_category(logger, "TRACK_MANAGER", "info", f"Using Chromaprint fingerprint")
                chromaprint = features["chromaprint"]
                # Utiliser les 32 premiers caractères comme hash pour la recherche
                fingerprint_hash = chromaprint[:32] if len(chromaprint) > 32 else chromaprint
                fingerprint_raw = chromaprint.encode('utf-8')
                return fingerprint_hash, fingerprint_raw
                
            # Essayer de générer une empreinte Chromaprint si nous avons des données audio brutes
            if "raw_audio" in features and features["raw_audio"]:
                chromaprint = self._generate_chromaprint_fingerprint(features["raw_audio"])
                if chromaprint:
                    log_with_category(logger, "TRACK_MANAGER", "info", f"Generated Chromaprint fingerprint: {chromaprint[:20]}...")
                    # Utiliser les 32 premiers caractères comme hash pour la recherche
                    fingerprint_hash = chromaprint[:32] if len(chromaprint) > 32 else chromaprint
                    fingerprint_raw = chromaprint.encode('utf-8')
                    return fingerprint_hash, fingerprint_raw
                
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
                log_with_category(logger, "TRACK_MANAGER", "warning", "No audio features available for fingerprint, using random value")
                
            # Convertir en chaîne JSON pour les données brutes
            fingerprint_raw_str = json.dumps(fingerprint_data, sort_keys=True)
            fingerprint_raw = fingerprint_raw_str.encode('utf-8')
            
            # Calculer le hash MD5 pour l'empreinte de recherche
            fingerprint_hash = hashlib.md5(fingerprint_raw).hexdigest()
            
            log_with_category(logger, "TRACK_MANAGER", "info", f"Generated new fingerprint: {fingerprint_hash[:10]}...")
            return fingerprint_hash, fingerprint_raw
            
        except Exception as e:
            log_with_category(logger, "TRACK_MANAGER", "error", f"Error extracting fingerprint: {str(e)}")
            import traceback
            log_with_category(logger, "TRACK_MANAGER", "error", traceback.format_exc())
            
            # En cas d'erreur, générer une empreinte aléatoire
            import random
            import hashlib
            random_data = str(random.random())
            fingerprint_raw = random_data.encode('utf-8')
            fingerprint_hash = hashlib.md5(fingerprint_raw).hexdigest()
            
            log_with_category(logger, "TRACK_MANAGER", "warning", f"Using fallback random fingerprint: {fingerprint_hash[:10]}...")
            return fingerprint_hash, fingerprint_raw

    def _generate_chromaprint_fingerprint(self, audio_data: bytes) -> Optional[str]:
        """
        Génère une empreinte Chromaprint à partir des données audio.
        
        Args:
            audio_data: Données audio brutes
            
        Returns:
            Empreinte Chromaprint ou None si l'extraction échoue
        """
        try:
            import tempfile
            import subprocess
            import os
            from backend.detection.audio_processor.external_services import get_fpcalc_path
            
            # Obtenir le chemin vers fpcalc
            fpcalc_path = get_fpcalc_path()
            if not fpcalc_path:
                log_with_category(logger, "TRACK_MANAGER", "warning", "fpcalc not available, cannot generate Chromaprint fingerprint")
                return None
                
            # Créer un fichier temporaire pour les données audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)
                
            try:
                # Générer l'empreinte avec fpcalc
                result = subprocess.run(
                    [fpcalc_path, '-raw', temp_path],
                    capture_output=True,
                    text=True
                )
                
                # Extraire l'empreinte
                for line in result.stdout.splitlines():
                    if line.startswith('FINGERPRINT='):
                        fingerprint = line[12:]
                        log_with_category(logger, "TRACK_MANAGER", "info", f"Generated Chromaprint fingerprint: {fingerprint[:20]}...")
                        return fingerprint
                
                log_with_category(logger, "TRACK_MANAGER", "warning", "No Chromaprint fingerprint found in fpcalc output")
                return None
            finally:
                # Supprimer le fichier temporaire
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            log_with_category(logger, "TRACK_MANAGER", "error", f"Error generating Chromaprint fingerprint: {str(e)}")
            import traceback
            log_with_category(logger, "TRACK_MANAGER", "error", traceback.format_exc())
            return None
            
    def _convert_features_to_audio(self, features: Dict[str, Any]) -> Optional[bytes]:
        """
        Convertit les caractéristiques audio en données audio brutes.
        
        Args:
            features: Dictionnaire de caractéristiques audio
            
        Returns:
            Données audio brutes (bytes) ou None en cas d'erreur
        """
        try:
            # Vérifier si les données audio brutes sont déjà disponibles
            if "raw_audio" in features and features["raw_audio"]:
                self.logger.info(f"Using raw audio data from features ({len(features['raw_audio'])} bytes)")
                return features["raw_audio"]
            
            # Vérifier si le chemin du fichier audio est disponible
            if "audio_file" in features and features["audio_file"]:
                audio_file = features["audio_file"]
                if os.path.exists(audio_file):
                    self.logger.info(f"Reading audio data from file: {audio_file}")
                    with open(audio_file, "rb") as f:
                        return f.read()
                else:
                    self.logger.error(f"Audio file not found: {audio_file}")
            
            # Vérifier si les données audio sont disponibles sous forme de tableau numpy
            if "audio_data" in features and features["audio_data"] is not None:
                import numpy as np
                from io import BytesIO
                import soundfile as sf
                
                audio_data = features["audio_data"]
                sample_rate = features.get("sample_rate", 44100)
                
                self.logger.info(f"Converting numpy audio data to bytes (shape: {audio_data.shape}, sample rate: {sample_rate})")
                
                # Convertir le tableau numpy en bytes
                buffer = BytesIO()
                sf.write(buffer, audio_data, sample_rate, format="WAV")
                buffer.seek(0)
                return buffer.read()
            
            # Vérifier si les caractéristiques MFCC sont disponibles
            if "mfcc" in features and features["mfcc"] is not None:
                self.logger.warning("Cannot convert MFCC features to audio data")
            
            self.logger.error("No convertible audio data found in features")
            return None
        
        except Exception as e:
            self.logger.error(f"Error converting features to audio: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
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
            track = await self._get_or_create_track(title=local_match["title"], artist_name=local_match["artist"], features=local_match)
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
            track = await self._get_or_create_track(title=acoustid_match["title"], artist_name=acoustid_match["artist"], features=acoustid_match)
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
        
        # No match found
        log_with_category(logger, "TRACK_MANAGER", "info", f"No match found for station {station_name}")
        return {"success": False, "error": "No match found"}

    def _execute_with_transaction(self, operation_func, *args, **kwargs):
        """
        Exécute une opération dans une transaction avec gestion des erreurs.
        
        Args:
            operation_func: Fonction à exécuter dans la transaction
            *args, **kwargs: Arguments à passer à la fonction
            
        Returns:
            Résultat de la fonction ou None en cas d'erreur
        """
        try:
            # Exécuter l'opération
            result = operation_func(*args, **kwargs)
            
            # Valider la transaction
            self.db_session.commit()
            return result
        except Exception as e:
            # En cas d'erreur, annuler la transaction
            self.logger.error(f"Transaction error: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            try:
                # Essayer de faire un rollback
                self.db_session.rollback()
                self.logger.info("Transaction rolled back successfully")
            except Exception as rollback_error:
                self.logger.error(f"Error during rollback: {str(rollback_error)}")
            
            return None