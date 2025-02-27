"""Audio feature extraction and analysis functionality."""

import logging
import numpy as np
import librosa
import soundfile as sf
from typing import Dict, Any, Optional, Tuple
import io
from datetime import datetime
from backend.utils.logging_config import setup_logging

logger = setup_logging(__name__)

class FeatureExtractor:
    """Handles audio feature extraction and music detection."""
    
    def __init__(self, 
                 sample_rate: int = 22050,
                 n_mels: int = 128,
                 n_fft: int = 2048,
                 hop_length: int = 512):
        """Initialize the feature extractor.
        
        Args:
            sample_rate: Audio sampling rate in Hz
            n_mels: Number of Mel bands
            n_fft: Length of the FFT window
            hop_length: Number of samples between successive frames
            
        Raises:
            ValueError: If any parameter is invalid
        """
        if sample_rate <= 0:
            raise ValueError("Sample rate must be greater than 0")
        if n_mels <= 0:
            raise ValueError("Number of Mel bands must be greater than 0")
        if n_fft <= 0:
            raise ValueError("FFT window length must be greater than 0")
        if hop_length <= 0:
            raise ValueError("Hop length must be greater than 0")
            
        self.sample_rate = sample_rate
        self.n_mels = n_mels
        self.n_fft = n_fft
        self.hop_length = hop_length
        
        logger.info(
            f"FeatureExtractor initialized: sample_rate={sample_rate}, "
            f"n_mels={n_mels}, n_fft={n_fft}, hop_length={hop_length}"
        )
        
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
            features = self.extract_features(samples)
            
            # Analyse le rythme
            rhythm_strength = self._calculate_rhythm_strength(features["mel_spectrogram"])
            features["rhythm_strength"] = rhythm_strength
            
            # Calcule la confiance globale
            features["confidence"] = self._calculate_confidence(features)
            
            return features
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse audio: {str(e)}")
            return None
    
    def extract_features(self, audio_data: np.ndarray) -> Dict[str, np.ndarray]:
        """Extract audio features from the input data.
        
        Args:
            audio_data: Audio signal as numpy array
            
        Returns:
            Dictionary containing extracted features:
                - mel_spectrogram: Mel-scaled spectrogram
                - mfcc: Mel-frequency cepstral coefficients
                - spectral_contrast: Spectral contrast
                - chroma: Chromagram
                
        Raises:
            ValueError: If audio_data is empty
            TypeError: If audio_data is not a numpy array
        """
        if not isinstance(audio_data, np.ndarray):
            raise TypeError("Audio data must be a numpy array")
        if audio_data.size == 0:
            raise ValueError("Audio data cannot be empty")
            
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
            
        # Calculate expected number of frames
        n_frames = 1 + (len(audio_data) - self.n_fft) // self.hop_length
            
        # Extract features
        mel_spec = librosa.feature.melspectrogram(
            y=audio_data,
            sr=self.sample_rate,
            n_mels=self.n_mels,
            n_fft=self.n_fft,
            hop_length=self.hop_length
        )
        
        # Convert to dB scale and normalize
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        mel_spec_norm = (mel_spec_db - np.min(mel_spec_db)) / (np.max(mel_spec_db) - np.min(mel_spec_db) + 1e-6)
        
        # Ensure all features have the same number of frames
        mel_spec_norm = mel_spec_norm[:, :n_frames]
        
        mfcc = librosa.feature.mfcc(
            S=mel_spec_db[:, :n_frames],
            n_mfcc=20
        )
        
        contrast = librosa.feature.spectral_contrast(
            y=audio_data,
            sr=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length
        )[:, :n_frames]
        
        chroma = librosa.feature.chroma_stft(
            y=audio_data,
            sr=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length
        )[:, :n_frames]
        
        logger.debug(
            f"Features extracted: mel_spec={mel_spec.shape}, mfcc={mfcc.shape}, "
            f"contrast={contrast.shape}, chroma={chroma.shape}"
        )
        
        return {
            "mel_spectrogram": mel_spec_norm,
            "mfcc": mfcc,
            "spectral_contrast": contrast,
            "chroma": chroma
        }
        
    def is_music(self, features: Dict[str, np.ndarray]) -> Tuple[bool, float]:
        """Determine if the audio segment contains music.
        
        Args:
            features: Dictionary of extracted features
            
        Returns:
            Tuple containing:
                - bool: True if music is detected
                - float: Confidence score between 0 and 1
                
        Raises:
            ValueError: If features dictionary is missing required keys
            TypeError: If features are not numpy arrays
        """
        required_features = ["mel_spectrogram", "mfcc", "spectral_contrast", "chroma"]
        for feature in required_features:
            if feature not in features:
                raise ValueError(f"Missing required feature: {feature}")
            if not isinstance(features[feature], np.ndarray):
                raise TypeError(f"Feature {feature} must be a numpy array")
                
        # Calculate music detection metrics
        rhythm_strength = self._calculate_rhythm_strength(features["mel_spectrogram"])
        harmonic_ratio = self._calculate_harmonic_ratio(features["spectral_contrast"])
        spectral_flux = self._calculate_spectral_flux(features["mel_spectrogram"])
        
        # Combine metrics with weights
        weights = {
            "rhythm": 0.4,
            "harmonic": 0.4,
            "flux": 0.2
        }
        
        confidence = float(
            weights["rhythm"] * rhythm_strength +
            weights["harmonic"] * harmonic_ratio +
            weights["flux"] * spectral_flux
        )
        
        # Music detection decision
        music_threshold = 0.6
        is_music = bool(confidence > music_threshold)
        
        logger.debug(
            f"Music detection: rhythm={rhythm_strength:.2f}, harmonic={harmonic_ratio:.2f}, "
            f"flux={spectral_flux:.2f}, confidence={confidence:.2f}"
        )
        
        return is_music, confidence
        
    def _calculate_rhythm_strength(self, mel_spec: np.ndarray) -> float:
        """Calculate rhythm strength from mel spectrogram."""
        # Calculate onset strength
        onset_env = librosa.onset.onset_strength(S=mel_spec)
        
        if len(onset_env) < 2:
            return 0.0
            
        # Calculate tempo and beat frames
        tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=self.sample_rate)
        
        if len(beat_frames) < 2:
            return 0.0
            
        # Calculate beat regularity
        beat_intervals = np.diff(beat_frames)
        if len(beat_intervals) > 0:
            regularity = 1.0 - np.std(beat_intervals) / (np.mean(beat_intervals) + 1e-6)
        else:
            regularity = 0.0
            
        # Calculate onset strength variation
        onset_mean = np.mean(onset_env)
        if onset_mean > 0:
            onset_variation = np.std(onset_env) / onset_mean
        else:
            onset_variation = 0.0
            
        # Combine metrics
        rhythm_strength = 0.5 * regularity + 0.5 * min(1.0, onset_variation)
        return float(rhythm_strength)
        
    def _calculate_harmonic_ratio(self, contrast: np.ndarray) -> float:
        """Calculate harmonic ratio from spectral contrast."""
        if contrast.size == 0:
            return 0.0
            
        # Calculate mean contrast in different frequency bands
        band_means = np.mean(np.abs(contrast), axis=1)
        
        # Weight the bands (emphasize mid-frequencies where harmonics typically occur)
        weights = np.array([0.1, 0.2, 0.3, 0.2, 0.1, 0.05, 0.05])
        weighted_contrast = np.sum(band_means * weights)
        
        # Normalize to [0, 1]
        max_contrast = np.max(np.abs(contrast))
        if max_contrast > 0:
            return float(min(1.0, weighted_contrast / max_contrast))
        return 0.0
        
    def _calculate_spectral_flux(self, mel_spec: np.ndarray) -> float:
        """Calculate spectral flux from mel spectrogram."""
        if mel_spec.shape[1] < 2:
            return 0.0
            
        # Calculate frame-to-frame spectral difference
        diff = np.diff(mel_spec, axis=1)
        flux = np.mean(np.abs(diff))
        
        # Normalize to [0, 1]
        max_diff = np.max(np.abs(mel_spec))
        if max_diff > 0:
            return float(min(1.0, flux / max_diff))
        return 0.0
        
    def get_audio_duration(self, audio_data: np.ndarray) -> float:
        """Calculate the duration of the audio in seconds."""
        if not isinstance(audio_data, np.ndarray):
            raise TypeError("Audio data must be a numpy array")
        if audio_data.size == 0:
            raise ValueError("Audio data cannot be empty")
            
        # Get number of samples (handle both mono and stereo)
        n_samples = audio_data.shape[0]
        return float(n_samples / self.sample_rate)
    
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
            logger.error(f"Erreur lors du calcul de la confiance: {str(e)}")
            return 0.0 