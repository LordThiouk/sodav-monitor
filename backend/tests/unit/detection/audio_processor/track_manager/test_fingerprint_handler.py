"""
Tests unitaires pour la classe FingerprintHandler.

Ce module contient les tests unitaires pour la classe FingerprintHandler qui est responsable
de la génération et de la gestion des empreintes digitales audio.
"""

import io
import os
import tempfile
from unittest.mock import MagicMock, patch

import librosa
import numpy as np
import pytest

from backend.config import get_settings
from backend.detection.audio_processor.track_manager.fingerprint_handler import FingerprintHandler


# Fixtures pour les tests
@pytest.fixture
def config():
    """Crée une configuration simulée pour les tests."""
    mock_config = MagicMock()
    mock_config.FINGERPRINT_ALGORITHM = "chromaprint"
    mock_config.FINGERPRINT_SAMPLE_RATE = 22050
    mock_config.FINGERPRINT_FRAME_SIZE = 4096
    mock_config.FINGERPRINT_HOP_SIZE = 2048
    return mock_config


@pytest.fixture
def fingerprint_handler(config):
    """Crée une instance de FingerprintHandler pour les tests."""
    with patch(
        "backend.detection.audio_processor.track_manager.fingerprint_handler.get_settings",
        return_value=config,
    ):
        return FingerprintHandler()


@pytest.fixture
def mock_audio_data():
    """Crée des données audio simulées pour les tests."""
    # Créer un signal audio synthétique (sinus à 440 Hz)
    sample_rate = 22050
    duration = 3.0  # secondes
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio_data = 0.5 * np.sin(2 * np.pi * 440 * t)
    return audio_data, sample_rate


@pytest.fixture
def mock_audio_file():
    """Crée un fichier audio temporaire pour les tests."""
    # Créer un fichier temporaire
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file.close()

    # Créer un signal audio synthétique et l'enregistrer dans le fichier
    sample_rate = 22050
    duration = 3.0  # secondes
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio_data = 0.5 * np.sin(2 * np.pi * 440 * t)

    # Enregistrer l'audio dans le fichier temporaire
    librosa.output.write_wav(temp_file.name, audio_data, sample_rate)

    yield temp_file.name

    # Nettoyer après les tests
    os.unlink(temp_file.name)


# Tests pour la méthode generate_fingerprint
def test_generate_fingerprint_from_array(fingerprint_handler, mock_audio_data):
    """Teste la génération d'une empreinte digitale à partir d'un tableau audio."""
    # Extraire les données du mock
    audio_data, sample_rate = mock_audio_data

    # Patch la méthode _compute_chromaprint pour simuler une empreinte
    with patch.object(
        fingerprint_handler, "_compute_chromaprint", return_value="test_fingerprint_123"
    ):
        # Appeler la méthode à tester
        fingerprint = fingerprint_handler.generate_fingerprint(audio_data, sample_rate)

        # Vérifier les résultats
        assert fingerprint == "test_fingerprint_123"

        # Vérifier les appels de méthode
        fingerprint_handler._compute_chromaprint.assert_called_once()


def test_generate_fingerprint_from_file(fingerprint_handler, mock_audio_file):
    """Teste la génération d'une empreinte digitale à partir d'un fichier audio."""
    # Patch la méthode _compute_chromaprint pour simuler une empreinte
    with patch.object(
        fingerprint_handler, "_compute_chromaprint", return_value="test_fingerprint_456"
    ), patch("librosa.load", return_value=(np.array([0.1, 0.2, 0.3]), 22050)):
        # Appeler la méthode à tester
        fingerprint = fingerprint_handler.generate_fingerprint(mock_audio_file)

        # Vérifier les résultats
        assert fingerprint == "test_fingerprint_456"

        # Vérifier les appels de méthode
        fingerprint_handler._compute_chromaprint.assert_called_once()
        librosa.load.assert_called_once()


def test_generate_fingerprint_from_bytes(fingerprint_handler):
    """Teste la génération d'une empreinte digitale à partir de données binaires."""
    # Créer des données audio binaires simulées
    audio_bytes = b"mock_audio_bytes"

    # Patch les méthodes nécessaires
    with patch("io.BytesIO") as mock_bytesio, patch(
        "librosa.load", return_value=(np.array([0.1, 0.2, 0.3]), 22050)
    ), patch.object(
        fingerprint_handler, "_compute_chromaprint", return_value="test_fingerprint_789"
    ):
        # Configurer le mock BytesIO
        mock_bytesio_instance = MagicMock(spec=io.BytesIO)
        mock_bytesio.return_value = mock_bytesio_instance

        # Appeler la méthode à tester
        fingerprint = fingerprint_handler.generate_fingerprint(audio_bytes)

        # Vérifier les résultats
        assert fingerprint == "test_fingerprint_789"

        # Vérifier les appels de méthode
        mock_bytesio.assert_called_once_with(audio_bytes)
        librosa.load.assert_called_once()
        fingerprint_handler._compute_chromaprint.assert_called_once()


def test_generate_fingerprint_invalid_input(fingerprint_handler):
    """Teste la gestion d'une entrée invalide pour la génération d'empreinte."""
    # Entrées invalides
    invalid_inputs = [None, 123, {}, []]

    # Patch le logger
    with patch.object(fingerprint_handler.logger, "error") as mock_logger:
        # Vérifier chaque entrée invalide
        for invalid_input in invalid_inputs:
            # Appeler la méthode à tester
            fingerprint = fingerprint_handler.generate_fingerprint(invalid_input)

            # Vérifier les résultats
            assert fingerprint is None

            # Vérifier les appels de méthode
            mock_logger.assert_called()
            mock_logger.reset_mock()


# Tests pour la méthode compare_fingerprints
def test_compare_fingerprints_identical(fingerprint_handler):
    """Teste la comparaison d'empreintes digitales identiques."""
    # Empreintes digitales identiques
    fingerprint1 = "abcdef123456"
    fingerprint2 = "abcdef123456"

    # Appeler la méthode à tester
    similarity = fingerprint_handler.compare_fingerprints(fingerprint1, fingerprint2)

    # Vérifier les résultats
    assert similarity == 1.0


def test_compare_fingerprints_similar(fingerprint_handler):
    """Teste la comparaison d'empreintes digitales similaires."""
    # Empreintes digitales similaires
    fingerprint1 = "abcdef123456"
    fingerprint2 = "abcdef789012"  # 50% similaire

    # Patch la méthode _compute_similarity pour simuler un score
    with patch.object(fingerprint_handler, "_compute_similarity", return_value=0.75):
        # Appeler la méthode à tester
        similarity = fingerprint_handler.compare_fingerprints(fingerprint1, fingerprint2)

        # Vérifier les résultats
        assert similarity == 0.75

        # Vérifier les appels de méthode
        fingerprint_handler._compute_similarity.assert_called_once_with(fingerprint1, fingerprint2)


def test_compare_fingerprints_different(fingerprint_handler):
    """Teste la comparaison d'empreintes digitales différentes."""
    # Empreintes digitales différentes
    fingerprint1 = "abcdef123456"
    fingerprint2 = "ghijkl789012"  # Complètement différent

    # Patch la méthode _compute_similarity pour simuler un score
    with patch.object(fingerprint_handler, "_compute_similarity", return_value=0.1):
        # Appeler la méthode à tester
        similarity = fingerprint_handler.compare_fingerprints(fingerprint1, fingerprint2)

        # Vérifier les résultats
        assert similarity == 0.1

        # Vérifier les appels de méthode
        fingerprint_handler._compute_similarity.assert_called_once_with(fingerprint1, fingerprint2)


def test_compare_fingerprints_invalid(fingerprint_handler):
    """Teste la gestion d'entrées invalides pour la comparaison d'empreintes."""
    # Entrées valides et invalides
    valid_fingerprint = "abcdef123456"
    invalid_inputs = [None, "", 123, {}, []]

    # Patch le logger
    with patch.object(fingerprint_handler.logger, "error") as mock_logger:
        # Vérifier chaque entrée invalide
        for invalid_input in invalid_inputs:
            # Appeler la méthode à tester dans les deux sens
            similarity1 = fingerprint_handler.compare_fingerprints(valid_fingerprint, invalid_input)
            similarity2 = fingerprint_handler.compare_fingerprints(invalid_input, valid_fingerprint)

            # Vérifier les résultats
            assert similarity1 == 0.0
            assert similarity2 == 0.0

            # Vérifier les appels de méthode
            assert mock_logger.call_count == 2
            mock_logger.reset_mock()


# Tests pour les méthodes utilitaires
def test_compute_chromaprint(fingerprint_handler, mock_audio_data):
    """Teste le calcul d'une empreinte Chromaprint."""
    # Extraire les données du mock
    audio_data, sample_rate = mock_audio_data

    # Patch la bibliothèque acoustid.chromaprint
    with patch("acoustid.chromaprint") as mock_chromaprint:
        # Configurer le mock pour simuler une empreinte
        mock_chromaprint.fingerprint.return_value = (1, "test_raw_fingerprint")
        mock_chromaprint.encode_fingerprint.return_value = "test_encoded_fingerprint"

        # Appeler la méthode à tester
        fingerprint = fingerprint_handler._compute_chromaprint(audio_data, sample_rate)

        # Vérifier les résultats
        assert fingerprint == "test_encoded_fingerprint"

        # Vérifier les appels de méthode
        mock_chromaprint.fingerprint.assert_called_once()
        mock_chromaprint.encode_fingerprint.assert_called_once_with("test_raw_fingerprint", 1)


def test_compute_chromaprint_error(fingerprint_handler, mock_audio_data):
    """Teste la gestion des erreurs lors du calcul d'une empreinte Chromaprint."""
    # Extraire les données du mock
    audio_data, sample_rate = mock_audio_data

    # Patch la bibliothèque acoustid.chromaprint pour lever une exception
    with patch("acoustid.chromaprint") as mock_chromaprint, patch.object(
        fingerprint_handler.logger, "error"
    ) as mock_logger:
        # Configurer le mock pour lever une exception
        mock_chromaprint.fingerprint.side_effect = Exception("Test error")

        # Appeler la méthode à tester
        fingerprint = fingerprint_handler._compute_chromaprint(audio_data, sample_rate)

        # Vérifier les résultats
        assert fingerprint is None

        # Vérifier les appels de méthode
        mock_chromaprint.fingerprint.assert_called_once()
        mock_logger.assert_called_once()


def test_compute_similarity(fingerprint_handler):
    """Teste le calcul de similarité entre deux empreintes digitales."""
    # Empreintes digitales de test
    fingerprint1 = "abcdef"
    fingerprint2 = "abcxyz"

    # Patch numpy pour simuler le calcul de similarité
    with patch("numpy.array") as mock_array, patch("numpy.linalg.norm") as mock_norm, patch(
        "numpy.dot", return_value=0.75
    ) as mock_dot:
        # Configurer les mocks
        mock_array.side_effect = lambda x: x  # Retourner l'entrée telle quelle
        mock_norm.return_value = 1.0  # Normalisation à 1.0

        # Appeler la méthode à tester
        similarity = fingerprint_handler._compute_similarity(fingerprint1, fingerprint2)

        # Vérifier les résultats
        assert similarity == 0.75

        # Vérifier les appels de méthode
        assert mock_array.call_count == 2
        assert mock_norm.call_count == 2
        mock_dot.assert_called_once()


def test_compute_similarity_error(fingerprint_handler):
    """Teste la gestion des erreurs lors du calcul de similarité."""
    # Empreintes digitales de test
    fingerprint1 = "abcdef"
    fingerprint2 = "abcxyz"

    # Patch numpy pour lever une exception
    with patch("numpy.array") as mock_array, patch.object(
        fingerprint_handler.logger, "error"
    ) as mock_logger:
        # Configurer le mock pour lever une exception
        mock_array.side_effect = Exception("Test error")

        # Appeler la méthode à tester
        similarity = fingerprint_handler._compute_similarity(fingerprint1, fingerprint2)

        # Vérifier les résultats
        assert similarity == 0.0

        # Vérifier les appels de méthode
        mock_array.assert_called_once()
        mock_logger.assert_called_once()


def test_extract_features(fingerprint_handler, mock_audio_data):
    """Teste l'extraction de caractéristiques audio."""
    # Extraire les données du mock
    audio_data, sample_rate = mock_audio_data

    # Patch librosa pour simuler l'extraction de caractéristiques
    with patch("librosa.feature.chroma_cqt") as mock_chroma, patch(
        "librosa.feature.mfcc"
    ) as mock_mfcc, patch("librosa.feature.spectral_contrast") as mock_contrast:
        # Configurer les mocks
        mock_chroma.return_value = np.random.rand(12, 100)
        mock_mfcc.return_value = np.random.rand(20, 100)
        mock_contrast.return_value = np.random.rand(7, 100)

        # Appeler la méthode à tester
        features = fingerprint_handler._extract_features(audio_data, sample_rate)

        # Vérifier les résultats
        assert isinstance(features, dict)
        assert "chroma" in features
        assert "mfcc" in features
        assert "contrast" in features

        # Vérifier les appels de méthode
        mock_chroma.assert_called_once()
        mock_mfcc.assert_called_once()
        mock_contrast.assert_called_once()


def test_extract_features_error(fingerprint_handler, mock_audio_data):
    """Teste la gestion des erreurs lors de l'extraction de caractéristiques."""
    # Extraire les données du mock
    audio_data, sample_rate = mock_audio_data

    # Patch librosa pour lever une exception
    with patch("librosa.feature.chroma_cqt") as mock_chroma, patch.object(
        fingerprint_handler.logger, "error"
    ) as mock_logger:
        # Configurer le mock pour lever une exception
        mock_chroma.side_effect = Exception("Test error")

        # Appeler la méthode à tester
        features = fingerprint_handler._extract_features(audio_data, sample_rate)

        # Vérifier les résultats
        assert features == {}

        # Vérifier les appels de méthode
        mock_chroma.assert_called_once()
        mock_logger.assert_called_once()


if __name__ == "__main__":
    pytest.main()
