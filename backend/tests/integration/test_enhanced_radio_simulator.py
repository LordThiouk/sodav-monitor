"""
Tests d'intégration pour le simulateur de radio amélioré.

Ce module contient des tests qui vérifient le bon fonctionnement du simulateur
de radio amélioré avec notre nouveau système de suivi de la durée de lecture.
"""

import logging
import time
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from backend.detection.audio_processor.play_duration_tracker import PlayDurationTracker
from backend.detection.audio_processor.track_manager.track_manager import TrackManager
from backend.models.models import RadioStation, Track, TrackDetection, Artist
from backend.tests.utils.enhanced_radio_simulator import EnhancedRadioSimulator

logger = logging.getLogger(__name__)


@pytest.fixture
def test_artists(db_session: Session):
    """Crée des artistes de test."""
    artists = []
    for i in range(3):
        artist = Artist(name=f"Test Artist {i}")
        db_session.add(artist)
        db_session.commit()
        artists.append(artist)
    return artists


@pytest.fixture
def test_tracks(db_session: Session, test_artists):
    """Crée des pistes de test."""
    tracks = []
    for i, artist in enumerate(test_artists):
        track = Track(
            title=f"Test Track {i}",
            artist_id=artist.id,
            isrc=f"TESTISRC{i:05d}",
        )
        db_session.add(track)
        db_session.commit()
        tracks.append(track)
    return tracks


@pytest.fixture
def test_station(db_session: Session):
    """Crée une station de test."""
    station = RadioStation(
        name="Test Station",
        url="http://test.station/stream",
        country="SN",
        language="fr",
        active=True,
    )
    db_session.add(station)
    db_session.commit()
    return station


@pytest.fixture
def track_manager(db_session: Session):
    """Crée un gestionnaire de pistes."""
    return TrackManager(db_session)


@pytest.fixture
def radio_simulator(test_tracks, test_station):
    """Crée un simulateur de radio amélioré."""
    return EnhancedRadioSimulator(
        tracks=test_tracks,
        station=test_station,
        segment_duration=2.0,  # 2 secondes par segment
        interruption_probability=0.3,  # 30% de chance d'interruption
        interruption_duration=1.0,  # 1 seconde d'interruption
    )


class TestEnhancedRadioSimulator:
    """Tests pour le simulateur de radio amélioré."""

    def test_play_duration_tracking(self, radio_simulator, track_manager, db_session):
        """Teste le suivi de la durée de lecture avec le simulateur de radio amélioré."""
        # Démarrer le simulateur
        radio_simulator.start()

        # Attendre que quelques segments soient joués
        time.sleep(10.0)

        # Arrêter le simulateur
        radio_simulator.stop()

        # Récupérer les logs du simulateur
        logs = radio_simulator.get_logs()

        # Vérifier qu'il y a des logs
        assert len(logs) > 0

        # Vérifier que les durées de lecture sont correctes
        for track_id, track_logs in radio_simulator.get_track_logs().items():
            # Calculer la durée totale de lecture selon les logs
            total_duration = sum(log["duration"] for log in track_logs if log["event"] == "track_end")

            # Récupérer les détections pour cette piste
            detections = (
                db_session.query(TrackDetection)
                .filter(TrackDetection.track_id == track_id)
                .all()
            )

            # Vérifier qu'il y a au moins une détection
            assert len(detections) > 0

            # Calculer la durée totale de lecture selon les détections
            detected_duration = sum(d.play_duration.total_seconds() for d in detections)

            # Vérifier que les durées sont proches (avec une tolérance de 1 seconde)
            assert abs(total_duration - detected_duration) < 1.0, (
                f"Durée incorrecte pour la piste {track_id}. "
                f"Attendu: {total_duration}s, Obtenu: {detected_duration}s"
            )

    def test_interrupted_track_detection(self, radio_simulator, track_manager, db_session):
        """Teste la détection des pistes interrompues."""
        # Configurer le simulateur pour une interruption certaine
        radio_simulator.interruption_probability = 1.0
        radio_simulator.interruption_duration = 0.5  # Courte interruption

        # Démarrer le simulateur
        radio_simulator.start()

        # Attendre que quelques segments soient joués
        time.sleep(10.0)

        # Arrêter le simulateur
        radio_simulator.stop()

        # Récupérer les logs du simulateur
        logs = radio_simulator.get_logs()

        # Vérifier qu'il y a des logs
        assert len(logs) > 0

        # Compter les interruptions
        interruptions = [log for log in logs if log["event"] == "interruption"]
        assert len(interruptions) > 0

        # Vérifier que les pistes interrompues ont été correctement détectées
        for track_id, track_logs in radio_simulator.get_track_logs().items():
            # Compter les interruptions pour cette piste
            track_interruptions = [
                log for log in track_logs if log["event"] == "interruption"
            ]
            
            if not track_interruptions:
                continue
                
            # Récupérer les détections pour cette piste
            detections = (
                db_session.query(TrackDetection)
                .filter(TrackDetection.track_id == track_id)
                .all()
            )
            
            # Vérifier qu'il y a au moins une détection
            assert len(detections) > 0
            
            # Vérifier que le nombre de détections est cohérent
            # Si les interruptions sont correctement gérées, il devrait y avoir moins de détections
            # que d'interruptions + 1 (car certaines interruptions sont fusionnées)
            assert len(detections) <= len(track_interruptions) + 1
            
    def test_play_duration_accuracy(self, radio_simulator, track_manager, db_session):
        """Teste la précision de la durée de lecture."""
        # Configurer le simulateur sans interruption
        radio_simulator.interruption_probability = 0.0
        
        # Démarrer le simulateur avec une durée fixe
        fixed_duration = 5.0  # 5 secondes
        radio_simulator.start(fixed_duration=fixed_duration)
        
        # Attendre que la lecture soit terminée
        time.sleep(fixed_duration + 1.0)
        
        # Arrêter le simulateur
        radio_simulator.stop()
        
        # Récupérer les logs du simulateur
        logs = radio_simulator.get_logs()
        
        # Vérifier qu'il y a des logs
        assert len(logs) > 0
        
        # Récupérer la piste jouée
        track_id = logs[0]["track_id"]
        
        # Récupérer les détections pour cette piste
        detections = (
            db_session.query(TrackDetection)
            .filter(TrackDetection.track_id == track_id)
            .all()
        )
        
        # Vérifier qu'il y a au moins une détection
        assert len(detections) > 0
        
        # Calculer la durée totale de lecture selon les détections
        detected_duration = sum(d.play_duration.total_seconds() for d in detections)
        
        # Vérifier que la durée est proche de la durée fixe (avec une tolérance de 1 seconde)
        assert abs(fixed_duration - detected_duration) < 1.0, (
            f"Durée incorrecte. Attendu: {fixed_duration}s, Obtenu: {detected_duration}s"
        ) 