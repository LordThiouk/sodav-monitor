"""Module de génération et comparaison d'empreintes digitales audio."""

import numpy as np
import soundfile as sf
import librosa
from typing import Optional, Tuple, List, Dict
import logging
from ..core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

def generate_fingerprint(audio_data: bytes) -> Optional[bytes]:
    """Générer une empreinte digitale à partir des données audio."""
    try:
        # Convertir les données audio en tableau numpy
        audio_array = np.frombuffer(audio_data, dtype=np.float32)
        
        # Normaliser l'audio
        audio_array = audio_array / np.max(np.abs(audio_array))
        
        # Extraire les caractéristiques MFCC
        mfcc = librosa.feature.mfcc(
            y=audio_array,
            sr=settings.SAMPLE_RATE,
            n_mfcc=13,
            hop_length=512
        )
        
        # Extraire les caractéristiques spectrales
        spectral_centroids = librosa.feature.spectral_centroid(
            y=audio_array,
            sr=settings.SAMPLE_RATE,
            hop_length=512
        )
        
        # Extraire le rythme
        tempo, _ = librosa.beat.beat_track(
            y=audio_array,
            sr=settings.SAMPLE_RATE
        )
        
        # Combiner les caractéristiques
        features = np.concatenate([
            mfcc.flatten(),
            spectral_centroids.flatten(),
            np.array([tempo])
        ])
        
        # Normaliser les caractéristiques
        features = (features - np.mean(features)) / np.std(features)
        
        return features.tobytes()
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'empreinte: {str(e)}")
        return None

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
            "mfcc": librosa.feature.mfcc(
                y=audio_array,
                sr=settings.SAMPLE_RATE,
                n_mfcc=13
            ).mean(axis=1).tolist(),
            
            "spectral_centroid": float(librosa.feature.spectral_centroid(
                y=audio_array,
                sr=settings.SAMPLE_RATE
            ).mean()),
            
            "spectral_bandwidth": float(librosa.feature.spectral_bandwidth(
                y=audio_array,
                sr=settings.SAMPLE_RATE
            ).mean()),
            
            "spectral_rolloff": float(librosa.feature.spectral_rolloff(
                y=audio_array,
                sr=settings.SAMPLE_RATE
            ).mean()),
            
            "zero_crossing_rate": float(librosa.feature.zero_crossing_rate(
                audio_array
            ).mean()),
            
            "tempo": float(librosa.beat.tempo(
                y=audio_array,
                sr=settings.SAMPLE_RATE
            )[0])
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
        score = (
            int(has_rhythm) +
            int(has_spectral_variety) +
            int(has_zero_crossings)
        ) / 3
        
        return score >= threshold
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection de musique: {str(e)}")
        return False 