"""Module de génération et comparaison d'empreintes digitales audio."""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import librosa
import numpy as np
import soundfile as sf

from backend.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AudioFingerprinter:
    """Audio fingerprinting class."""

    def __init__(self, sample_rate: int = 22050, n_mels: int = 128):
        """Initialize the fingerprinter."""
        self.sample_rate = sample_rate
        self.n_mels = n_mels
        self.hop_length = 512
        self.n_fft = 2048

    def generate_fingerprint(self, audio_data: np.ndarray) -> bytes:
        """Generate a fingerprint from audio data."""
        try:
            # Extract features
            features = self.extract_features(audio_data)

            # Convert features to bytes
            feature_bytes = json.dumps(features).encode()

            # Generate hash
            return hashlib.sha256(feature_bytes).digest()

        except Exception as e:
            logger.error(f"Error generating fingerprint: {str(e)}")
            return None

    def extract_features(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Extract audio features."""
        try:
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)

            # Compute mel spectrogram
            mel_spec = librosa.feature.melspectrogram(
                y=audio_data,
                sr=self.sample_rate,
                n_mels=self.n_mels,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
            )

            # Compute MFCC
            mfcc = librosa.feature.mfcc(S=librosa.power_to_db(mel_spec), n_mfcc=20)

            # Compute spectral contrast
            contrast = librosa.feature.spectral_contrast(
                y=audio_data, sr=self.sample_rate, n_fft=self.n_fft, hop_length=self.hop_length
            )

            # Compute chroma features
            chroma = librosa.feature.chroma_stft(
                y=audio_data, sr=self.sample_rate, n_fft=self.n_fft, hop_length=self.hop_length
            )

            return {
                "mel_spectrogram": mel_spec.tolist(),
                "mfcc": mfcc.tolist(),
                "spectral_contrast": contrast.tolist(),
                "chroma": chroma.tolist(),
            }

        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            return None

    def compare_fingerprints(self, fp1: bytes, fp2: bytes) -> float:
        """Compare two fingerprints and return similarity score."""
        try:
            if not fp1 or not fp2:
                return 0.0

            # Compare byte sequences
            matches = sum(a == b for a, b in zip(fp1, fp2))
            return matches / len(fp1)

        except Exception as e:
            logger.error(f"Error comparing fingerprints: {str(e)}")
            return 0.0

    def get_audio_duration(self, audio_data: np.ndarray) -> float:
        """Get duration of audio in seconds."""
        try:
            if len(audio_data.shape) > 1:
                return len(audio_data) / self.sample_rate
            return len(audio_data) / self.sample_rate
        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            return 0.0


def generate_fingerprint(audio_data: np.ndarray) -> bytes:
    """Generate fingerprint from audio data."""
    fingerprinter = AudioFingerprinter()
    return fingerprinter.generate_fingerprint(audio_data)


def compare_fingerprints(fp1: bytes, fp2: bytes) -> float:
    """Comparer deux empreintes digitales et retourner un score de similarité."""
    try:
        # Convertir les empreintes en tableaux numpy
        features1 = np.frombuffer(fp1, dtype=np.float32)
        features2 = np.frombuffer(fp2, dtype=np.float32)

        # Calculer la distance euclidienne
        distance = np.linalg.norm(features1 - features2)

        # Convertir la distance en score de similarité (0 à 1)
        similarity = 1 / (1 + distance)

        return float(similarity)

    except Exception as e:
        logger.error(f"Erreur lors de la comparaison des empreintes: {str(e)}")
        return 0.0


def extract_audio_features(audio_data: bytes) -> Optional[Dict]:
    """Extraire les caractéristiques audio pour l'analyse."""
    try:
        # Convertir les données audio en tableau numpy
        audio_array = np.frombuffer(audio_data, dtype=np.float32)

        # Normaliser l'audio
        audio_array = audio_array / np.max(np.abs(audio_array))

        # Extraire les caractéristiques
        features = {
            "mfcc": librosa.feature.mfcc(y=audio_array, sr=settings.SAMPLE_RATE, n_mfcc=13)
            .mean(axis=1)
            .tolist(),
            "spectral_centroid": float(
                librosa.feature.spectral_centroid(y=audio_array, sr=settings.SAMPLE_RATE).mean()
            ),
            "spectral_bandwidth": float(
                librosa.feature.spectral_bandwidth(y=audio_array, sr=settings.SAMPLE_RATE).mean()
            ),
            "spectral_rolloff": float(
                librosa.feature.spectral_rolloff(y=audio_array, sr=settings.SAMPLE_RATE).mean()
            ),
            "zero_crossing_rate": float(librosa.feature.zero_crossing_rate(audio_array).mean()),
            "tempo": float(librosa.beat.tempo(y=audio_array, sr=settings.SAMPLE_RATE)[0]),
        }

        return features

    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des caractéristiques: {str(e)}")
        return None


def is_music(audio_data: bytes, threshold: float = 0.6) -> bool:
    """Déterminer si l'audio contient de la musique."""
    try:
        features = extract_audio_features(audio_data)
        if not features:
            return False

        # Critères pour la détection de musique
        has_rhythm = features["tempo"] > settings.MIN_RHYTHM_STRENGTH
        has_spectral_variety = features["spectral_bandwidth"] > settings.MIN_BASS_ENERGY
        has_zero_crossings = features["zero_crossing_rate"] > settings.MIN_MID_ENERGY

        # Calculer un score global
        score = (int(has_rhythm) + int(has_spectral_variety) + int(has_zero_crossings)) / 3

        return score >= threshold

    except Exception as e:
        logger.error(f"Erreur lors de la détection de musique: {str(e)}")
        return False
