"""Module d'extraction des caractéristiques audio."""

import logging
import numpy as np
import librosa
import soundfile as sf
from typing import Dict, Any, Optional
import io
from ...utils.logging_config import setup_logging

logger = setup_logging(__name__)

class FeatureExtractor:
    """Extracteur de caractéristiques audio."""
    
    def __init__(self):
        """Initialise l'extracteur de caractéristiques."""
        self.logger = logging.getLogger(__name__)
        self.sample_rate = 22050
        self.hop_length = 512
        self.n_mels = 128
        self.n_mfcc = 20
    
    async def analyze_audio(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Analyse un segment audio et extrait ses caractéristiques."""
        try:
            # Charge l'audio en mémoire
            samples, _ = sf.read(io.BytesIO(audio_data))
            if len(samples.shape) > 1:
                samples = np.mean(samples, axis=1)
            
            # Normalise les échantillons
            samples = librosa.util.normalize(samples)
            
            # Extrait les caractéristiques
            features = self._extract_features(samples)
            
            # Analyse le rythme
            rhythm_strength = self._detect_rhythm_strength(samples, self.sample_rate)
            features["rhythm_strength"] = rhythm_strength
            
            # Calcule la confiance globale
            features["confidence"] = self._calculate_confidence(features)
            
            return features
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse audio: {str(e)}")
            return None
    
    def _extract_features(self, samples: np.ndarray) -> Dict[str, Any]:
        """Extrait les caractéristiques audio d'un signal."""
        features = {}
        
        try:
            # Spectrogramme mel
            mel_spec = librosa.feature.melspectrogram(
                y=samples,
                sr=self.sample_rate,
                n_mels=self.n_mels,
                hop_length=self.hop_length
            )
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
            features["mel_mean"] = np.mean(mel_spec_db)
            features["mel_std"] = np.std(mel_spec_db)
            
            # MFCC
            mfcc = librosa.feature.mfcc(
                y=samples,
                sr=self.sample_rate,
                n_mfcc=self.n_mfcc,
                hop_length=self.hop_length
            )
            features["mfcc_mean"] = np.mean(mfcc, axis=1).tolist()
            features["mfcc_std"] = np.std(mfcc, axis=1).tolist()
            
            # Chromagramme
            chroma = librosa.feature.chroma_stft(
                y=samples,
                sr=self.sample_rate,
                hop_length=self.hop_length
            )
            features["chroma_mean"] = np.mean(chroma, axis=1).tolist()
            
            # Énergie spectrale
            spectral_centroids = librosa.feature.spectral_centroid(
                y=samples,
                sr=self.sample_rate,
                hop_length=self.hop_length
            )
            features["spectral_centroid_mean"] = float(np.mean(spectral_centroids))
            
            # Détection de tempo
            tempo, _ = librosa.beat.beat_track(
                y=samples,
                sr=self.sample_rate,
                hop_length=self.hop_length
            )
            features["tempo"] = float(tempo)
            
            # Analyse des bandes de fréquence
            frequencies = self._analyze_frequency_bands(samples)
            features.update(frequencies)
            
            return features
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction des caractéristiques: {str(e)}")
            return {}
    
    def _detect_rhythm_strength(self, samples: np.ndarray, sample_rate: int) -> float:
        """Détecte la force du rythme dans un signal audio."""
        try:
            # Calcule l'enveloppe du signal
            onset_env = librosa.onset.onset_strength(
                y=samples,
                sr=sample_rate,
                hop_length=self.hop_length
            )
            
            # Détecte les pics dans l'enveloppe
            peaks = librosa.util.peak_pick(
                onset_env,
                pre_max=3,
                post_max=3,
                pre_avg=3,
                post_avg=5,
                delta=0.5,
                wait=10
            )
            
            # Calcule la force moyenne des pics
            if len(peaks) > 0:
                peak_heights = onset_env[peaks]
                rhythm_strength = float(np.mean(peak_heights))
            else:
                rhythm_strength = 0.0
            
            return min(1.0, rhythm_strength / 10.0)  # Normalise entre 0 et 1
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la détection du rythme: {str(e)}")
            return 0.0
    
    def _analyze_frequency_bands(self, samples: np.ndarray) -> Dict[str, float]:
        """Analyse les différentes bandes de fréquence."""
        try:
            # Calcule le spectrogramme
            D = librosa.stft(samples)
            frequencies = librosa.fft_frequencies(sr=self.sample_rate)
            
            # Définit les bandes de fréquence
            bands = {
                "sub_bass": (20, 60),
                "bass": (60, 250),
                "low_mids": (250, 500),
                "mids": (500, 2000),
                "high_mids": (2000, 4000),
                "highs": (4000, 20000)
            }
            
            results = {}
            magnitudes = np.abs(D)
            
            # Calcule l'énergie pour chaque bande
            for band_name, (low, high) in bands.items():
                mask = (frequencies >= low) & (frequencies <= high)
                band_energy = np.mean(magnitudes[mask])
                results[f"{band_name}_energy"] = float(band_energy)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse des fréquences: {str(e)}")
            return {}
    
    def _calculate_confidence(self, features: Dict[str, Any]) -> float:
        """Calcule le score de confiance global basé sur les caractéristiques."""
        try:
            # Poids pour chaque caractéristique
            weights = {
                "rhythm_strength": 0.3,
                "bass_energy": 0.2,
                "mids_energy": 0.2,
                "spectral_centroid_mean": 0.15,
                "mel_std": 0.15
            }
            
            # Normalise et combine les caractéristiques
            score = 0.0
            for feature, weight in weights.items():
                if feature in features:
                    value = features[feature]
                    if isinstance(value, (int, float)):
                        score += weight * min(1.0, max(0.0, value))
            
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de la confiance: {str(e)}")
            return 0.0 