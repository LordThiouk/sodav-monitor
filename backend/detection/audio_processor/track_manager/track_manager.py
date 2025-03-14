"""
Module principal de gestion des pistes audio.

Ce module contient la classe TrackManager qui coordonne les différentes
opérations liées aux pistes audio, en déléguant aux classes spécialisées.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from backend.detection.audio_processor.play_duration_tracker import PlayDurationTracker
from backend.detection.audio_processor.track_manager.external_detection import (
    ExternalDetectionService,
)
from backend.detection.audio_processor.track_manager.fingerprint_handler import FingerprintHandler
from backend.detection.audio_processor.track_manager.stats_recorder import StatsRecorder

# Import des classes spécialisées
from backend.detection.audio_processor.track_manager.track_creator import TrackCreator
from backend.detection.audio_processor.track_manager.track_finder import TrackFinder
from backend.models.models import Artist, RadioStation, Track, TrackDetection
from backend.utils.logging import log_with_category

logger = logging.getLogger(__name__)


class TrackManager:
    """
    Classe principale pour la gestion des pistes audio.

    Cette classe sert de façade pour les différentes opérations liées aux pistes audio,
    en déléguant les responsabilités spécifiques aux classes spécialisées.
    """

    def __init__(self, db_session: Session, feature_extractor=None):
        """
        Initialise un nouveau TrackManager.

        Args:
            db_session: Session de base de données SQLAlchemy
            feature_extractor: Extracteur de caractéristiques audio (optionnel)
        """
        self.db_session = db_session
        self.feature_extractor = feature_extractor
        self.logger = logging.getLogger(__name__)

        # Initialisation des composants spécialisés
        self.track_creator = TrackCreator(db_session)
        self.track_finder = TrackFinder(db_session)
        self.stats_recorder = StatsRecorder(db_session)
        self.external_service = ExternalDetectionService(db_session)
        self.fingerprint_handler = FingerprintHandler()
        
        # Initialisation du tracker de durée de lecture
        self.play_duration_tracker = PlayDurationTracker(db_session)
        
        # Planifier le nettoyage périodique des pistes interrompues
        self._schedule_cleanup()
        
    def _schedule_cleanup(self):
        """
        Planifie le nettoyage périodique des pistes interrompues.
        """
        import threading
        
        def cleanup_task():
            self.play_duration_tracker.cleanup_interrupted_tracks()
            # Planifier la prochaine exécution dans 30 secondes
            threading.Timer(30.0, cleanup_task).start()
        
        # Démarrer le premier nettoyage après 30 secondes
        threading.Timer(30.0, cleanup_task).start()
        
    async def process_track(
        self, features: Dict[str, Any], station_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Traite les caractéristiques audio pour détecter et enregistrer une piste.

        Cette méthode coordonne le processus de détection et d'enregistrement d'une piste
        en déléguant aux différentes classes spécialisées.

        Args:
            features: Caractéristiques audio extraites
            station_id: ID de la station radio (optionnel)

        Returns:
            Dictionnaire contenant les résultats du traitement
        """
        try:
            log_with_category(
                logger, "TRACK_MANAGER", "info", f"Processing track for station ID: {station_id}"
            )

            # Extraire la durée des caractéristiques
            duration = features.get("duration", features.get("play_duration", 0))
            fingerprint = features.get("fingerprint", "")

            # 1. Rechercher une correspondance locale
            result = await self.track_finder.find_local_match(features)
            if result:
                log_with_category(
                    logger,
                    "TRACK_MANAGER",
                    "info",
                    f"Found local match: {result['track']['title']} by {result['track']['artist']}",
                )
                # Ajouter la durée au résultat
                result["duration"] = duration
                
                # Démarrer le suivi de la durée de lecture
                track_id = result['track']['id']
                start_time = self.play_duration_tracker.start_tracking(
                    station_id, track_id, fingerprint
                )
                
                # Créer la détection avec le tracker
                detection = self.play_duration_tracker.create_detection(
                    station_id=station_id,
                    track_id=track_id,
                    confidence=result.get('confidence', 0.8),
                    fingerprint=fingerprint,
                    detection_method=result.get('method', 'local')
                )
                
                if detection:
                    result['detection_id'] = detection.id
                    result['success'] = True
                    return result
                
                return self.stats_recorder.record_detection(result, station_id)

            # 2. Si aucune correspondance locale n'est trouvée, vérifier si un ISRC est disponible
            isrc = features.get("isrc")
            if isrc:
                isrc_result = await self.track_finder.find_track_by_isrc(isrc)
                if isrc_result:
                    log_with_category(
                        logger,
                        "TRACK_MANAGER",
                        "info",
                        f"Found match by ISRC: {isrc_result['track']['title']} by {isrc_result['track']['artist']}",
                    )
                    # Ajouter la durée au résultat
                    isrc_result["duration"] = duration
                    
                    # Démarrer le suivi de la durée de lecture
                    track_id = isrc_result['track']['id']
                    start_time = self.play_duration_tracker.start_tracking(
                        station_id, track_id, fingerprint
                    )
                    
                    # Créer la détection avec le tracker
                    detection = self.play_duration_tracker.create_detection(
                        station_id=station_id,
                        track_id=track_id,
                        confidence=isrc_result.get('confidence', 0.8),
                        fingerprint=fingerprint,
                        detection_method=isrc_result.get('method', 'isrc')
                    )
                    
                    if detection:
                        isrc_result['detection_id'] = detection.id
                        isrc_result['success'] = True
                        return isrc_result
                    
                    return self.stats_recorder.record_detection(isrc_result, station_id)

            # 3. Si toujours aucune correspondance, essayer les services externes
            external_result = await self.external_service.find_external_match(features, station_id)
            if external_result:
                log_with_category(
                    logger,
                    "TRACK_MANAGER",
                    "info",
                    f"Found external match: {external_result['track']['title']} by {external_result['track']['artist']}",
                )

                # Créer ou récupérer la piste dans la base de données
                track_info = external_result["track"]
                artist_id = await self.track_creator.get_or_create_artist(
                    track_info.get("artist", "Unknown Artist")
                )

                if not artist_id:
                    log_with_category(logger, "TRACK_MANAGER", "error", "Failed to create artist")
                    return {"error": "Failed to create artist"}

                track = await self.track_creator.get_or_create_track(
                    title=track_info.get("title", "Unknown Track"),
                    artist_id=artist_id,
                    album=track_info.get("album"),
                    isrc=track_info.get("isrc"),
                    release_date=track_info.get("release_date"),
                )

                if not track:
                    log_with_category(logger, "TRACK_MANAGER", "error", "Failed to create track")
                    return {"error": "Failed to create track"}

                # Enregistrer l'empreinte digitale si disponible
                if fingerprint:
                    await self.fingerprint_handler.store_fingerprint(track.id, fingerprint)

                # Démarrer le suivi de la durée de lecture
                start_time = self.play_duration_tracker.start_tracking(
                    station_id, track.id, fingerprint
                )
                
                # Créer la détection avec le tracker
                detection = self.play_duration_tracker.create_detection(
                    station_id=station_id,
                    track_id=track.id,
                    confidence=external_result.get('confidence', 0.8),
                    fingerprint=fingerprint,
                    detection_method=external_result.get('method', 'external')
                )
                
                if detection:
                    result = {
                        "track": {
                            "id": track.id,
                            "title": track.title,
                            "artist": track_info.get("artist", "Unknown Artist"),
                        },
                        "confidence": external_result.get("confidence", 0.8),
                        "method": external_result.get("method", "external"),
                        "duration": duration,
                        "detection_id": detection.id,
                        "success": True
                    }
                    return result

                # Préparer le résultat pour l'enregistrement des statistiques
                detection_result = {
                    "track": {
                        "id": track.id,
                        "title": track.title,
                        "artist": track_info.get("artist", "Unknown Artist"),
                    },
                    "confidence": external_result.get("confidence", 0.8),
                    "method": external_result.get("method", "external"),
                    "duration": duration,  # Ajouter la durée au résultat
                }

                return self.stats_recorder.record_detection(detection_result, station_id)

            # 4. Si aucune correspondance n'est trouvée, retourner une erreur
            log_with_category(logger, "TRACK_MANAGER", "warning", "No match found for track")
            return {"error": "No match found for track", "success": False}

        except Exception as e:
            log_with_category(logger, "TRACK_MANAGER", "error", f"Error processing track: {e}")
            return {"error": str(e), "success": False}
            
    def update_track_detection(self, station_id: int, track_id: int) -> None:
        """
        Met à jour le suivi de la durée de lecture pour une piste sur une station.
        
        Args:
            station_id: ID de la station radio
            track_id: ID de la piste
        """
        self.play_duration_tracker.update_tracking(station_id, track_id)
        
    def stop_track_detection(self, station_id: int, track_id: int, is_silence: bool = False) -> Optional[timedelta]:
        """
        Arrête le suivi de la durée de lecture pour une piste sur une station.
        
        Args:
            station_id: ID de la station radio
            track_id: ID de la piste
            is_silence: Indique si l'arrêt est dû à un silence
            
        Returns:
            Durée totale de lecture ou None si la piste n'était pas suivie
        """
        return self.play_duration_tracker.stop_tracking(station_id, track_id, is_silence)
        
    def get_active_tracks(self) -> List[Dict]:
        """
        Retourne la liste des pistes actuellement suivies.
        
        Returns:
            Liste des pistes actives avec leurs informations de suivi
        """
        return self.play_duration_tracker.get_active_tracks()

    async def process_station_data(self, station_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite les données d'une station radio.

        Args:
            station_data: Données de la station radio

        Returns:
            Dictionnaire contenant les résultats du traitement
        """
        try:
            station_id = station_data.get("station_id")
            if not station_id:
                return {"error": "No station ID provided"}

            # Vérifier si la station existe
            station = (
                self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
            )
            if not station:
                log_with_category(
                    logger, "TRACK_MANAGER", "error", f"Station with ID {station_id} not found"
                )
                return {"error": f"Station with ID {station_id} not found"}

            # Extraire les caractéristiques audio
            features = station_data.get("features", {})
            if not features:
                log_with_category(logger, "TRACK_MANAGER", "warning", "No features provided")
                return {"error": "No features provided"}

            # Traiter les caractéristiques audio
            return await self.process_track(features, station_id)

        except Exception as e:
            log_with_category(
                logger, "TRACK_MANAGER", "error", f"Error processing station data: {e}"
            )
            return {"error": str(e)}

    async def get_or_create_track(
        self,
        title: str,
        artist_name: str,
        album: Optional[str] = None,
        isrc: Optional[str] = None,
        label: Optional[str] = None,
        release_date: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> Optional[Track]:
        """
        Récupère ou crée une piste dans la base de données.

        Cette méthode est une façade pour la méthode correspondante dans TrackCreator.

        Args:
            title: Titre de la piste
            artist_name: Nom de l'artiste
            album: Nom de l'album (optionnel)
            isrc: Code ISRC (optionnel)
            label: Label (optionnel)
            release_date: Date de sortie (optionnel)
            duration: Durée de la piste en secondes (optionnel)

        Returns:
            Objet Track ou None en cas d'erreur
        """
        try:
            # Récupérer ou créer l'artiste
            artist_id = await self.track_creator.get_or_create_artist(artist_name)
            if not artist_id:
                return None

            # Récupérer ou créer la piste
            return await self.track_creator.get_or_create_track(
                title=title,
                artist_id=artist_id,
                album=album,
                isrc=isrc,
                label=label,
                release_date=release_date,
                duration=duration,
            )

        except Exception as e:
            log_with_category(
                logger, "TRACK_MANAGER", "error", f"Error getting or creating track: {e}"
            )
            return None

    def record_play_time(self, station_id: int, track_id: int, play_duration: float) -> bool:
        """
        Enregistre le temps de lecture d'une piste sur une station.

        Cette méthode utilise maintenant le PlayDurationTracker pour un suivi plus précis.

        Args:
            station_id: ID de la station radio
            track_id: ID de la piste
            play_duration: Durée de lecture en secondes

        Returns:
            True si l'enregistrement a réussi, False sinon
        """
        try:
            # Vérifier que la station existe
            station = (
                self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
            )
            if not station:
                log_with_category(
                    logger, "TRACK_MANAGER", "warning", f"Station with ID {station_id} not found"
                )
                return False

            # Vérifier que la piste existe
            track = self.db_session.query(Track).filter(Track.id == track_id).first()
            if not track:
                log_with_category(
                    logger, "TRACK_MANAGER", "warning", f"Track with ID {track_id} not found"
                )
                return False
                
            # Récupérer l'empreinte digitale de la piste si disponible
            fingerprint = self.fingerprint_handler.get_fingerprint(track_id) or "unknown"
            
            # Démarrer le suivi de la durée de lecture
            self.play_duration_tracker.start_tracking(station_id, track_id, fingerprint)
            
            # Créer la détection avec le tracker
            detection = self.play_duration_tracker.create_detection(
                station_id=station_id,
                track_id=track_id,
                confidence=0.8,  # Valeur par défaut
                fingerprint=fingerprint,
                detection_method="manual"  # Méthode manuelle
            )
            
            if detection:
                log_with_category(
                    logger,
                    "TRACK_MANAGER",
                    "info",
                    f"Recorded play time for track ID {track_id} on station ID {station_id}: {play_duration} seconds"
                )
                return True
                
            # Fallback à l'ancienne méthode si la nouvelle échoue
            return self.stats_recorder.record_play_time(station_id, track_id, play_duration)
            
        except Exception as e:
            log_with_category(
                logger, "TRACK_MANAGER", "error", f"Error recording play time: {e}"
            )
            # Fallback à l'ancienne méthode
            return self.stats_recorder.record_play_time(station_id, track_id, play_duration)

    async def find_track_by_isrc(self, isrc: str) -> Optional[Dict[str, Any]]:
        """
        Recherche une piste par son code ISRC dans la base de données.

        Cette méthode est une façade pour la méthode correspondante dans TrackFinder.

        Args:
            isrc: Code ISRC à rechercher

        Returns:
            Dictionnaire contenant les informations de la piste ou None si aucune correspondance
        """
        return await self.track_finder.find_track_by_isrc(isrc)

    async def find_local_match(self, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Recherche une correspondance locale pour les caractéristiques audio fournies.

        Cette méthode est une façade pour la méthode correspondante dans TrackFinder.

        Args:
            features: Caractéristiques audio extraites

        Returns:
            Dictionnaire contenant les informations de la piste correspondante ou None si aucune correspondance
        """
        return await self.track_finder.find_local_match(features)

    async def find_external_match(
        self, features: Dict[str, Any], station_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Recherche une correspondance via les services externes.

        Cette méthode est une façade pour la méthode correspondante dans ExternalDetectionService.

        Args:
            features: Caractéristiques audio extraites
            station_id: ID de la station radio (optionnel)

        Returns:
            Dictionnaire contenant les informations de la piste ou None si aucune correspondance
        """
        return await self.external_service.find_external_match(features, station_id)

    def extract_fingerprint(self, features: Dict[str, Any]) -> Optional[str]:
        """
        Extrait une empreinte digitale à partir des caractéristiques audio.

        Cette méthode est une façade pour la méthode correspondante dans FingerprintHandler.

        Args:
            features: Caractéristiques audio extraites

        Returns:
            Empreinte digitale sous forme de chaîne de caractères ou None si l'extraction échoue
        """
        return self.fingerprint_handler.extract_fingerprint(features)

    def compare_fingerprints(self, fingerprint1: str, fingerprint2: str) -> float:
        """
        Compare deux empreintes digitales et retourne un score de similarité.

        Cette méthode est une façade pour la méthode correspondante dans FingerprintHandler.

        Args:
            fingerprint1: Première empreinte digitale
            fingerprint2: Deuxième empreinte digitale

        Returns:
            Score de similarité entre 0.0 et 1.0
        """
        return self.fingerprint_handler.compare_fingerprints(fingerprint1, fingerprint2)
