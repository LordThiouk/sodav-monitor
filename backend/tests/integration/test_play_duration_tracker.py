"""
Tests d'intégration pour le suivi précis de la durée de lecture.

Ce module contient des tests qui vérifient le bon fonctionnement du système
de suivi de la durée de lecture, y compris la gestion des interruptions et
la fusion des détections.
"""

import logging
import time
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from backend.detection.audio_processor.play_duration_tracker import PlayDurationTracker
from backend.models.models import RadioStation, Track, TrackDetection, Artist

logger = logging.getLogger(__name__)


@pytest.fixture
def test_artist(db_session: Session):
    """Crée un artiste de test."""
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.commit()
    return artist


@pytest.fixture
def test_track(db_session: Session, test_artist: Artist):
    """Crée une piste de test."""
    track = Track(
        title="Test Track",
        artist_id=test_artist.id,
        isrc="TESTISRC12345",
    )
    db_session.add(track)
    db_session.commit()
    return track


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
def play_duration_tracker(db_session: Session):
    """Crée un tracker de durée de lecture."""
    return PlayDurationTracker(db_session)


class TestPlayDurationTracker:
    """Tests pour le tracker de durée de lecture."""

    def test_start_tracking(self, play_duration_tracker, test_track, test_station):
        """Teste le démarrage du suivi de la durée de lecture."""
        # Démarrer le suivi
        start_time = play_duration_tracker.start_tracking(
            test_station.id, test_track.id, "test_fingerprint"
        )

        # Vérifier que le suivi a bien démarré
        assert start_time is not None
        assert (datetime.utcnow() - start_time).total_seconds() < 1.0

        # Vérifier que la piste est bien dans les pistes actives
        active_tracks = play_duration_tracker.get_active_tracks()
        assert len(active_tracks) == 1
        assert active_tracks[0]["track_id"] == test_track.id
        assert active_tracks[0]["station_id"] == test_station.id

    def test_update_tracking(self, play_duration_tracker, test_track, test_station):
        """Teste la mise à jour du suivi de la durée de lecture."""
        # Démarrer le suivi
        play_duration_tracker.start_tracking(test_station.id, test_track.id, "test_fingerprint")

        # Attendre un peu
        time.sleep(0.1)

        # Mettre à jour le suivi
        play_duration_tracker.update_tracking(test_station.id, test_track.id)

        # Vérifier que la piste est toujours active
        active_tracks = play_duration_tracker.get_active_tracks()
        assert len(active_tracks) == 1
        assert active_tracks[0]["track_id"] == test_track.id
        assert active_tracks[0]["station_id"] == test_station.id

    def test_stop_tracking(self, play_duration_tracker, test_track, test_station):
        """Teste l'arrêt du suivi de la durée de lecture."""
        # Démarrer le suivi
        play_duration_tracker.start_tracking(test_station.id, test_track.id, "test_fingerprint")

        # Attendre un peu
        time.sleep(0.1)

        # Arrêter le suivi
        duration = play_duration_tracker.stop_tracking(test_station.id, test_track.id)

        # Vérifier que la durée est correcte
        assert duration is not None
        assert duration.total_seconds() > 0.0

        # Vérifier que la piste n'est plus active
        active_tracks = play_duration_tracker.get_active_tracks()
        assert len(active_tracks) == 0

    def test_create_detection(self, play_duration_tracker, test_track, test_station, db_session):
        """Teste la création d'une détection."""
        # Démarrer le suivi
        play_duration_tracker.start_tracking(test_station.id, test_track.id, "test_fingerprint")

        # Attendre un peu
        time.sleep(0.1)

        # Créer la détection
        detection = play_duration_tracker.create_detection(
            station_id=test_station.id,
            track_id=test_track.id,
            confidence=0.9,
            fingerprint="test_fingerprint",
            detection_method="test",
        )

        # Vérifier que la détection a été créée
        assert detection is not None
        assert detection.track_id == test_track.id
        assert detection.station_id == test_station.id
        assert detection.confidence == 0.9
        assert detection.fingerprint == "test_fingerprint"
        assert detection.detection_method == "test"
        assert detection.play_duration is not None
        assert detection.play_duration.total_seconds() > 0.0

        # Vérifier que la détection est bien dans la base de données
        db_detection = (
            db_session.query(TrackDetection)
            .filter(TrackDetection.id == detection.id)
            .first()
        )
        assert db_detection is not None
        assert db_detection.track_id == test_track.id
        assert db_detection.station_id == test_station.id

    def test_interrupted_track_resume(self, play_duration_tracker, test_track, test_station):
        """Teste la reprise d'une piste interrompue."""
        # Démarrer le suivi
        play_duration_tracker.start_tracking(test_station.id, test_track.id, "test_fingerprint")

        # Attendre un peu
        time.sleep(0.1)

        # Créer la détection
        detection = play_duration_tracker.create_detection(
            station_id=test_station.id,
            track_id=test_track.id,
            confidence=0.9,
            fingerprint="test_fingerprint",
            detection_method="test",
        )

        # Arrêter le suivi avec silence
        play_duration_tracker.stop_tracking(test_station.id, test_track.id, is_silence=True)

        # Vérifier que la piste n'est plus active
        active_tracks = play_duration_tracker.get_active_tracks()
        assert len(active_tracks) == 0

        # Attendre un peu (moins que le seuil de fusion)
        time.sleep(0.1)

        # Redémarrer le suivi
        start_time = play_duration_tracker.start_tracking(
            test_station.id, test_track.id, "test_fingerprint"
        )

        # Vérifier que la piste est à nouveau active
        active_tracks = play_duration_tracker.get_active_tracks()
        assert len(active_tracks) == 1
        assert active_tracks[0]["track_id"] == test_track.id
        assert active_tracks[0]["station_id"] == test_station.id
        assert active_tracks[0]["is_resumed"] == True

        # Vérifier que le start_time est celui de la première détection
        assert start_time < datetime.utcnow() - timedelta(seconds=0.1)

    def test_cleanup_interrupted_tracks(self, play_duration_tracker, test_track, test_station):
        """Teste le nettoyage des pistes interrompues."""
        # Démarrer le suivi
        play_duration_tracker.start_tracking(test_station.id, test_track.id, "test_fingerprint")

        # Créer la détection
        detection = play_duration_tracker.create_detection(
            station_id=test_station.id,
            track_id=test_track.id,
            confidence=0.9,
            fingerprint="test_fingerprint",
            detection_method="test",
        )

        # Arrêter le suivi avec silence
        play_duration_tracker.stop_tracking(test_station.id, test_track.id, is_silence=True)

        # Vérifier que la piste est dans les pistes interrompues
        assert len(play_duration_tracker.interrupted_tracks) == 1

        # Nettoyer les pistes interrompues avec un âge maximum très court
        play_duration_tracker.cleanup_interrupted_tracks(max_age_seconds=0.01)

        # Attendre un peu pour que le nettoyage ait lieu
        time.sleep(0.02)

        # Nettoyer à nouveau
        play_duration_tracker.cleanup_interrupted_tracks(max_age_seconds=0.01)

        # Vérifier que la piste a été nettoyée
        assert len(play_duration_tracker.interrupted_tracks) == 0 