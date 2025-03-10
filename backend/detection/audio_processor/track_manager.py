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
            
            # Vérifier que last_update_time existe, sinon utiliser start_time
            last_time = current.get("last_update_time", current["start_time"])
            
            # Vérifier que last_time est un objet datetime valide
            if not isinstance(last_time, datetime):
                self.logger.warning(f"Invalid last_update_time type: {type(last_time)}, using start_time")
                last_time = current["start_time"]
            
            # Calculer le temps écoulé
            time_since_last_update = now - last_time
            
            # Vérifier que le temps écoulé est positif et raisonnable
            if time_since_last_update.total_seconds() < 0:
                self.logger.warning("Negative time since last update, using 1 second")
                time_since_last_update = timedelta(seconds=1)
            elif time_since_last_update.total_seconds() > 3600:  # Plus d'une heure
                self.logger.warning("Time since last update exceeds 1 hour, capping at 1 hour")
                time_since_last_update = timedelta(hours=1)
            
            # Vérifier que play_duration existe et est un objet timedelta
            if not isinstance(current["play_duration"], timedelta):
                self.logger.warning(f"Invalid play_duration type: {type(current['play_duration'])}, resetting")
                current["play_duration"] = timedelta(seconds=0)
            
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
            self.logger.error(f"Erreur lors de la mise à jour de la piste: {str(e)}", exc_info=True)
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
                
                # Vérifier que last_update_time existe, sinon utiliser start_time
                last_time = current.get("last_update_time", current["start_time"])
                
                # Vérifier que last_time est un objet datetime valide
                if not isinstance(last_time, datetime):
                    self.logger.warning(f"Invalid last_update_time type: {type(last_time)}, using start_time")
                    last_time = current["start_time"]
                
                # Calculer le temps écoulé
                time_since_last_update = now - last_time
                
                # Vérifier que le temps écoulé est positif et raisonnable
                if time_since_last_update.total_seconds() < 0:
                    self.logger.warning("Negative time since last update, using 1 second")
                    time_since_last_update = timedelta(seconds=1)
                elif time_since_last_update.total_seconds() > 3600:  # Plus d'une heure
                    self.logger.warning("Time since last update exceeds 1 hour, capping at 1 hour")
                    time_since_last_update = timedelta(hours=1)
                
                # Vérifier que play_duration existe et est un objet timedelta
                if not isinstance(current["play_duration"], timedelta):
                    self.logger.warning(f"Invalid play_duration type: {type(current['play_duration'])}, resetting")
                    current["play_duration"] = timedelta(seconds=0)
                
                # Ajouter ce dernier intervalle à la durée totale
                total_duration = current["play_duration"] + time_since_last_update
                
                # Vérifier que la durée totale est raisonnable
                if total_duration.total_seconds() <= 0:
                    self.logger.warning("Total duration is zero or negative, using minimum duration")
                    total_duration = timedelta(seconds=15)
                elif total_duration.total_seconds() > 3600:
                    self.logger.warning("Total duration exceeds maximum, capping at 1 hour")
                    total_duration = timedelta(hours=1)
                
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
                self.logger.error(f"Erreur lors de la fin du suivi de piste: {str(e)}", exc_info=True)
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
            self.logger.error(f"Erreur lors de la fin de la piste: {str(e)}")
            self.db_session.rollback()
            return None

    async def _get_or_create_track(self, title: str, artist_id: int, album: Optional[str] = None, 
                              isrc: Optional[str] = None, label: Optional[str] = None, 
                              release_date: Optional[str] = None, duration: Optional[float] = None) -> Optional[Track]:
        """
        Récupère ou crée une piste dans la base de données.
        
        Args:
            title: Titre de la piste
            artist_id: ID de l'artiste
            album: Nom de l'album (optionnel)
            isrc: Code ISRC (optionnel)
            label: Label (optionnel)
            release_date: Date de sortie (optionnel)
            duration: Durée de la piste en secondes (optionnel)
            
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
            
            # Convertir la durée en timedelta si elle est fournie
            duration_value = None
            if duration is not None:
                duration_value = timedelta(seconds=duration)
            
            track = Track(
                title=title,
                artist_id=artist_id,
                album=album,
                isrc=isrc,
                label=label,
                release_date=release_date,
                duration=duration_value,
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
            # Convertir play_duration en timedelta pour l'enregistrement
            play_duration_td = timedelta(seconds=play_duration)
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
                "release_date": existing_track.release_date,
                "duration": existing_track.duration.total_seconds() if existing_track.duration else 0
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
            # Convertir play_duration en timedelta si ce n'est pas déjà le cas
            if isinstance(play_duration, (int, float)):
                play_duration_td = timedelta(seconds=play_duration)
            elif isinstance(play_duration, timedelta):
                play_duration_td = play_duration
            else:
                self.logger.warning(f"Invalid play_duration type: {type(play_duration)}, using 0 seconds")
                play_duration_td = timedelta(seconds=0)
                
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
                play_duration=play_duration_td,
                confidence=0.8,
                detection_method="audd"
            )
            self.db_session.add(detection)
            
            # Update station track stats
            self._update_station_track_stats(station_id, track_id, play_duration_td)
            
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
                    play_duration=play_duration_td
                )
                
                self.logger.info(f"Updated all stats for track ID {track_id} on station ID {station_id}")
            except Exception as stats_error:
                self.logger.error(f"Error updating stats: {stats_error}")
                # Continue with the rest of the method even if stats update fails
            
            self.db_session.commit()
            self.logger.info(f"Recorded play time for track ID {track_id} on station ID {station_id}: {play_duration_td.total_seconds()} seconds")
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