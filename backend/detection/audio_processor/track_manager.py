"""Module de gestion des pistes audio détectées."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ...models.models import Track, TrackDetection, RadioStation, StationTrackStats, Artist
from ...utils.logging_config import setup_logging
import numpy as np

logger = setup_logging(__name__)

class TrackManager:
    """Gestionnaire des pistes audio."""
    
    def __init__(self, db_session: Session):
        """Initialise le gestionnaire de pistes."""
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        self.current_tracks = {}
    
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
            current["duration"] += timedelta(seconds=features.get("duration", 0))
            current["features"] = features
            
            return {
                "status": "playing",
                "track": current["track"].to_dict(),
                "duration": current["duration"].total_seconds()
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
                    start_time=current["start_time"],
                    end_time=datetime.utcnow(),
                    duration=current["duration"].total_seconds(),
                    confidence=current["features"].get("confidence", 0)
                )
                self.db_session.add(detection)
                
                # Met à jour les statistiques
                self._update_station_track_stats(
                    station_id,
                    current["track"].id,
                    current["duration"]
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
                duration=features.get("duration", 0),
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
                "duration": timedelta(seconds=features.get("duration", 0)),
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
    
    def _update_station_track_stats(self, station_id: int, track_id: int, duration: timedelta):
        """Met à jour les statistiques de diffusion."""
        try:
            stats = self.db_session.query(StationTrackStats).filter_by(
                station_id=station_id,
                track_id=track_id
            ).first()
            
            if stats:
                stats.play_count += 1
                stats.total_play_time += duration.total_seconds()
                stats.last_played = datetime.utcnow()
            else:
                stats = StationTrackStats(
                    station_id=station_id,
                    track_id=track_id,
                    play_count=1,
                    total_play_time=duration.total_seconds(),
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