"""
Module d'enregistrement et de mise à jour des statistiques de lecture.

Ce module contient la classe StatsRecorder qui est responsable de l'enregistrement
des temps de lecture et de la mise à jour des statistiques associées.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.models import Artist, RadioStation, StationTrackStats, Track, TrackDetection
from backend.utils.logging import log_with_category

logger = logging.getLogger(__name__)


class StatsRecorder:
    """
    Classe responsable de l'enregistrement et de la mise à jour des statistiques de lecture.

    Cette classe extrait les fonctionnalités d'enregistrement des statistiques du TrackManager
    pour améliorer la séparation des préoccupations et faciliter la maintenance.
    """

    def __init__(self, db_session: Session):
        """
        Initialise un nouveau StatsRecorder.

        Args:
            db_session: Session de base de données SQLAlchemy
        """
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

        # État interne pour le suivi des pistes en cours de lecture
        self.current_tracks = {}

    def record_play_time(self, station_id: int, track_id: int, play_duration: float) -> bool:
        """
        Enregistre le temps de lecture d'une piste sur une station.

        Args:
            station_id: ID de la station radio
            track_id: ID de la piste
            play_duration: Durée de lecture en secondes

        Returns:
            True si l'enregistrement a réussi, False sinon
        """
        try:
            # Convertir play_duration en timedelta si ce n'est pas déjà le cas
            if isinstance(play_duration, (int, float)):
                play_duration_td = timedelta(seconds=play_duration)
            elif isinstance(play_duration, timedelta):
                play_duration_td = play_duration
            else:
                log_with_category(
                    logger,
                    "STATS_RECORDER",
                    "warning",
                    f"Invalid play_duration type: {type(play_duration)}, using 0 seconds",
                )
                play_duration_td = timedelta(seconds=0)

            # Vérifier que la station existe
            station = (
                self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
            )
            if not station:
                log_with_category(
                    logger, "STATS_RECORDER", "warning", f"Station with ID {station_id} not found"
                )
                return False

            # Vérifier que la piste existe
            track = self.db_session.query(Track).filter(Track.id == track_id).first()
            if not track:
                log_with_category(
                    logger, "STATS_RECORDER", "warning", f"Track with ID {track_id} not found"
                )
                return False

            # Créer un nouvel enregistrement de détection
            detection = TrackDetection(
                track_id=track_id,
                station_id=station_id,
                detected_at=datetime.utcnow(),
                play_duration=play_duration_td,
                confidence=0.8,  # Valeur par défaut, à remplacer par la valeur réelle
                detection_method="local",  # Valeur par défaut, à remplacer par la méthode réelle
            )
            self.db_session.add(detection)

            # Mettre à jour les statistiques de la station et de la piste
            self._update_station_track_stats(station_id, track_id, play_duration_td)

            # Mettre à jour les autres statistiques via StatsUpdater si disponible
            try:
                from backend.utils.analytics.stats_updater import StatsUpdater

                stats_updater = StatsUpdater(self.db_session)

                detection_result = {
                    "track_id": track_id,
                    "confidence": 0.8,
                    "detection_method": "local",
                }

                stats_updater.update_all_stats(
                    detection_result=detection_result,
                    station_id=station_id,
                    track=track,
                    play_duration=play_duration_td,
                )

                log_with_category(
                    logger,
                    "STATS_RECORDER",
                    "info",
                    f"Updated all stats for track ID {track_id} on station ID {station_id}",
                )
            except Exception as stats_error:
                log_with_category(
                    logger, "STATS_RECORDER", "error", f"Error updating stats: {stats_error}"
                )
                # Continuer même si la mise à jour des statistiques échoue

            self.db_session.commit()
            log_with_category(
                logger,
                "STATS_RECORDER",
                "info",
                f"Recorded play time for track ID {track_id} on station ID {station_id}: {play_duration_td.total_seconds()} seconds",
            )
            return True

        except Exception as e:
            log_with_category(logger, "STATS_RECORDER", "error", f"Error recording play time: {e}")
            self.db_session.rollback()
            return False

    def _update_station_track_stats(
        self, station_id: int, track_id: int, play_duration: timedelta
    ) -> None:
        """
        Met à jour les statistiques de lecture d'une piste sur une station.

        Args:
            station_id: ID de la station radio
            track_id: ID de la piste
            play_duration: Durée de lecture
        """
        try:
            # Rechercher les statistiques existantes
            stats = (
                self.db_session.query(StationTrackStats)
                .filter(
                    StationTrackStats.station_id == station_id,
                    StationTrackStats.track_id == track_id,
                )
                .first()
            )

            if stats:
                # Mettre à jour les statistiques existantes
                stats.play_count += 1
                stats.total_play_duration += play_duration
                stats.last_played_at = datetime.utcnow()
                log_with_category(
                    logger,
                    "STATS_RECORDER",
                    "debug",
                    f"Updated station track stats for track ID {track_id} on station ID {station_id}",
                )
            else:
                # Créer de nouvelles statistiques
                new_stats = StationTrackStats(
                    station_id=station_id,
                    track_id=track_id,
                    play_count=1,
                    total_play_duration=play_duration,
                    last_played_at=datetime.utcnow(),
                )
                self.db_session.add(new_stats)
                log_with_category(
                    logger,
                    "STATS_RECORDER",
                    "info",
                    f"Created new station track stats for track ID {track_id} on station ID {station_id}",
                )

            self.db_session.flush()

        except Exception as e:
            log_with_category(
                logger, "STATS_RECORDER", "error", f"Error updating station track stats: {e}"
            )
            # Ne pas faire de rollback ici, laisser la méthode appelante gérer la transaction

    def start_track_detection(
        self, track: Track, station_id: int, features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Démarre le suivi d'une nouvelle piste détectée sur une station.

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

            # Récupérer l'artiste
            artist = self.db_session.query(Artist).filter(Artist.id == track.artist_id).first()
            artist_name = artist.name if artist else "Unknown Artist"

            # Créer un dictionnaire pour suivre la piste en cours
            current_track = {
                "track_id": track.id,
                "title": track.title,
                "artist": artist_name,
                "start_time": start_time,
                "last_update_time": start_time,
                "play_duration": timedelta(seconds=0),
                "confidence": features.get("confidence", 0.8),
                "detection_method": features.get("detection_method", "unknown"),
            }

            # Stocker les informations de la piste en cours pour cette station
            self.current_tracks[station_id] = current_track

            log_with_category(
                logger,
                "STATS_RECORDER",
                "info",
                f"Started tracking track: {track.title} by {artist_name} on station ID {station_id}",
            )

            # Retourner les informations de la piste détectée
            return {
                "status": "success",
                "track": {
                    "id": track.id,
                    "title": track.title,
                    "artist": artist_name,
                    "album": track.album,
                    "isrc": track.isrc,
                },
                "detection": {
                    "start_time": start_time.isoformat(),
                    "confidence": features.get("confidence", 0.8),
                    "method": features.get("detection_method", "unknown"),
                },
                "station_id": station_id,
            }

        except Exception as e:
            log_with_category(
                logger, "STATS_RECORDER", "error", f"Error starting track detection: {e}"
            )
            return {"error": str(e)}

    def update_current_track(self, station_id: int, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Met à jour les informations de la piste en cours de lecture sur une station.

        Args:
            station_id: ID de la station radio
            features: Caractéristiques audio extraites

        Returns:
            Dict contenant les informations mises à jour sur la piste
        """
        try:
            # Vérifier si une piste est en cours de lecture sur cette station
            if station_id not in self.current_tracks:
                log_with_category(
                    logger,
                    "STATS_RECORDER",
                    "warning",
                    f"No current track for station ID {station_id}",
                )
                return {"error": "No current track for this station"}

            current = self.current_tracks[station_id]

            # Calculer le temps écoulé depuis la dernière mise à jour
            now = datetime.utcnow()
            time_since_last_update = now - current.get("last_update_time", current["start_time"])

            # Mettre à jour la durée totale avec le temps réel écoulé
            current["play_duration"] += time_since_last_update
            current["last_update_time"] = now

            log_with_category(
                logger,
                "STATS_RECORDER",
                "debug",
                f"Updated current track for station ID {station_id}: +{time_since_last_update.total_seconds()} seconds",
            )

            # Retourner les informations mises à jour
            return {
                "status": "success",
                "track": {
                    "id": current["track_id"],
                    "title": current["title"],
                    "artist": current["artist"],
                },
                "detection": {
                    "start_time": current["start_time"].isoformat(),
                    "current_time": now.isoformat(),
                    "play_duration": current["play_duration"].total_seconds(),
                    "confidence": current["confidence"],
                    "method": current["detection_method"],
                },
                "station_id": station_id,
            }

        except Exception as e:
            log_with_category(
                logger, "STATS_RECORDER", "error", f"Error updating current track: {e}"
            )
            return {"error": str(e)}

    def end_current_track(self, station_id: int) -> Optional[Dict[str, Any]]:
        """
        Termine le suivi de la piste en cours de lecture sur une station.

        Args:
            station_id: ID de la station radio

        Returns:
            Dict contenant les informations finales sur la piste ou None si aucune piste en cours
        """
        try:
            # Vérifier si une piste est en cours de lecture sur cette station
            if station_id not in self.current_tracks:
                log_with_category(
                    logger,
                    "STATS_RECORDER",
                    "warning",
                    f"No current track for station ID {station_id}",
                )
                return None

            current = self.current_tracks[station_id]

            # Calculer le temps écoulé depuis la dernière mise à jour
            now = datetime.utcnow()
            time_since_last_update = now - current.get("last_update_time", current["start_time"])

            # Ajouter le dernier intervalle de temps à la durée totale
            current["play_duration"] += time_since_last_update

            # Enregistrer le temps de lecture total
            total_duration = current["play_duration"].total_seconds()
            self.record_play_time(station_id, current["track_id"], total_duration)

            # Préparer les informations finales
            result = {
                "status": "success",
                "track": {
                    "id": current["track_id"],
                    "title": current["title"],
                    "artist": current["artist"],
                },
                "detection": {
                    "start_time": current["start_time"].isoformat(),
                    "end_time": now.isoformat(),
                    "play_duration": total_duration,
                    "confidence": current["confidence"],
                    "method": current["detection_method"],
                },
                "station_id": station_id,
            }

            # Supprimer la piste en cours pour cette station
            del self.current_tracks[station_id]

            log_with_category(
                logger,
                "STATS_RECORDER",
                "info",
                f"Ended tracking track ID {current['track_id']} on station ID {station_id}: {total_duration} seconds",
            )

            return result

        except Exception as e:
            log_with_category(logger, "STATS_RECORDER", "error", f"Error ending current track: {e}")
            self.db_session.rollback()
            return {"error": str(e)}

    def record_detection(self, detection_result: Dict[str, Any], station_id: int) -> Dict[str, Any]:
        """
        Enregistre une détection réussie et met à jour les statistiques.

        Args:
            detection_result: Résultat de la détection
            station_id: ID de la station radio

        Returns:
            Dict contenant les informations sur la détection
        """
        try:
            # Extraire les informations de la piste
            track_info = detection_result.get("track", {})
            track_id = track_info.get("id")

            if not track_id:
                log_with_category(
                    logger, "STATS_RECORDER", "error", "No track ID in detection result"
                )
                return {"error": "No track ID in detection result"}

            # Récupérer la piste
            track = self.db_session.query(Track).filter(Track.id == track_id).first()
            if not track:
                log_with_category(
                    logger, "STATS_RECORDER", "error", f"Track with ID {track_id} not found"
                )
                return {"error": f"Track with ID {track_id} not found"}

            # Extraire la durée du résultat de détection
            duration = detection_result.get("duration", 0)

            # Terminer la piste en cours si elle existe
            self.end_current_track(station_id)

            # Créer un enregistrement de détection
            detection = TrackDetection(
                track_id=track.id,
                station_id=station_id,
                detected_at=datetime.utcnow(),
                confidence=detection_result.get("confidence", 0.8),
                method=detection_result.get("method", "unknown"),
                play_duration=duration,  # Utiliser la durée extraite
            )
            self.db_session.add(detection)

            # Mettre à jour les statistiques de la station
            station_track_stats = (
                self.db_session.query(StationTrackStats)
                .filter(
                    StationTrackStats.station_id == station_id,
                    StationTrackStats.track_id == track.id,
                )
                .first()
            )

            if not station_track_stats:
                # Créer de nouvelles statistiques si elles n'existent pas
                station_track_stats = StationTrackStats(
                    station_id=station_id,
                    track_id=track.id,
                    detection_count=1,
                    total_play_duration=duration,
                    last_detected_at=datetime.utcnow(),
                )
                self.db_session.add(station_track_stats)
            else:
                # Mettre à jour les statistiques existantes
                station_track_stats.detection_count += 1
                station_track_stats.total_play_duration += duration
                station_track_stats.last_detected_at = datetime.utcnow()

            # Valider les changements
            self.db_session.commit()

            # Récupérer l'artiste
            artist = self.db_session.query(Artist).filter(Artist.id == track.artist_id).first()
            artist_name = artist.name if artist else "Unknown Artist"

            log_with_category(
                logger,
                "STATS_RECORDER",
                "info",
                f"Recorded detection: {track.title} by {artist_name} on station ID {station_id} with duration {duration:.2f}s",
            )

            # Retourner les informations de la détection
            return {
                "success": True,
                "track_id": track.id,
                "detection_id": detection.id,
                "track": {
                    "title": track.title,
                    "artist": artist_name,
                    "album": track.album,
                    "isrc": track.isrc,
                },
                "detection": {
                    "time": detection.detected_at.isoformat(),
                    "confidence": detection.confidence,
                    "method": detection.method,
                    "duration": duration,  # Inclure la durée dans le résultat
                },
                "station_id": station_id,
            }

        except Exception as e:
            log_with_category(logger, "STATS_RECORDER", "error", f"Error recording detection: {e}")
            self.db_session.rollback()
            return {"error": str(e)}
