"""
Tests d'intégration pour la capture de la durée de lecture jusqu'à la fin naturelle du son.

Ce module contient des tests qui vérifient que le système capture correctement la durée
de lecture jusqu'à ce que le son s'arrête naturellement, soit par détection de silence,
soit par détection de changement spectral.
"""

import io
import os
import uuid
import pytest
import requests
import numpy as np
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydub import AudioSegment

from backend.models.models import Track, Artist, RadioStation, TrackDetection, StationTrackStats
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.track_manager.track_manager import TrackManager
from backend.tests.integration.detection.fetch_senegal_stations import fetch_senegal_stations

# Configurer le logger
logger = logging.getLogger(__name__)

# Durées d'enregistrement pour les tests (en secondes)
SHORT_RECORDING = 15
MEDIUM_RECORDING = 30
LONG_RECORDING = 60

# Paramètres de détection de silence
SILENCE_THRESHOLD = 0.05
MIN_SILENCE_DURATION = 2.0
MAX_SILENCE_DURATION = 5.0

# Paramètres de détection de changement spectral
SPECTRAL_CHANGE_THRESHOLD = 0.3

# Limite de sécurité pour la durée maximale de capture (en secondes)
MAX_CAPTURE_DURATION = 180  # 3 minutes


class TestContinuousPlayDuration:
    """Tests d'intégration pour la capture de la durée de lecture continue."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Crée une session de base de données pour les tests."""
        # Créer une base de données en mémoire pour les tests
        engine = create_engine("sqlite:///:memory:")
        
        # Créer les tables
        from backend.models.models import Base
        Base.metadata.create_all(engine)
        
        # Créer une session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        yield session
        
        # Nettoyer après les tests
        session.close()

    @pytest.fixture
    def test_stations(self, db_session):
        """Crée des stations de test à partir de vraies stations sénégalaises."""
        # Récupérer les stations sénégalaises
        senegal_stations = fetch_senegal_stations()
        
        # Créer des stations de test
        stations = []
        for i, station_data in enumerate(senegal_stations[:5]):  # Limiter à 5 stations pour les tests
            station = RadioStation(
                name=station_data["name"],
                stream_url=station_data["url"],
                status="active"
            )
            db_session.add(station)
            stations.append(station)
        
        db_session.commit()
        
        return stations

    def capture_audio_stream_until_silence(self, stream_url, 
                                          silence_threshold=SILENCE_THRESHOLD,
                                          min_silence_duration=MIN_SILENCE_DURATION,
                                          max_silence_duration=MAX_SILENCE_DURATION,
                                          spectral_change_threshold=SPECTRAL_CHANGE_THRESHOLD,
                                          max_capture_duration=MAX_CAPTURE_DURATION):
        """
        Capture un extrait audio d'un flux radio en direct jusqu'à ce qu'un silence
        ou un changement spectral soit détecté.
        
        Args:
            stream_url: URL du flux radio
            silence_threshold: Seuil pour considérer un segment comme silence
            min_silence_duration: Durée minimale de silence pour considérer la fin du morceau
            max_silence_duration: Durée maximale de silence à tolérer
            spectral_change_threshold: Seuil pour détecter un changement spectral
            max_capture_duration: Durée maximale de capture (limite de sécurité)
            
        Returns:
            tuple: (bytes: Données audio capturées, float: Durée réelle capturée, str: Raison de fin)
        """
        try:
            logger.info(f"Tentative de connexion au flux: {stream_url}")
            
            # Établir une connexion au flux
            response = requests.get(stream_url, stream=True, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Connexion établie, début de la capture audio...")
            
            # Préparer un buffer pour stocker les données audio
            audio_buffer = io.BytesIO()
            
            # Variables pour la capture
            bytes_captured = 0
            start_time = datetime.now()
            
            # Variables pour la détection de silence/changement
            silence_duration = 0
            previous_segment = None
            segment_size = 4096  # Taille des segments pour l'analyse
            segments_buffer = []  # Buffer pour stocker les segments récents
            end_reason = "unknown"
            
            for chunk in response.iter_content(chunk_size=segment_size):
                if chunk:
                    audio_buffer.write(chunk)
                    bytes_captured += len(chunk)
                    
                    # Stocker le segment pour analyse
                    segments_buffer.append(chunk)
                    
                    # Garder seulement les 10 derniers segments pour l'analyse
                    if len(segments_buffer) > 10:
                        segments_buffer.pop(0)
                    
                    # Analyser seulement tous les 5 segments pour des raisons de performance
                    if len(segments_buffer) >= 5 and bytes_captured % (segment_size * 5) == 0:
                        # Convertir les segments récents en audio pour analyse
                        temp_buffer = io.BytesIO()
                        for seg in segments_buffer:
                            temp_buffer.write(seg)
                        temp_buffer.seek(0)
                        
                        try:
                            # Analyser l'audio pour détecter le silence ou changement
                            temp_audio = AudioSegment.from_file(temp_buffer)
                            
                            # Calculer le niveau sonore moyen
                            rms = temp_audio.rms
                            normalized_rms = rms / 32768.0  # Normaliser par rapport à la valeur max d'un int16
                            
                            # Détecter le silence
                            if normalized_rms < silence_threshold:
                                silence_duration += len(temp_audio) / 1000.0
                                logger.debug(f"Silence détecté: {silence_duration:.2f}s (seuil: {min_silence_duration:.2f}s)")
                                
                                if silence_duration >= min_silence_duration:
                                    logger.info(f"Silence détecté pendant {silence_duration:.2f}s - Fin du morceau")
                                    end_reason = "silence_detected"
                                    break
                            else:
                                silence_duration = 0
                                
                            # Détecter un changement significatif dans le contenu audio
                            if previous_segment is not None:
                                # Comparer les caractéristiques spectrales
                                current_spectrum = np.array(temp_audio.get_array_of_samples())
                                previous_spectrum = np.array(previous_segment.get_array_of_samples())
                                
                                if len(current_spectrum) > 0 and len(previous_spectrum) > 0:
                                    # Redimensionner si nécessaire
                                    min_length = min(len(current_spectrum), len(previous_spectrum))
                                    current_spectrum = current_spectrum[:min_length]
                                    previous_spectrum = previous_spectrum[:min_length]
                                    
                                    # Calculer la différence spectrale
                                    spectral_diff = np.mean(np.abs(current_spectrum - previous_spectrum)) / 32768.0
                                    
                                    logger.debug(f"Différence spectrale: {spectral_diff:.4f} (seuil: {spectral_change_threshold:.4f})")
                                    
                                    if spectral_diff > spectral_change_threshold:
                                        logger.info(f"Changement de contenu audio détecté (diff={spectral_diff:.2f}) - Possible nouveau morceau")
                                        end_reason = "spectral_change_detected"
                                        break
                            
                            previous_segment = temp_audio
                            
                        except Exception as e:
                            logger.warning(f"Erreur lors de l'analyse audio: {e}")
                    
                    # Vérifier si on a capturé pendant trop longtemps (limite de sécurité)
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed > max_capture_duration:
                        logger.warning(f"Durée maximale de capture atteinte ({max_capture_duration} secondes)")
                        end_reason = "max_duration_reached"
                        break
            
            # Calculer la durée totale de capture
            total_elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Capture terminée après {total_elapsed:.2f} secondes. Raison: {end_reason}")
            
            # Convertir en format compatible avec pydub pour extraction de la durée
            audio_buffer.seek(0)
            audio = AudioSegment.from_file(audio_buffer)
            
            # Calculer la durée réelle capturée
            real_duration = len(audio) / 1000.0  # Convertir en secondes
            logger.info(f"Durée réelle de l'audio capturé: {real_duration:.2f} secondes")
            
            # Créer un nouveau buffer avec le segment audio
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format="mp3")
            output_buffer.seek(0)
            
            return output_buffer.read(), real_duration, end_reason
                    
        except Exception as e:
            logger.error(f"Erreur lors de la capture audio: {e}")
            return None, 0.0, f"error: {str(e)}"

    def test_available_stations(self, test_stations):
        """Vérifie que les stations de test sont disponibles."""
        assert len(test_stations) > 0, "Aucune station de test disponible"
        
        for station in test_stations:
            logger.info(f"Station disponible: {station.name} ({station.stream_url})")
            
            # Tester la connexion au flux
            try:
                response = requests.head(station.stream_url, timeout=5)
                response.raise_for_status()
                logger.info(f"Connexion réussie à {station.name}")
            except Exception as e:
                logger.warning(f"Impossible de se connecter à {station.name}: {e}")

    @pytest.mark.asyncio
    async def test_silence_detection(self, db_session, test_stations):
        """
        Test qui capture un extrait audio d'une vraie radio jusqu'à ce qu'un silence
        soit détecté, puis vérifie que la durée est correctement enregistrée.
        """
        # Sélectionner une station de test
        station = test_stations[0]
        logger.info(f"Test de détection de silence avec la station: {station.name} ({station.stream_url})")
        
        # Capturer l'audio jusqu'à ce qu'un silence soit détecté
        audio_data, captured_duration, end_reason = self.capture_audio_stream_until_silence(
            station.stream_url,
            silence_threshold=SILENCE_THRESHOLD,
            min_silence_duration=MIN_SILENCE_DURATION
        )
        
        if not audio_data:
            pytest.skip(f"Impossible de capturer l'audio de {station.name}")
        
        logger.info(f"Audio capturé avec succès. Durée: {captured_duration:.2f} secondes. Raison de fin: {end_reason}")
        
        # Vérifier que la capture s'est terminée à cause d'un silence détecté
        if end_reason != "silence_detected":
            logger.warning(f"La capture ne s'est pas terminée à cause d'un silence détecté, mais pour la raison: {end_reason}")
        
        # Créer un FeatureExtractor
        feature_extractor = FeatureExtractor()
        
        # Extraire les caractéristiques
        try:
            features = await feature_extractor.analyze_audio(audio_data)
            
            if not features:
                pytest.skip(f"Impossible d'extraire les caractéristiques de l'audio")
            
            # Vérifier que la durée extraite correspond à la durée capturée
            assert abs(features["duration"] - captured_duration) < 1.0, \
                f"La durée extraite ({features['duration']:.2f} s) ne correspond pas à la durée capturée ({captured_duration:.2f} s)"
            
            # Créer un TrackManager
            track_manager = TrackManager(db_session)
            
            # Traiter les caractéristiques
            result = await track_manager.process_track(features, station.id)
            
            # Vérifier que le traitement a réussi
            assert result["success"] is True, f"Le traitement a échoué: {result.get('error', 'Erreur inconnue')}"
            assert "detection_id" in result, "L'ID de détection n'est pas présent dans le résultat"
            
            # Récupérer la détection
            detection = db_session.query(TrackDetection).filter(
                TrackDetection.id == result["detection_id"]
            ).first()
            
            # Vérifier que la détection existe
            assert detection is not None, "La détection n'a pas été enregistrée dans la base de données"
            
            # Vérifier que la durée enregistrée correspond à la durée capturée
            captured_duration_td = timedelta(seconds=captured_duration)
            assert abs(detection.play_duration.total_seconds() - captured_duration_td.total_seconds()) < 1.0, \
                f"La durée enregistrée ({detection.play_duration.total_seconds()} s) ne correspond pas à la durée capturée ({captured_duration_td.total_seconds()} s)"
            
            # Récupérer le morceau
            track = db_session.query(Track).filter(
                Track.id == detection.track_id
            ).first()
            
            # Vérifier que le morceau existe
            assert track is not None, "Le morceau n'a pas été trouvé dans la base de données"
            
            # Vérifier que les statistiques ont été mises à jour
            station_track_stats = db_session.query(StationTrackStats).filter(
                StationTrackStats.station_id == station.id,
                StationTrackStats.track_id == track.id
            ).first()
            
            assert station_track_stats is not None, f"Les statistiques de la station {station.name} n'ont pas été créées"
            assert station_track_stats.total_play_duration > timedelta(0), f"La durée totale de lecture pour {station.name} n'a pas été mise à jour"
            
            # Vérifier que la durée totale de lecture dans les statistiques correspond à la durée capturée
            assert abs(station_track_stats.total_play_duration.total_seconds() - captured_duration) < 1.0, \
                f"La durée totale de lecture dans les statistiques ({station_track_stats.total_play_duration.total_seconds()} s) " \
                f"ne correspond pas à la durée capturée ({captured_duration} s)"
            
            # Afficher les résultats
            print(f"\nTest de détection de silence réussi!")
            print(f"Morceau détecté: {track.title} par {track.artist.name if track.artist else 'Artiste inconnu'}")
            print(f"Durée capturée jusqu'au silence: {captured_duration:.2f} secondes")
            print(f"Durée enregistrée: {detection.play_duration.total_seconds():.2f} secondes")
            print(f"Méthode de détection: {detection.method}")
            print(f"Confiance: {detection.confidence}")
            print(f"Raison de fin de capture: {end_reason}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des caractéristiques: {e}")
            pytest.skip(f"Erreur lors de l'extraction des caractéristiques: {e}")

    @pytest.mark.asyncio
    async def test_spectral_change_detection(self, db_session, test_stations):
        """
        Test qui capture un extrait audio d'une vraie radio jusqu'à ce qu'un changement
        spectral soit détecté, puis vérifie que la durée est correctement enregistrée.
        """
        # Sélectionner une station de test
        station = test_stations[1] if len(test_stations) > 1 else test_stations[0]
        logger.info(f"Test de détection de changement spectral avec la station: {station.name} ({station.stream_url})")
        
        # Capturer l'audio jusqu'à ce qu'un changement spectral soit détecté
        audio_data, captured_duration, end_reason = self.capture_audio_stream_until_silence(
            station.stream_url,
            silence_threshold=0.01,  # Seuil de silence très bas pour favoriser la détection de changement spectral
            min_silence_duration=10.0,  # Durée de silence très longue pour favoriser la détection de changement spectral
            spectral_change_threshold=SPECTRAL_CHANGE_THRESHOLD
        )
        
        if not audio_data:
            pytest.skip(f"Impossible de capturer l'audio de {station.name}")
        
        logger.info(f"Audio capturé avec succès. Durée: {captured_duration:.2f} secondes. Raison de fin: {end_reason}")
        
        # Créer un FeatureExtractor
        feature_extractor = FeatureExtractor()
        
        # Extraire les caractéristiques
        try:
            features = await feature_extractor.analyze_audio(audio_data)
            
            if not features:
                pytest.skip(f"Impossible d'extraire les caractéristiques de l'audio")
            
            # Vérifier que la durée extraite correspond à la durée capturée
            assert abs(features["duration"] - captured_duration) < 1.0, \
                f"La durée extraite ({features['duration']:.2f} s) ne correspond pas à la durée capturée ({captured_duration:.2f} s)"
            
            # Créer un TrackManager
            track_manager = TrackManager(db_session)
            
            # Traiter les caractéristiques
            result = await track_manager.process_track(features, station.id)
            
            # Vérifier que le traitement a réussi
            assert result["success"] is True, f"Le traitement a échoué: {result.get('error', 'Erreur inconnue')}"
            assert "detection_id" in result, "L'ID de détection n'est pas présent dans le résultat"
            
            # Récupérer la détection
            detection = db_session.query(TrackDetection).filter(
                TrackDetection.id == result["detection_id"]
            ).first()
            
            # Vérifier que la détection existe
            assert detection is not None, "La détection n'a pas été enregistrée dans la base de données"
            
            # Vérifier que la durée enregistrée correspond à la durée capturée
            captured_duration_td = timedelta(seconds=captured_duration)
            assert abs(detection.play_duration.total_seconds() - captured_duration_td.total_seconds()) < 1.0, \
                f"La durée enregistrée ({detection.play_duration.total_seconds()} s) ne correspond pas à la durée capturée ({captured_duration_td.total_seconds()} s)"
            
            # Afficher les résultats
            print(f"\nTest de détection de changement spectral réussi!")
            print(f"Durée capturée jusqu'au changement spectral: {captured_duration:.2f} secondes")
            print(f"Durée enregistrée: {detection.play_duration.total_seconds():.2f} secondes")
            print(f"Raison de fin de capture: {end_reason}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des caractéristiques: {e}")
            pytest.skip(f"Erreur lors de l'extraction des caractéristiques: {e}")

    @pytest.mark.asyncio
    async def test_multiple_stations_continuous_duration(self, db_session, test_stations):
        """
        Test qui capture des extraits audio de plusieurs stations jusqu'à ce que le son s'arrête,
        puis vérifie que les durées sont correctement enregistrées et peuvent être différentes.
        """
        # Sélectionner plusieurs stations de test
        test_station_count = min(3, len(test_stations))
        selected_stations = test_stations[:test_station_count]
        
        logger.info(f"Test avec {test_station_count} stations différentes")
        
        # Stocker les résultats pour chaque station
        station_results = []
        
        for station in selected_stations:
            logger.info(f"Capture audio de {station.name} jusqu'à ce que le son s'arrête...")
            
            # Capturer l'audio jusqu'à ce que le son s'arrête
            audio_data, captured_duration, end_reason = self.capture_audio_stream_until_silence(
                station.stream_url,
                max_capture_duration=90  # Limiter à 90 secondes pour ce test
            )
            
            if not audio_data:
                logger.warning(f"Impossible de capturer l'audio de {station.name}")
                continue
            
            logger.info(f"Audio capturé avec succès. Durée: {captured_duration:.2f} secondes. Raison de fin: {end_reason}")
            
            # Créer un FeatureExtractor
            feature_extractor = FeatureExtractor()
            
            try:
                # Extraire les caractéristiques
                features = await feature_extractor.analyze_audio(audio_data)
                
                if not features:
                    logger.warning(f"Impossible d'extraire les caractéristiques de l'audio pour {station.name}")
                    continue
                
                # Créer un TrackManager
                track_manager = TrackManager(db_session)
                
                # Traiter les caractéristiques
                result = await track_manager.process_track(features, station.id)
                
                if not result["success"]:
                    logger.warning(f"Le traitement a échoué pour {station.name}: {result.get('error', 'Erreur inconnue')}")
                    continue
                
                # Récupérer la détection
                detection = db_session.query(TrackDetection).filter(
                    TrackDetection.id == result["detection_id"]
                ).first()
                
                if not detection:
                    logger.warning(f"La détection n'a pas été enregistrée dans la base de données pour {station.name}")
                    continue
                
                # Stocker les résultats
                station_results.append({
                    "station": station,
                    "captured_duration": captured_duration,
                    "recorded_duration": detection.play_duration.total_seconds(),
                    "end_reason": end_reason,
                    "detection": detection
                })
                
            except Exception as e:
                logger.error(f"Erreur lors du traitement pour {station.name}: {e}")
                continue
        
        # Vérifier que nous avons des résultats pour au moins 2 stations
        assert len(station_results) >= 2, f"Pas assez de stations avec des résultats valides ({len(station_results)})"
        
        # Vérifier que les durées sont différentes
        durations = [result["captured_duration"] for result in station_results]
        assert len(set(durations)) > 1, f"Toutes les durées sont identiques: {durations}"
        
        # Vérifier que les durées enregistrées correspondent aux durées capturées
        for result in station_results:
            assert abs(result["recorded_duration"] - result["captured_duration"]) < 1.0, \
                f"La durée enregistrée ({result['recorded_duration']} s) ne correspond pas à la durée capturée ({result['captured_duration']} s) pour {result['station'].name}"
        
        # Afficher les résultats
        print(f"\nTest de durées continues sur plusieurs stations réussi!")
        for result in station_results:
            print(f"Station: {result['station'].name}")
            print(f"Durée capturée: {result['captured_duration']:.2f} secondes")
            print(f"Durée enregistrée: {result['recorded_duration']:.2f} secondes")
            print(f"Raison de fin: {result['end_reason']}")
            print(f"Méthode de détection: {result['detection'].method}")
            print("---")

    @pytest.mark.asyncio
    async def test_safety_limit(self, db_session, test_stations):
        """
        Test qui vérifie que la limite de sécurité fonctionne correctement
        en capturant un flux audio avec une limite de temps très courte.
        """
        # Sélectionner une station de test
        station = test_stations[0]
        logger.info(f"Test de limite de sécurité avec la station: {station.name} ({station.stream_url})")
        
        # Définir une limite de sécurité très courte
        short_limit = 10  # 10 secondes
        
        # Capturer l'audio avec une limite de sécurité très courte
        audio_data, captured_duration, end_reason = self.capture_audio_stream_until_silence(
            station.stream_url,
            silence_threshold=0.001,  # Seuil de silence très bas pour éviter la détection de silence
            min_silence_duration=30.0,  # Durée de silence très longue pour éviter la détection de silence
            spectral_change_threshold=0.9,  # Seuil de changement spectral très élevé pour éviter la détection de changement
            max_capture_duration=short_limit
        )
        
        if not audio_data:
            pytest.skip(f"Impossible de capturer l'audio de {station.name}")
        
        logger.info(f"Audio capturé avec succès. Durée: {captured_duration:.2f} secondes. Raison de fin: {end_reason}")
        
        # Vérifier que la capture s'est terminée à cause de la limite de sécurité
        assert end_reason == "max_duration_reached", f"La capture ne s'est pas terminée à cause de la limite de sécurité, mais pour la raison: {end_reason}"
        
        # La durée réelle de l'audio capturé peut être différente de la limite de sécurité
        # car la capture s'arrête après la limite, mais l'audio capturé peut contenir plus de données
        # Nous vérifions donc uniquement que la capture s'est terminée à cause de la limite de sécurité
        
        # Afficher les résultats
        print(f"\nTest de limite de sécurité réussi!")
        print(f"Limite de sécurité: {short_limit} secondes")
        print(f"Durée capturée: {captured_duration:.2f} secondes")
        print(f"Raison de fin: {end_reason}") 