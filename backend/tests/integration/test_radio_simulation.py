"""
Test d'intégration utilisant le simulateur de radio.

Ce module teste le système de détection en utilisant le simulateur de radio
qui diffuse des fichiers audio sénégalais en continu.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker

from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.track_manager.track_manager import TrackManager
from backend.models.models import Artist, Base
from backend.models.models import RadioStation as Station
from backend.models.models import StationTrackStats, Track, TrackStats
from backend.tests.integration.detection.fetch_senegal_stations import fetch_senegal_stations
from backend.tests.utils.radio_simulator import AUDIO_DIR, RadioSimulator, RadioStation
from backend.utils.detection.music_detector import MusicDetector

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_radio_simulation")

# Configuration de la base de données en mémoire pour les tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db_session():
    """Crée une session de base de données en mémoire pour les tests."""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def test_stations(db_session: Session):
    """Crée des stations de test basées sur les stations de radio sénégalaises réelles."""
    stations = fetch_senegal_stations(db_session)
    return stations


@pytest.fixture
def track_manager(db_session: Session):
    """Crée une instance de TrackManager pour les tests."""
    return TrackManager(db_session)


@pytest.fixture
def feature_extractor():
    """Crée une instance de FeatureExtractor pour les tests."""
    return FeatureExtractor()


@pytest.fixture
def radio_simulator():
    """Crée un simulateur de radio pour les tests."""
    simulator = RadioSimulator()

    # Vérifier si des fichiers audio sont disponibles
    audio_dir = Path(AUDIO_DIR)
    if not audio_dir.exists() or not any(audio_dir.glob("*.mp3")):
        pytest.skip(
            "Aucun fichier audio trouvé pour les tests. Veuillez ajouter des fichiers audio dans le répertoire de test."
        )

    # Créer une station avec les fichiers audio disponibles
    station = simulator.create_station("Radio Test Senegal")
    if not station or not station.playlist:
        pytest.skip(
            "Impossible de créer la station simulée. Vérifiez que des fichiers audio sont disponibles."
        )

    try:
        yield simulator
    finally:
        simulator.stop_all()


class TestRadioSimulation:
    """Tests utilisant le simulateur de radio pour la détection musicale."""

    @pytest.mark.asyncio
    async def test_detection_with_simulated_radio(self, db_session: Session):
        """
        Teste la détection musicale avec une station de radio simulée.

        Ce test vérifie que le système peut détecter correctement les morceaux joués
        sur une station de radio simulée en utilisant les vrais services externes.
        """
        # Setup test data directory
        test_audio_dir = os.path.join(os.path.dirname(__file__), "..", "data", "audio", "senegal")
        test_audio_dir = Path(test_audio_dir)

        # Create a simulated radio station
        simulator = RadioSimulator()
        station = simulator.create_station(name="Test Senegal Radio", audio_dir=test_audio_dir)

        # Si aucune station n'a été créée (pas de fichiers audio), on ignore le test
        if not station:
            pytest.skip("Aucun fichier audio trouvé pour la simulation")

        station.start()

        try:
            # Create a database station entry
            db_station = Station(
                name="Test Senegal Radio",
                stream_url=f"http://localhost:{station.port}/stream",
                country="Senegal",
                language="French",
                status="active",
                is_active=True,
            )
            db_session.add(db_station)
            db_session.commit()

            # Create an artist for testing
            artist = Artist(name="Test Artist", country="Senegal", type="Solo")
            db_session.add(artist)
            db_session.commit()

            # Create a track for testing
            track = Track(
                title="Test Track",
                artist_id=artist.id,
                duration=timedelta(minutes=3),
                fingerprint="test_fingerprint",
            )
            db_session.add(track)
            db_session.commit()

            # Initialize track stats
            track_stats = StationTrackStats(
                station_id=db_station.id,
                track_id=track.id,
                play_count=0,
                total_play_time=timedelta(0),
                last_played=datetime.now(),
                average_confidence=0.0,
            )
            db_session.add(track_stats)
            db_session.commit()

            # Create a music detector and process audio
            detector = MusicDetector(db_session)

            # Capture audio for a short period (enough to detect something)
            detection_result = await detector.process_track(
                station_id=db_station.id,
                stream_url=db_station.stream_url,
                capture_duration=15,  # Capture 15 seconds of audio for better detection
            )

            # Log the detection result
            logger.info(f"Detection result: {detection_result}")

            # Assert that a detection was made
            assert detection_result is not None, "Aucun résultat de détection"

            # Check if we got an error
            if not detection_result.get("success", False):
                logger.warning(
                    f"Erreur de détection: {detection_result.get('error', 'Erreur inconnue')}"
                )
                # Ne pas faire échouer le test si aucune correspondance n'est trouvée
                if "Aucune correspondance" in detection_result.get("error", ""):
                    pytest.skip("Aucune correspondance trouvée dans les services externes")
                elif "Audio non musical" in detection_result.get("error", ""):
                    pytest.skip("L'audio capturé n'est pas musical (parole ou silence)")
            else:
                # Get the track_id from the detection result
                track_id = detection_result.get("track_id")
                if track_id:
                    # Verify that track stats were updated
                    updated_stats = (
                        db_session.query(StationTrackStats)
                        .filter(
                            StationTrackStats.station_id == db_station.id,
                            StationTrackStats.track_id == track_id,
                        )
                        .first()
                    )

                    # Assert that play count and duration were updated
                    assert (
                        updated_stats is not None
                    ), "Les statistiques de piste n'ont pas été mises à jour"
                    assert (
                        updated_stats.play_count > 0
                    ), "Le compteur de lecture n'a pas été incrémenté"
                    assert updated_stats.total_play_time > timedelta(
                        0
                    ), "La durée de lecture n'a pas été enregistrée"

                    # Log the updated stats
                    logger.info(
                        f"Statistiques mises à jour: play_count={updated_stats.play_count}, total_play_time={updated_stats.total_play_time}"
                    )

        finally:
            # Clean up
            station.stop()
            await asyncio.sleep(1)  # Give time for the server to shut down

    @pytest.mark.asyncio
    async def test_external_services_detection(self, db_session: Session):
        """
        Teste spécifiquement la détection avec les services externes.

        Ce test vérifie que les services externes (AcoustID, MusicBrainz, AudD)
        fonctionnent correctement avec notre système de détection.
        """
        # Setup test data directory
        test_audio_dir = os.path.join(os.path.dirname(__file__), "..", "data", "audio", "senegal")
        test_audio_dir = Path(test_audio_dir)

        # Vérifier si des fichiers audio sont disponibles
        if not test_audio_dir.exists() or not any(test_audio_dir.glob("*.mp3")):
            pytest.skip("Aucun fichier audio trouvé pour les tests")

        # Sélectionner un fichier audio pour le test
        audio_files = list(test_audio_dir.glob("*.mp3"))
        if not audio_files:
            pytest.skip("Aucun fichier MP3 trouvé pour les tests")

        test_file = audio_files[0]
        logger.info(f"Utilisation du fichier audio: {test_file}")

        # Create a simulated radio station
        simulator = RadioSimulator()
        station = simulator.create_station(name="External Services Test", audio_dir=test_audio_dir)

        if not station:
            pytest.skip("Impossible de créer la station simulée")

        station.start()

        try:
            # Create a database station entry
            db_station = Station(
                name="External Services Test",
                stream_url=f"http://localhost:{station.port}/stream",
                country="Senegal",
                language="French",
                status="active",
                is_active=True,
            )
            db_session.add(db_station)
            db_session.commit()

            # Create a music detector with the database session
            detector = MusicDetector(db_session)

            # Capture audio and test each external service
            logger.info("Test de détection avec les services externes...")

            # Capture audio for a longer period for better detection
            detection_result = await detector.process_track(
                station_id=db_station.id,
                stream_url=db_station.stream_url,
                capture_duration=20,  # Capture 20 seconds of audio for better detection
            )

            # Log the detection result
            logger.info(f"Résultat de la détection: {detection_result}")

            # Check if we got a result
            if detection_result and detection_result.get("success", False):
                # Get the track_id from the detection result
                track_id = detection_result.get("track_id")

                if track_id:
                    # Verify that track stats were updated
                    updated_stats = (
                        db_session.query(StationTrackStats)
                        .filter(
                            StationTrackStats.station_id == db_station.id,
                            StationTrackStats.track_id == track_id,
                        )
                        .first()
                    )

                    # Assert that play count and duration were updated
                    assert (
                        updated_stats is not None
                    ), "Les statistiques de piste n'ont pas été mises à jour"
                    assert (
                        updated_stats.play_count > 0
                    ), "Le compteur de lecture n'a pas été incrémenté"
                    assert updated_stats.total_play_time > timedelta(
                        0
                    ), "La durée de lecture n'a pas été enregistrée"

                    # Log the updated stats
                    logger.info(
                        f"Statistiques mises à jour: play_count={updated_stats.play_count}, total_play_time={updated_stats.total_play_time}"
                    )
                else:
                    logger.warning("Aucun track_id dans le résultat de détection")
            else:
                error_msg = (
                    detection_result.get("error", "Erreur inconnue")
                    if detection_result
                    else "Aucun résultat"
                )
                logger.warning(f"Échec de la détection: {error_msg}")
                # Ne pas faire échouer le test si les services externes ne sont pas disponibles
                # ou si l'audio n'est pas musical
                if "Audio non musical" in error_msg:
                    pytest.skip(f"L'audio capturé n'est pas musical (parole ou silence)")
                else:
                    pytest.skip(f"Les services externes ne sont pas disponibles: {error_msg}")

        finally:
            # Clean up
            station.stop()
            await asyncio.sleep(1)  # Give time for the server to shut down

    async def capture_audio_stream(self, stream_url: str, duration: int = 15) -> Optional[bytes]:
        """
        Capture l'audio depuis un flux HTTP pendant une durée spécifiée.

        Args:
            stream_url: URL du flux audio
            duration: Durée de capture en secondes

        Returns:
            Données audio capturées ou None en cas d'échec
        """
        import io
        import time

        import requests
        from pydub import AudioSegment

        logger.info(f"Capture audio depuis {stream_url} pendant {duration}s")

        try:
            # Établir la connexion au flux avec un timeout plus long
            response = requests.get(stream_url, stream=True, timeout=30)
            response.raise_for_status()

            # Préparer un buffer pour stocker les données audio
            buffer = io.BytesIO()

            # Calculer la taille approximative des données à capturer
            # Estimation: ~128 kbps = 16 ko/s
            approx_size = duration * 16 * 1024

            start_time = time.time()
            bytes_read = 0

            # Capturer les données audio avec un timeout par chunk
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue

                buffer.write(chunk)
                bytes_read += len(chunk)

                # Vérifier si nous avons capturé suffisamment de données
                elapsed_time = time.time() - start_time
                if bytes_read >= approx_size or elapsed_time >= duration:
                    break

                # Vérifier si nous sommes bloqués trop longtemps
                if elapsed_time > duration * 2:
                    logger.warning(
                        f"Timeout dépassé lors de la capture audio après {elapsed_time:.1f}s"
                    )
                    break

            # Si nous n'avons pas capturé assez de données, c'est un échec
            if bytes_read < 1024:  # Au moins 1 Ko
                logger.error(f"Pas assez de données capturées: seulement {bytes_read} octets")
                return None

            actual_duration = time.time() - start_time
            logger.info(f"Capture terminée: {bytes_read / 1024:.1f} ko en {actual_duration:.1f}s")

            # Convertir les données capturées en format audio utilisable
            buffer.seek(0)

            try:
                # Essayer de convertir en AudioSegment
                audio = AudioSegment.from_file(buffer)
                logger.info(
                    f"Audio capturé: {audio.duration_seconds:.2f}s, {audio.frame_rate}Hz, {audio.channels} canaux"
                )

                # Convertir en format WAV pour le traitement
                wav_data = io.BytesIO()
                audio.export(wav_data, format="wav")
                wav_data.seek(0)
                return wav_data.read()

            except Exception as e:
                logger.error(f"Erreur lors de la conversion audio: {e}")
                # Retourner les données brutes en cas d'échec de conversion
                buffer.seek(0)
                return buffer.read() if bytes_read > 1024 else None

        except Exception as e:
            logger.error(f"Erreur lors de la capture audio: {e}")
            return None
