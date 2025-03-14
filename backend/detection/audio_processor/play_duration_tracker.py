"""
Module pour le suivi précis de la durée de lecture des morceaux.

Ce module implémente un système de suivi de la durée de lecture qui gère :
- Le démarrage et l'arrêt du timer lorsqu'un morceau est détecté
- La vérification continue si le même morceau est toujours joué
- La fusion des détections lorsqu'un morceau est interrompu puis reprend
- L'enregistrement précis de la durée de lecture
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List

from sqlalchemy.orm import Session

from backend.models.models import TrackDetection, Track, RadioStation

logger = logging.getLogger(__name__)


class PlayDurationTracker:
    """
    Classe responsable du suivi précis de la durée de lecture des morceaux.
    
    Cette classe implémente les règles définies pour le calcul de la durée de lecture :
    - Démarrer un timer lorsqu'un son est détecté
    - Vérifier en continu si le même son est toujours joué
    - Arrêter le timer lorsque le son change ou que le silence est détecté
    - Fusionner les lectures si un son redémarre après une pause courte
    """

    def __init__(self, db_session: Session):
        """
        Initialise le tracker de durée de lecture.
        
        Args:
            db_session: Session de base de données
        """
        self.db_session = db_session
        self.active_tracks: Dict[Tuple[int, int], Dict] = {}  # (station_id, track_id) -> track_info
        self.interrupted_tracks: Dict[Tuple[int, int], Dict] = {}  # Pistes interrompues récemment
        self.merge_threshold = 10  # Seuil en secondes pour fusionner les détections
        self.min_duration_threshold = 5  # Durée minimale en secondes pour enregistrer une détection

    def start_tracking(self, station_id: int, track_id: int, fingerprint: str) -> datetime:
        """
        Démarre le suivi de la durée de lecture pour une piste sur une station.
        
        Args:
            station_id: ID de la station
            track_id: ID de la piste
            fingerprint: Empreinte acoustique de la piste
            
        Returns:
            Timestamp de début de lecture
        """
        now = datetime.utcnow()
        key = (station_id, track_id)
        
        # Vérifier si cette piste a été interrompue récemment
        if key in self.interrupted_tracks:
            interrupted_info = self.interrupted_tracks[key]
            time_since_interruption = (now - interrupted_info["end_time"]).total_seconds()
            
            # Si la piste a été interrompue il y a moins de X secondes, on reprend le suivi
            if time_since_interruption <= self.merge_threshold:
                logger.info(
                    f"Reprise de la piste ID {track_id} sur la station ID {station_id} "
                    f"après {time_since_interruption:.2f}s d'interruption"
                )
                
                # Récupérer l'ancienne détection pour la mettre à jour plus tard
                self.active_tracks[key] = {
                    "start_time": interrupted_info["start_time"],
                    "last_update": now,
                    "fingerprint": fingerprint,
                    "detection_id": interrupted_info["detection_id"],
                    "accumulated_duration": interrupted_info["accumulated_duration"],
                    "is_resumed": True
                }
                
                # Supprimer des pistes interrompues
                del self.interrupted_tracks[key]
                
                return interrupted_info["start_time"]
        
        # Nouvelle détection
        self.active_tracks[key] = {
            "start_time": now,
            "last_update": now,
            "fingerprint": fingerprint,
            "detection_id": None,  # Sera défini lors de la création de la détection
            "accumulated_duration": timedelta(0),
            "is_resumed": False
        }
        
        logger.info(f"Début du suivi de la piste ID {track_id} sur la station ID {station_id}")
        return now

    def update_tracking(self, station_id: int, track_id: int) -> None:
        """
        Met à jour le suivi de la durée de lecture pour une piste sur une station.
        
        Args:
            station_id: ID de la station
            track_id: ID de la piste
        """
        key = (station_id, track_id)
        now = datetime.utcnow()
        
        if key in self.active_tracks:
            self.active_tracks[key]["last_update"] = now
            logger.debug(f"Mise à jour du suivi de la piste ID {track_id} sur la station ID {station_id}")

    def stop_tracking(self, station_id: int, track_id: int, is_silence: bool = False) -> Optional[timedelta]:
        """
        Arrête le suivi de la durée de lecture pour une piste sur une station.
        
        Args:
            station_id: ID de la station
            track_id: ID de la piste
            is_silence: Indique si l'arrêt est dû à un silence
            
        Returns:
            Durée totale de lecture ou None si la piste n'était pas suivie
        """
        key = (station_id, track_id)
        now = datetime.utcnow()
        
        if key not in self.active_tracks:
            logger.warning(f"Tentative d'arrêt du suivi d'une piste non suivie: {track_id} sur {station_id}")
            return None
        
        track_info = self.active_tracks[key]
        
        # Calculer la durée de cette session
        session_duration = now - track_info["last_update"]
        
        # Calculer la durée totale
        total_duration = track_info["accumulated_duration"] + (now - track_info["start_time"])
        
        # Si c'est un silence et que la durée est courte, on garde la piste en mémoire
        # pour une possible fusion si elle reprend rapidement
        if is_silence:
            self.interrupted_tracks[key] = {
                "start_time": track_info["start_time"],
                "end_time": now,
                "fingerprint": track_info["fingerprint"],
                "detection_id": track_info["detection_id"],
                "accumulated_duration": total_duration,
            }
            logger.info(
                f"Interruption de la piste ID {track_id} sur la station ID {station_id}, "
                f"durée accumulée: {total_duration.total_seconds():.2f}s"
            )
        else:
            logger.info(
                f"Fin du suivi de la piste ID {track_id} sur la station ID {station_id}, "
                f"durée totale: {total_duration.total_seconds():.2f}s"
            )
        
        # Supprimer la piste des pistes actives
        del self.active_tracks[key]
        
        return total_duration

    def create_detection(
        self, 
        station_id: int, 
        track_id: int, 
        confidence: float, 
        fingerprint: str,
        detection_method: str
    ) -> Optional[TrackDetection]:
        """
        Crée une détection en base de données.
        
        Args:
            station_id: ID de la station
            track_id: ID de la piste
            confidence: Niveau de confiance de la détection
            fingerprint: Empreinte acoustique
            detection_method: Méthode de détection utilisée
            
        Returns:
            Objet TrackDetection créé ou None en cas d'erreur
        """
        key = (station_id, track_id)
        
        if key not in self.active_tracks:
            logger.warning(f"Tentative de création d'une détection pour une piste non suivie: {track_id} sur {station_id}")
            return None
        
        track_info = self.active_tracks[key]
        
        try:
            # Créer une nouvelle détection ou mettre à jour une détection existante
            if track_info.get("is_resumed") and track_info.get("detection_id"):
                # Mettre à jour la détection existante
                detection = self.db_session.query(TrackDetection).get(track_info["detection_id"])
                if detection:
                    detection.end_time = datetime.utcnow()
                    detection.play_duration = datetime.utcnow() - track_info["start_time"]
                    self.db_session.commit()
                    logger.info(
                        f"Mise à jour de la détection ID {detection.id} pour la piste ID {track_id} "
                        f"sur la station ID {station_id}, durée: {detection.play_duration.total_seconds():.2f}s"
                    )
                    return detection
            
            # Créer une nouvelle détection
            detection = TrackDetection(
                track_id=track_id,
                station_id=station_id,
                confidence=confidence,
                detected_at=track_info["start_time"],
                end_time=datetime.utcnow(),
                play_duration=datetime.utcnow() - track_info["start_time"],
                fingerprint=fingerprint,
                detection_method=detection_method
            )
            
            self.db_session.add(detection)
            self.db_session.commit()
            self.db_session.refresh(detection)
            
            # Mettre à jour l'ID de détection dans le suivi
            track_info["detection_id"] = detection.id
            
            logger.info(
                f"Création de la détection ID {detection.id} pour la piste ID {track_id} "
                f"sur la station ID {station_id}, durée: {detection.play_duration.total_seconds():.2f}s"
            )
            
            return detection
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Erreur lors de la création de la détection: {e}")
            return None

    def update_detection(self, detection_id: int, end_time: datetime, play_duration: timedelta) -> bool:
        """
        Met à jour une détection existante avec la durée de lecture finale.
        
        Args:
            detection_id: ID de la détection
            end_time: Heure de fin de lecture
            play_duration: Durée totale de lecture
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        try:
            detection = self.db_session.query(TrackDetection).get(detection_id)
            if not detection:
                logger.warning(f"Détection ID {detection_id} non trouvée")
                return False
            
            detection.end_time = end_time
            detection.play_duration = play_duration
            
            self.db_session.commit()
            logger.info(
                f"Mise à jour de la détection ID {detection_id}, "
                f"durée finale: {play_duration.total_seconds():.2f}s"
            )
            
            return True
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Erreur lors de la mise à jour de la détection: {e}")
            return False

    def cleanup_interrupted_tracks(self, max_age_seconds: int = 60) -> None:
        """
        Nettoie les pistes interrompues trop anciennes.
        
        Args:
            max_age_seconds: Âge maximum en secondes pour conserver une piste interrompue
        """
        now = datetime.utcnow()
        keys_to_remove = []
        
        for key, track_info in self.interrupted_tracks.items():
            age = (now - track_info["end_time"]).total_seconds()
            if age > max_age_seconds:
                keys_to_remove.append(key)
                
                # Si la durée accumulée est suffisante, finaliser la détection
                if track_info["accumulated_duration"].total_seconds() >= self.min_duration_threshold:
                    if track_info.get("detection_id"):
                        self.update_detection(
                            track_info["detection_id"],
                            track_info["end_time"],
                            track_info["accumulated_duration"]
                        )
                        logger.info(
                            f"Finalisation de la détection ID {track_info['detection_id']} "
                            f"pour une piste interrompue, durée: {track_info['accumulated_duration'].total_seconds():.2f}s"
                        )
        
        # Supprimer les pistes trop anciennes
        for key in keys_to_remove:
            del self.interrupted_tracks[key]
            
        if keys_to_remove:
            logger.info(f"Nettoyage de {len(keys_to_remove)} pistes interrompues trop anciennes")

    def get_active_tracks(self) -> List[Dict]:
        """
        Retourne la liste des pistes actuellement suivies.
        
        Returns:
            Liste des pistes actives avec leurs informations de suivi
        """
        result = []
        for (station_id, track_id), track_info in self.active_tracks.items():
            # Récupérer les informations sur la piste et la station
            track = self.db_session.query(Track).get(track_id)
            station = self.db_session.query(RadioStation).get(station_id)
            
            if track and station:
                current_duration = (datetime.utcnow() - track_info["start_time"]).total_seconds()
                result.append({
                    "track_id": track_id,
                    "track_title": track.title,
                    "station_id": station_id,
                    "station_name": station.name,
                    "start_time": track_info["start_time"],
                    "current_duration": current_duration,
                    "is_resumed": track_info.get("is_resumed", False)
                })
        
        return result 