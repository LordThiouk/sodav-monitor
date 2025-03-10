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
import re
from backend.utils.validators import validate_isrc as validate_isrc_util

logger = setup_logging(__name__)

class TrackManager:
    """
    Gère les pistes musicales dans la base de données.
    
    Cette classe fournit des méthodes pour créer, rechercher, mettre à jour et
    gérer les pistes musicales dans la base de données. Elle est responsable de
    la détection des pistes, de l'extraction des métadonnées, de la gestion des
    empreintes digitales et du suivi des statistiques de lecture.
    
    La classe utilise différentes méthodes de détection (locale, AcoustID, AudD)
    pour identifier les pistes musicales et éviter les doublons en utilisant
    notamment les codes ISRC comme identifiants uniques.
    
    Attributes:
        db_session (Session): Session de base de données SQLAlchemy.
        feature_extractor (Optional): Extracteur de caractéristiques audio.
        logger (Logger): Logger pour enregistrer les événements.
        current_tracks (Dict[int, Dict]): Dictionnaire des pistes en cours de lecture par station.
    """
    
    def __init__(self, db_session: Session, feature_extractor=None):
        """
        Initialise un gestionnaire de pistes.
        
        Args:
            db_session: Session de base de données SQLAlchemy.
            feature_extractor: Extracteur de caractéristiques audio (optionnel).
        """
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
        """
        Traite une piste détectée et gère son cycle de vie dans le système.
        
        Cette méthode est le point d'entrée principal pour le traitement des pistes
        détectées. Elle gère le cycle de vie complet d'une piste, depuis sa détection
        jusqu'à sa fin de lecture, en passant par la création ou la récupération
        de la piste dans la base de données et la mise à jour des statistiques.
        
        Le processus comprend:
        1. Vérification si une piste est déjà en cours de lecture sur la station
           - Si c'est la même piste, mise à jour de la durée de lecture
           - Si c'est une nouvelle piste, fin de la piste précédente
        2. Création ou récupération de la piste dans la base de données
           - Utilisation de l'ISRC comme identifiant unique si disponible
        3. Démarrage du suivi de la nouvelle piste
        
        Args:
            features (Dict[str, Any]): Caractéristiques audio et métadonnées de la piste détectée.
                Peut inclure: title, artist, isrc, fingerprint, audio_data, etc.
            station_id (Optional[int], optional): ID de la station radio. Défaut à None.
            
        Returns:
            Dict[str, Any]: Dictionnaire contenant:
                - status: "success" si le traitement a réussi
                - track: Informations sur la piste (id, title, artist, etc.)
                - detection: Informations sur la détection (id, timestamp, etc.)
                - error: Message d'erreur si le traitement a échoué
                
        Raises:
            Exception: Les exceptions sont capturées et retournées dans le dictionnaire
                      de résultat avec une clé "error".
                      
        Note:
            Cette méthode utilise la contrainte d'unicité ISRC pour éviter les doublons
            et consolider les statistiques de lecture pour une même piste.
        """
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
        """
        Met à jour les informations de la piste en cours.
        
        Cette méthode est cruciale pour le suivi précis de la durée réelle de diffusion.
        Au lieu d'utiliser simplement la durée de l'échantillon audio, elle calcule
        le temps réel écoulé depuis la dernière détection de cette piste.
        
        Args:
            station_id: ID de la station radio
            features: Caractéristiques audio extraites
            
        Returns:
            Dict contenant le statut de la piste et sa durée de lecture actuelle
        """
        try:
            current = self.current_tracks[station_id]
            
            # Calculer le temps écoulé depuis la dernière mise à jour
            now = datetime.utcnow()
            time_since_last_update = now - current.get("last_update_time", current["start_time"])
            
            # Mettre à jour la durée totale avec le temps réel écoulé
            current["play_duration"] += time_since_last_update
            current["last_update_time"] = now
            current["features"] = features
            
            # Enregistrer cette mise à jour dans les logs pour le suivi
            self.logger.info(
                f"Mise à jour de la piste en cours sur la station {station_id}: "
                f"Track ID {current['track'].id}, "
                f"Temps écoulé depuis dernière mise à jour: {time_since_last_update.total_seconds()} secondes, "
                f"Durée totale accumulée: {current['play_duration'].total_seconds()} secondes"
            )
            
            return {
                "status": "playing",
                "track": current["track"].to_dict(),
                "play_duration": current["play_duration"].total_seconds(),
                "time_since_last_update": time_since_last_update.total_seconds()
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour de la piste: {str(e)}")
            return {"error": str(e)}
    
    def _end_current_track(self, station_id: int):
        """
        Termine le suivi de la piste en cours pour une station donnée.
        
        Cette méthode est appelée lorsqu'une piste cesse d'être détectée sur une station,
        soit parce qu'une nouvelle piste commence, soit parce que la diffusion s'arrête.
        Elle enregistre la durée totale de diffusion et met à jour les statistiques.
        
        Args:
            station_id: ID de la station radio
            
        Returns:
            Dict contenant les informations sur la piste terminée, ou None si aucune piste n'était en cours
        """
        if station_id in self.current_tracks:
            try:
                current = self.current_tracks[station_id]
                
                # Calculer le temps écoulé depuis la dernière mise à jour
                now = datetime.utcnow()
                time_since_last_update = now - current.get("last_update_time", current["start_time"])
                
                # Ajouter ce dernier intervalle à la durée totale
                total_duration = current["play_duration"] + time_since_last_update
                
                # Créer un enregistrement de détection avec la durée totale précise
                detection = TrackDetection(
                    track_id=current["track"].id,
                    station_id=station_id,
                    detected_at=current["start_time"],
                    end_time=now,
                    play_duration=total_duration,
                    fingerprint=current["features"].get("fingerprint", ""),
                    audio_hash=current["features"].get("audio_hash", ""),
                    confidence=current["features"].get("confidence", 0),
                    detection_method=current["features"].get("detection_method", "unknown")
                )
                self.db_session.add(detection)
                
                # Mettre à jour les statistiques avec la durée totale précise
                self._update_station_track_stats(
                    station_id,
                    current["track"].id,
                    total_duration
                )
                
                # Enregistrer cette fin de diffusion dans les logs
                self.logger.info(
                    f"Fin de diffusion sur la station {station_id}: "
                    f"Track ID {current['track'].id}, "
                    f"Durée totale: {total_duration.total_seconds()} secondes, "
                    f"Début: {current['start_time'].isoformat()}, "
                    f"Fin: {now.isoformat()}"
                )
                
                # Créer un résumé de la diffusion
                result = {
                    "track_id": current["track"].id,
                    "track_title": current["track"].title,
                    "artist_name": current["track"].artist.name if current["track"].artist else None,
                    "start_time": current["start_time"].isoformat(),
                    "end_time": now.isoformat(),
                    "play_duration": total_duration.total_seconds(),
                    "confidence": current["features"].get("confidence", 0)
                }
                
                # Supprimer la piste en cours
                del self.current_tracks[station_id]
                
                # Valider les changements
                self.db_session.commit()
                
                return result
                
            except Exception as e:
                self.logger.error(f"Erreur lors de la fin du suivi de piste: {str(e)}")
                self.db_session.rollback()
                return {"error": str(e)}
                
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
        Récupère une piste existante ou en crée une nouvelle dans la base de données.
        
        Cette méthode est au cœur du système de gestion des pistes, assurant l'unicité
        des pistes grâce à plusieurs critères de recherche hiérarchisés, avec une
        priorité donnée à l'ISRC. Elle extrait également les métadonnées des différentes
        sources disponibles et met à jour les pistes existantes avec de nouvelles informations.
        
        Processus de recherche hiérarchique:
        1. Recherche par ISRC (prioritaire) - Exploite la contrainte d'unicité
        2. Recherche par empreinte digitale dans la table fingerprints
        3. Recherche par empreinte digitale dans la table tracks
        4. Recherche par titre et artiste
        
        Si une piste est trouvée, ses métadonnées sont mises à jour avec les nouvelles
        informations disponibles. Si aucune piste n'est trouvée, une nouvelle est créée.
        
        Args:
            title (str, optional): Titre de la piste. Défaut à None.
            artist_name (str, optional): Nom de l'artiste. Défaut à None.
            features (Optional[Dict[str, Any]], optional): Caractéristiques et métadonnées
                supplémentaires (album, isrc, label, fingerprint, etc.). Défaut à None.
            
        Returns:
            Optional[Track]: Objet Track créé ou récupéré, ou None en cas d'erreur.
            
        Raises:
            Exception: Les exceptions sont capturées et journalisées, et la méthode
                      retourne None en cas d'erreur.
                      
        Note:
            Cette méthode est cruciale pour maintenir l'intégrité des données et éviter
            les doublons dans la base de données, notamment grâce à la contrainte
            d'unicité sur les codes ISRC.
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
                
                # Normaliser et valider l'ISRC si présent
                if isrc:
                    isrc = isrc.replace('-', '').upper()
                    if not self._validate_isrc(isrc):
                        self.logger.warning(f"ISRC invalide ignoré: {isrc}")
                        isrc = None  # Ignorer l'ISRC invalide
                    else:
                        self.logger.info(f"ISRC valide trouvé et normalisé: {isrc}")
                
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
            
            track = None
            
            # 1. Rechercher d'abord par ISRC si disponible (critère principal)
            if isrc:
                self.logger.info(f"Searching for track with ISRC: {isrc}")
                track = self.db_session.query(Track).filter(Track.isrc == isrc).first()
                
                if track:
                    self.logger.info(f"Track found by ISRC: {track.title} by artist ID {track.artist_id}")
                    # Mettre à jour le titre et l'artiste si nécessaire pour standardiser
                    if track.title != title or track.artist_id != artist_id:
                        self.logger.info(f"Updating track metadata to standardize: {track.title} -> {title}, artist ID {track.artist_id} -> {artist_id}")
                        # On ne change pas l'artiste_id pour éviter de casser les relations, mais on peut mettre à jour le titre
                        if track.title != title:
                            track.title = title
                            track.updated_at = datetime.utcnow()
                            self.db_session.flush()
            
            # 2. Si pas trouvé par ISRC, rechercher par fingerprint
            if not track and fingerprint_hash:
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
                            
                            # Si on a un ISRC mais que la piste n'en a pas, mettre à jour
                            if isrc and not track.isrc:
                                self.logger.info(f"Updating track with ISRC: {isrc}")
                                track.isrc = isrc
                                track.updated_at = datetime.utcnow()
                                self.db_session.flush()
            
            # 3. Si toujours pas trouvé, rechercher dans la colonne fingerprint de la table tracks
            if not track and fingerprint_hash:
                track = self.db_session.query(Track).filter(Track.fingerprint == fingerprint_hash).first()
                if track:
                    self.logger.info(f"Track found by fingerprint in tracks table: {track.title}")
                    
                    # Si on a un ISRC mais que la piste n'en a pas, mettre à jour
                    if isrc and not track.isrc:
                        self.logger.info(f"Updating track with ISRC: {isrc}")
                        track.isrc = isrc
                        track.updated_at = datetime.utcnow()
                        self.db_session.flush()
            
            # 4. En dernier recours, rechercher par titre et artiste
            if not track:
                track = self.db_session.query(Track).filter(
                    Track.title == title,
                    Track.artist_id == artist_id
                ).first()
                
                if track:
                    self.logger.info(f"Track found by title and artist: {track.title}")
                    
                    # Si on a un ISRC mais que la piste n'en a pas, mettre à jour
                    if isrc and not track.isrc:
                        self.logger.info(f"Updating track with ISRC: {isrc}")
                        track.isrc = isrc
                        track.updated_at = datetime.utcnow()
                        self.db_session.flush()
            
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
        """
        Démarre le suivi d'une nouvelle piste détectée sur une station.
        
        Cette méthode initialise le suivi d'une nouvelle piste, en enregistrant
        le moment exact où la piste a commencé à être diffusée. Cette information
        est cruciale pour calculer précisément la durée totale de diffusion.
        
        Args:
            track: Objet Track représentant la piste détectée
            station_id: ID de la station radio
            features: Caractéristiques audio extraites
            
        Returns:
            Dict contenant les informations sur la piste détectée
        """
        try:
            # Enregistrer le moment exact de début de la diffusion
            start_time = datetime.utcnow()
            
            # Initialiser le suivi avec une durée initiale de 0
            self.current_tracks[station_id] = {
                "track": track,
                "track_id": track.id,
                "start_time": start_time,
                "last_update_time": start_time,  # Important pour le calcul du temps réel
                "play_duration": timedelta(seconds=0),  # On commence à 0, pas avec la durée de l'échantillon
                "features": features
            }
            
            # Récupérer le nom de l'artiste de manière sécurisée
            artist_name = "Inconnu"
            if track.artist:
                artist_name = track.artist.name
            
            # Enregistrer cette détection dans les logs
            self.logger.info(
                f"Nouvelle piste détectée sur la station {station_id}: "
                f"Track ID {track.id}, Titre: {track.title}, "
                f"Artiste: {artist_name}, "
                f"Début de diffusion: {start_time.isoformat()}"
            )
            
            return {
                "track_id": track.id,
                "track_title": track.title,
                "artist": artist_name,  # Utiliser "artist" au lieu de "artist_name"
                "start_time": start_time.isoformat(),
                "confidence": features.get("confidence", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage du suivi de piste: {str(e)}")
            return {"error": str(e)}
    
    def _update_station_track_stats(self, station_id: int, track_id: int, play_duration: timedelta):
        """
        Met à jour les statistiques de diffusion pour une piste sur une station spécifique.
        
        Cette méthode est responsable de la mise à jour des statistiques cumulatives
        de diffusion dans la table `station_track_stats`. Elle est appelée par la méthode
        `_record_play_time` après chaque détection d'une piste. Cette fonctionnalité est
        essentielle pour le suivi précis des statistiques de diffusion, en particulier
        pour les pistes identifiées par leur code ISRC.
        
        Le processus comprend:
        1. Recherche des statistiques existantes pour la paire station-piste
        2. Si des statistiques existent:
           - Incrémentation du compteur de diffusions
           - Ajout de la durée de lecture au total existant
           - Mise à jour de la date de dernière diffusion
        3. Si aucune statistique n'existe:
           - Création d'un nouvel enregistrement avec les valeurs initiales
        
        Args:
            station_id (int): ID de la station radio.
            track_id (int): ID de la piste détectée.
            play_duration (timedelta): Durée de lecture sous forme d'objet timedelta.
            
        Raises:
            Exception: Si une erreur survient lors de la mise à jour, la transaction
                      est annulée et l'erreur est journalisée.
                      
        Note:
            Cette méthode est cruciale pour maintenir l'intégrité des statistiques
            de diffusion et éviter la duplication des données grâce à la contrainte
            d'unicité sur les codes ISRC.
        """
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
    
    def _validate_isrc(self, isrc: str) -> bool:
        """
        Valide un code ISRC selon le format standard international.
        
        Cette méthode utilise la fonction validate_isrc_util du module utils.validators
        pour vérifier si un code ISRC respecte le format standard. Un ISRC valide
        est essentiel pour maintenir l'intégrité des données et exploiter la
        contrainte d'unicité dans la base de données.
        
        Format ISRC: CC-XXX-YY-NNNNN
        - CC: Code pays (2 lettres)
        - XXX: Code du propriétaire (3 caractères alphanumériques)
        - YY: Année de référence (2 chiffres)
        - NNNNN: Code de désignation (5 chiffres)
        
        Args:
            isrc (str): Code ISRC à valider. Doit être une chaîne de 12 caractères
                       après normalisation (sans tirets).
            
        Returns:
            bool: True si le format est valide, False sinon.
            
        Examples:
            >>> track_manager._validate_isrc("FRXXX0123456")
            True
            >>> track_manager._validate_isrc("FR-XXX-01-23456")  # Avec tirets (normalisé en interne)
            True
            >>> track_manager._validate_isrc("INVALID")
            False
        """
        is_valid, _ = validate_isrc_util(isrc)
        return is_valid

    async def _find_track_by_isrc(self, isrc: str, source: str, play_duration: float = 0, station_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Méthode commune pour rechercher une piste par son code ISRC et mettre à jour ses statistiques.
        
        Cette méthode interne est utilisée par les différentes méthodes de détection
        (AcoustID, AudD, etc.) pour rechercher une piste existante par son ISRC et
        mettre à jour ses statistiques de lecture si nécessaire. Elle exploite la
        contrainte d'unicité des ISRC pour éviter les doublons dans la base de données.
        
        Le processus comprend:
        1. Validation du format ISRC
        2. Recherche de la piste dans la base de données
        3. Mise à jour des statistiques de lecture si une durée est fournie
        4. Construction d'un dictionnaire de résultat standardisé
        
        Args:
            isrc (str): Code ISRC à rechercher. Sera normalisé automatiquement.
            source (str): Source de la détection ('acoustid', 'audd', etc.).
            play_duration (float, optional): Durée de lecture en secondes. Défaut à 0.
            station_id (Optional[int], optional): ID de la station. Défaut à None.
            
        Returns:
            Optional[Dict[str, Any]]: Dictionnaire contenant les informations de la piste
                                     avec les clés suivantes:
                - track: Dictionnaire avec les détails de la piste
                - confidence: Niveau de confiance (1.0 pour les correspondances ISRC)
                - source: Source de la détection (passée en paramètre)
                - detection_method: "isrc_match"
                
                Retourne None si aucune piste n'est trouvée avec cet ISRC ou si l'ISRC est invalide.
        """
        if not isrc:
            return None
        
        # Normaliser l'ISRC (supprimer les tirets, mettre en majuscules)
        normalized_isrc = isrc.replace('-', '').upper()
        
        # Vérifier la validité du format ISRC
        if not self._validate_isrc(normalized_isrc):
            return None
        
        # Rechercher la piste par ISRC
        existing_track = self.db_session.query(Track).filter(Track.isrc == normalized_isrc).first()
        
        if not existing_track:
            return None
        
        # Récupérer l'artiste
        artist = self.db_session.query(Artist).filter(Artist.id == existing_track.artist_id).first()
        artist_name_from_db = artist.name if artist else "Unknown Artist"
        
        # Mettre à jour les statistiques si station_id est fourni
        if station_id and play_duration > 0:
            self._record_play_time(station_id, existing_track.id, play_duration)
        
        self.logger.info(f"Found existing track with ISRC {isrc}: {existing_track.title} by {artist_name_from_db}")
        
        # Retourner les informations de la piste existante
        return {
            "track": {
                "id": existing_track.id,
                "title": existing_track.title,
                "artist": artist_name_from_db,
                "album": existing_track.album,
                "isrc": existing_track.isrc,
                "label": existing_track.label,
                "release_date": existing_track.release_date
            },
            "confidence": 1.0,  # Confiance maximale pour les correspondances ISRC
            "source": source,
            "detection_method": source,
            "play_duration": play_duration
        }

    async def find_track_by_isrc(self, isrc: str) -> Optional[Dict[str, Any]]:
        """
        Recherche une piste par son code ISRC dans la base de données.
        
        Cette méthode est essentielle pour exploiter la contrainte d'unicité des ISRC
        dans le système. Elle normalise d'abord le code ISRC fourni, vérifie sa validité,
        puis interroge la base de données pour trouver une correspondance exacte.
        
        Si une piste est trouvée, la méthode retourne un dictionnaire contenant les
        informations de la piste avec un niveau de confiance maximal (1.0), car les
        correspondances ISRC sont considérées comme fiables à 100%.
        
        Args:
            isrc (str): Code ISRC à rechercher. Peut contenir des tirets qui seront
                        automatiquement supprimés lors de la normalisation.
            
        Returns:
            Optional[Dict[str, Any]]: Dictionnaire contenant les informations de la piste
                                     avec les clés suivantes:
                - track: Dictionnaire avec les détails de la piste (id, title, artist, album, isrc, etc.)
                - confidence: Niveau de confiance de la correspondance (1.0 pour les ISRC)
                - source: Source de la détection ("database")
                - detection_method: Méthode de détection utilisée ("isrc_match")
                
                Retourne None si aucune piste n'est trouvée avec cet ISRC ou si l'ISRC est invalide.
                
        Examples:
            >>> result = await track_manager.find_track_by_isrc("FRXXX0123456")
            >>> if result:
            ...     print(f"Piste trouvée: {result['track']['title']} par {result['track']['artist']}")
            ... else:
            ...     print("Aucune piste trouvée avec cet ISRC")
        """
        if not isrc:
            return None
        
        # Normaliser l'ISRC (supprimer les tirets, mettre en majuscules)
        normalized_isrc = isrc.replace('-', '').upper()
        
        # Vérifier la validité du format ISRC
        if not self._validate_isrc(normalized_isrc):
            self.logger.warning(f"Format ISRC invalide: {isrc}")
            return None
        
        # Rechercher la piste par ISRC
        existing_track = self.db_session.query(Track).filter(Track.isrc == normalized_isrc).first()
        
        if not existing_track:
            return None
        
        # Récupérer l'artiste
        artist = self.db_session.query(Artist).filter(Artist.id == existing_track.artist_id).first()
        artist_name = artist.name if artist else "Unknown Artist"
        
        return {
            "track": {
                "id": existing_track.id,
                "title": existing_track.title,
                "artist": artist_name,
                "album": existing_track.album,
                "isrc": existing_track.isrc,
                "label": existing_track.label,
                "release_date": existing_track.release_date
            },
            "confidence": 1.0,  # Confiance maximale pour les correspondances ISRC
            "source": "database",
            "detection_method": "isrc_match"
        }

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
            
            # Extraire l'ISRC et valider son format
            isrc = result.get("isrc")
            if isrc and isinstance(isrc, str) and len(isrc) == 12 and isrc.isalnum():
                self.logger.info(f"Valid ISRC found in AcoustID result: {isrc}")
            else:
                if isrc:
                    self.logger.warning(f"Invalid ISRC format found in AcoustID result: {isrc}")
                isrc = None
            
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
            
            # Si nous avons un ISRC valide, vérifier d'abord si une piste avec cet ISRC existe déjà
            if isrc:
                existing_track_result = await self._find_track_by_isrc(isrc, "acoustid", play_duration, station_id)
                if existing_track_result:
                    return existing_track_result
            
            # Si aucune piste existante n'a été trouvée par ISRC, créer ou récupérer la piste
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
                    self.logger.error(f"Failed to create or get track: {title} by {artist_name}")
                    return None
                
                # Démarrer la détection de piste
                detection_result = self._start_track_detection(track, station_id, audio_features)
                
                # Créer le résultat final avec la structure attendue
                return {
                    "track": {
                        "id": track.id,
                        "title": title,
                        "artist": artist_name,
                        "album": album,
                        "isrc": isrc,
                        "label": label,
                        "release_date": release_date
                    },
                    "confidence": result.get("confidence", 0.8),
                    "source": "acoustid",
                    "detection_method": "acoustid",
                    "play_duration": play_duration
                }
            except Exception as e:
                self.logger.error(f"Error creating or getting track: {str(e)}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error in find_acoustid_match: {str(e)}")
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
            
            if not result or not result.get("success", False):
                self.logger.info("No AudD match found")
                return None
            
            # Extraire les informations de base
            detection_data = result.get("detection", {})
            title = detection_data.get("title", "Unknown Track")
            artist_name = detection_data.get("artist", "Unknown Artist")
            album = detection_data.get("album", "Unknown Album")
            
            # Extraire l'ISRC - vérifier plusieurs sources possibles
            isrc = None
            isrc_sources = []
            
            # Vérifier dans le résultat principal
            if "isrc" in detection_data:
                isrc_sources.append(("main", detection_data["isrc"]))
            
            # Vérifier dans Apple Music
            if "apple_music" in detection_data and detection_data["apple_music"] and "isrc" in detection_data["apple_music"]:
                isrc_sources.append(("apple_music", detection_data["apple_music"]["isrc"]))
            
            # Vérifier dans Spotify
            if "spotify" in detection_data and detection_data["spotify"] and "external_ids" in detection_data["spotify"] and "isrc" in detection_data["spotify"]["external_ids"]:
                isrc_sources.append(("spotify", detection_data["spotify"]["external_ids"]["isrc"]))
            
            # Vérifier dans Deezer
            if "deezer" in detection_data and detection_data["deezer"] and "isrc" in detection_data["deezer"]:
                isrc_sources.append(("deezer", detection_data["deezer"]["isrc"]))
            
            # Prendre le premier ISRC valide
            for source, value in isrc_sources:
                # Valider le format ISRC (12 caractères alphanumériques)
                if value and isinstance(value, str) and len(value) == 12 and value.isalnum():
                    isrc = value
                    self.logger.info(f"Valid ISRC found in {source}: {isrc}")
                    break
            
            if isrc:
                self.logger.info(f"Using ISRC: {isrc} for track: {title} by {artist_name}")
            else:
                self.logger.warning(f"No valid ISRC found for track: {title} by {artist_name}")
            
            # Extraire le label - vérifier plusieurs sources possibles
            label = None
            label_sources = []
            
            if "label" in detection_data:
                label_sources.append(("main", detection_data["label"]))
            
            if "apple_music" in detection_data and detection_data["apple_music"] and "label" in detection_data["apple_music"]:
                label_sources.append(("apple_music", detection_data["apple_music"]["label"]))
            
            if "spotify" in detection_data and detection_data["spotify"] and "label" in detection_data["spotify"]:
                label_sources.append(("spotify", detection_data["spotify"]["label"]))
            
            # Prendre le premier label valide
            for source, value in label_sources:
                if value and isinstance(value, str):
                    label = value
                    self.logger.info(f"Label found in {source}: {label}")
                    break
            
            # Extraire la date de sortie
            release_date = None
            release_date_sources = []
            
            if "release_date" in detection_data:
                release_date_sources.append(("main", detection_data["release_date"]))
            
            if "apple_music" in detection_data and detection_data["apple_music"] and "release_date" in detection_data["apple_music"]:
                release_date_sources.append(("apple_music", detection_data["apple_music"]["release_date"]))
            
            if "spotify" in detection_data and detection_data["spotify"] and "release_date" in detection_data["spotify"]:
                release_date_sources.append(("spotify", detection_data["spotify"]["release_date"]))
            
            # Prendre la première date de sortie valide
            for source, value in release_date_sources:
                if value and isinstance(value, str):
                    release_date = value
                    self.logger.info(f"Release date found in {source}: {release_date}")
                    break
            
            # Extraire l'empreinte digitale
            fingerprint = None
            if "fingerprint" in audio_features:
                fingerprint = audio_features["fingerprint"]
            
            # Calculer la durée de lecture
            play_duration = 0
            if "duration" in audio_features:
                play_duration = audio_features["duration"]
            
            # Si nous avons un ISRC valide, vérifier d'abord si une piste avec cet ISRC existe déjà
            if isrc:
                existing_track_result = await self._find_track_by_isrc(isrc, "audd", play_duration, station_id)
                if existing_track_result:
                    return existing_track_result
            
            # Si aucune piste existante n'a été trouvée par ISRC, créer ou récupérer la piste
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
                    self.logger.error(f"Failed to create or get track: {title} by {artist_name}")
                    return None
                
                # Créer le résultat final avec la structure attendue
                return {
                    "track": {
                        "id": track.id,
                        "title": title,
                        "artist": artist_name,
                        "album": album,
                        "isrc": isrc,
                        "label": label,
                        "release_date": release_date
                    },
                    "confidence": detection_data.get("confidence", 0.8),
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
        Enregistre le temps de lecture exact d'une piste sur une station et met à jour les statistiques.
        
        Cette méthode interne est cruciale pour maintenir des statistiques précises de lecture
        pour chaque piste. Elle crée un nouvel enregistrement de détection dans la table
        `track_detections` et met à jour les statistiques cumulatives dans la table
        `station_track_stats`. Cette fonctionnalité est particulièrement importante pour
        les pistes identifiées par leur code ISRC, car elle permet de consolider toutes
        les statistiques de lecture pour une même piste, même si elle est détectée par
        différentes méthodes.
        
        Le processus comprend:
        1. Vérification de l'existence de la station
        2. Création d'un nouvel enregistrement de détection
        3. Mise à jour des statistiques cumulatives via _update_station_track_stats
        4. Validation des changements dans la base de données
        
        Args:
            station_id (int): ID de la station radio qui diffuse la piste.
            track_id (int): ID de la piste détectée.
            play_duration (float): Durée de lecture en secondes.
            
        Raises:
            Exception: Si une erreur survient lors de l'enregistrement, la transaction
                      est annulée et l'erreur est journalisée.
                      
        Examples:
            >>> self._record_play_time(1, 42, 180.5)  # Enregistre 3 minutes de lecture
        """
        try:
            # Get the station
            station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
            if not station:
                self.logger.warning(f"Station with ID {station_id} not found")
                return
            
            # Get the track
            track = self.db_session.query(Track).filter(Track.id == track_id).first()
            if not track:
                self.logger.warning(f"Track with ID {track_id} not found")
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
            
            # Use StatsUpdater to update all statistics
            try:
                # Create a detection result dictionary
                detection_result = {
                    "track_id": track_id,
                    "confidence": 0.8,
                    "detection_method": "audd"
                }
                
                # Initialize StatsUpdater if not already done
                from backend.utils.analytics.stats_updater import StatsUpdater
                stats_updater = StatsUpdater(self.db_session)
                
                # Update all stats
                stats_updater.update_all_stats(
                    detection_result=detection_result,
                    station_id=station_id,
                    track=track,
                    play_duration=timedelta(seconds=play_duration)
                )
                
                self.logger.info(f"Updated all stats for track ID {track_id} on station ID {station_id}")
            except Exception as stats_error:
                self.logger.error(f"Error updating stats: {stats_error}")
                # Continue with the rest of the method even if stats update fails
            
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