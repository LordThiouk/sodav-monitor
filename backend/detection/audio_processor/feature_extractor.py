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
    
    def extract_features(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Extrait les caractéristiques audio pour l'identification de musique.
        
        Args:
            audio_data: Données audio sous forme de tableau numpy
            
        Returns:
            Dictionnaire de caractéristiques incluant la durée
            
        Raises:
            TypeError: Si audio_data n'est pas un tableau numpy
            ValueError: Si audio_data est vide
        """
        if not isinstance(audio_data, np.ndarray):
            raise TypeError("Audio data must be a numpy array")
        if audio_data.size == 0:
            raise ValueError("Audio data cannot be empty")
        
        # Calculer la durée audio
        play_duration = self.get_audio_duration(audio_data)
        logger.debug(f"Calculated audio duration: {play_duration:.2f} seconds from {len(audio_data)} samples at {self.sample_rate} Hz")
        
        # Convertir en mono si nécessaire
        if len(audio_data.shape) == 2 and audio_data.shape[1] > 1:
            # Convertir stéréo en mono en prenant la moyenne des canaux
            audio_mono = np.mean(audio_data, axis=1)
        else:
            # Déjà en mono ou mono avec dimension explicite
            audio_mono = audio_data.reshape(-1)
        
        # Normaliser l'amplitude
        audio_mono = audio_mono / np.max(np.abs(audio_mono)) if np.max(np.abs(audio_mono)) > 0 else audio_mono
        
        # Extraire les caractéristiques MFCC (Mel-Frequency Cepstral Coefficients)
        try:
            mfccs = librosa.feature.mfcc(
                y=audio_mono, 
                sr=self.sample_rate,
                n_mfcc=13,
                n_fft=self.n_fft,
                hop_length=self.hop_length
            )
            mfcc_mean = np.mean(mfccs, axis=1).tolist()
        except Exception as e:
            logger.error(f"Error extracting MFCCs: {str(e)}")
            mfcc_mean = [0] * 13  # Valeurs par défaut en cas d'erreur
        
        # Extraire les caractéristiques de chroma (représentation des hauteurs musicales)
        try:
            chroma = librosa.feature.chroma_stft(
                y=audio_mono, 
                sr=self.sample_rate,
                n_fft=self.n_fft,
                hop_length=self.hop_length
            )
            chroma_mean = np.mean(chroma, axis=1).tolist()
        except Exception as e:
            logger.error(f"Error extracting chroma features: {str(e)}")
            chroma_mean = [0] * 12  # Valeurs par défaut en cas d'erreur
        
        # Extraire le centroïde spectral (brillance du son)
        try:
            spectral_centroid = librosa.feature.spectral_centroid(
                y=audio_mono, 
                sr=self.sample_rate,
                n_fft=self.n_fft,
                hop_length=self.hop_length
            )
            spectral_centroid_mean = float(np.mean(spectral_centroid))
        except Exception as e:
            logger.error(f"Error extracting spectral centroid: {str(e)}")
            spectral_centroid_mean = 0.0  # Valeur par défaut en cas d'erreur
        
        # Détecter le tempo et la force rythmique
        try:
            onset_env = librosa.onset.onset_strength(
                y=audio_mono, 
                sr=self.sample_rate
            )
            tempo, _ = librosa.beat.beat_track(
                onset_envelope=onset_env, 
                sr=self.sample_rate
            )
            rhythm_strength = float(np.mean(onset_env))
        except Exception as e:
            logger.error(f"Error detecting tempo: {str(e)}")
            tempo = 0.0
            rhythm_strength = 0.0  # Valeurs par défaut en cas d'erreur
        
        # Calculer l'empreinte digitale audio (simulée ici)
        fingerprint = self._calculate_fingerprint(audio_mono)
        
        # Extract mel spectrogram
        try:
            mel_spectrogram = librosa.feature.melspectrogram(
                y=audio_mono,
                sr=self.sample_rate,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                n_mels=self.n_mels
            )
        except Exception as e:
            logger.error(f"Error extracting mel spectrogram: {str(e)}")
            mel_spectrogram = np.zeros((self.n_mels, 10))  # Default value
            
        # Extract spectral contrast
        try:
            spectral_contrast = librosa.feature.spectral_contrast(
                y=audio_mono,
                sr=self.sample_rate,
                n_fft=self.n_fft,
                hop_length=self.hop_length
            )
        except Exception as e:
            logger.error(f"Error extracting spectral contrast: {str(e)}")
            spectral_contrast = np.zeros((7, 10))  # Default value
            
        # Prepare features for is_music method
        music_detection_features = {
            "mel_spectrogram": mel_spectrogram,
            "mfcc": mfccs,
            "spectral_contrast": spectral_contrast,
            "chroma": chroma
        }
        
        # Determine if it's music
        is_music_result, music_confidence = self.is_music(music_detection_features)
        
        # Assembler toutes les caractéristiques
        features = {
            "play_duration": play_duration,
            "mfcc_mean": mfcc_mean,
            "chroma_mean": chroma_mean,
            "spectral_centroid_mean": spectral_centroid_mean,
            "tempo": tempo,
            "rhythm_strength": rhythm_strength,
            "fingerprint": fingerprint,
            "is_music": is_music_result,
            "confidence": music_confidence
        }
        
        logger.debug(f"Extracted features with play_duration: {play_duration:.2f} seconds")
        
        return features
    
    def _calculate_fingerprint(self, audio_data: np.ndarray) -> str:
        """
        Calcule une empreinte digitale audio (simulée).
        
        Args:
            audio_data: Données audio sous forme de tableau numpy
            
        Returns:
            Empreinte digitale sous forme de chaîne de caractères
        """
        # Dans une implémentation réelle, utiliser un algorithme comme Chromaprint
        # Pour l'instant, simuler avec un hachage MD5
        import hashlib
        # Prendre un sous-échantillon pour accélérer le calcul
        subsample = audio_data[::100] if len(audio_data) > 1000 else audio_data
        return hashlib.md5(subsample.tobytes()).hexdigest()
    
    def _calculate_confidence(self, audio_data: np.ndarray) -> float:
        """
        Calcule un score de confiance pour la détection de musique.
        
        Args:
            audio_data: Données audio sous forme de tableau numpy
            
        Returns:
            Score de confiance entre 0 et 1
        """
        # Simuler un calcul de confiance basé sur des caractéristiques audio
        # Dans une implémentation réelle, ce serait basé sur des modèles ML
        
        # Calculer l'énergie du signal
        energy = np.mean(np.abs(audio_data))
        
        # Calculer la variance (complexité du signal)
        variance = np.var(audio_data)
        
        # Calculer un score simple basé sur l'énergie et la variance
        confidence = min(0.95, (energy * 0.5 + variance * 2.0))
        
        return float(confidence)
    
    def is_music(self, features: Dict[str, np.ndarray]) -> Tuple[bool, float]:
        """Determine if the audio segment is music based on extracted features.
        
        Args:
            features: Dictionary containing audio features
            
        Returns:
            Tuple of (is_music, confidence)
            
        Raises:
            ValueError: If features is not a dictionary or missing required keys
            TypeError: If features are not numpy arrays
        """
        try:
            # Input validation
            if not isinstance(features, dict):
                raise ValueError("Features must be a dictionary")
                
            required_features = ["mel_spectrogram", "mfcc", "spectral_contrast", "chroma"]
            if not all(key in features for key in required_features):
                raise ValueError(f"Missing required features: {required_features}")
                
            if not all(isinstance(features[key], np.ndarray) for key in required_features):
                raise TypeError("Features must be numpy arrays")
                
            # Calculate individual feature scores
            rhythm_strength = self._calculate_rhythm_strength(features["mel_spectrogram"])
            harmonic_ratio = self._calculate_harmonic_ratio(features["mel_spectrogram"])
            spectral_flux = self._calculate_spectral_flux(features["mel_spectrogram"])
            chroma_variance = self._calculate_chroma_variance(features["chroma"])
            timbre_stability = self._calculate_timbre_stability(features["mfcc"])
            
            # Log feature scores for debugging
            logger.debug(
                f"Music detection: rhythm={rhythm_strength:.2f}, harmonic={harmonic_ratio:.2f}, "
                f"flux={spectral_flux:.2f}, chroma={chroma_variance:.2f}, timbre={timbre_stability:.2f}"
            )
            
            # Calculate primary and secondary scores
            primary_score = (
                0.5 * rhythm_strength +     # Rhythm is most important
                0.5 * harmonic_ratio        # Harmonic content equally important
            )
            
            secondary_score = (
                0.4 * (1.0 - spectral_flux) +  # Low flux indicates stability
                0.4 * timbre_stability +       # Stable timbre helps
                0.2 * chroma_variance          # Pitch variation helps
            )
            
            # Combine scores with emphasis on primary features
            base_confidence = 0.7 * primary_score + 0.3 * secondary_score
            
            # Apply penalties for weak primary features
            if rhythm_strength < 0.3 and harmonic_ratio < 0.3:
                base_confidence *= 0.5  # Both primary features weak
            elif rhythm_strength < 0.2 or harmonic_ratio < 0.2:
                base_confidence *= 0.7  # One primary feature very weak
                
            # Apply threshold and return result
            is_music = base_confidence >= 0.6
            
            # Return tuple of (is_music, confidence)
            return (is_music, base_confidence)
            
        except Exception as e:
            logger.error(f"Error in music detection: {str(e)}")
            return (False, 0.0)  # Default to not music with zero confidence
        
    def _calculate_rhythm_strength(self, mel_spectrogram: np.ndarray) -> float:
        """Calculate rhythm strength from mel spectrogram."""
        try:
            if mel_spectrogram.shape[0] < 128:
                return 0.0
                
            # Split into frequency bands
            bass = mel_spectrogram[:30]      # 0-300 Hz
            low_mid = mel_spectrogram[30:60]  # 300-600 Hz
            mid = mel_spectrogram[60:90]      # 600-900 Hz
            high = mel_spectrogram[90:]       # >900 Hz
            
            # Calculate onset envelope for each band
            def get_onset_envelope(band):
                # Calculate power spectrogram
                power = np.sum(band**2, axis=0)
                # Normalize
                power = power / (np.max(power) + 1e-6)
                # Calculate onset envelope
                onset_env = np.diff(power, prepend=power[0])
                # Half-wave rectification
                onset_env = np.maximum(onset_env, 0)
                # Normalize
                if np.any(onset_env):
                    onset_env = onset_env / (np.max(onset_env) + 1e-6)
                return onset_env
            
            # Get onset envelopes
            bass_onsets = get_onset_envelope(bass)
            low_mid_onsets = get_onset_envelope(low_mid)
            mid_onsets = get_onset_envelope(mid)
            high_onsets = get_onset_envelope(high)
            
            # Calculate onset statistics for each band
            def get_onset_stats(onsets):
                if len(onsets) < 2:
                    return 0.0, 0.0, 0.0
                    
                # Find peaks with adaptive thresholding
                mean_onset = np.mean(onsets)
                std_onset = np.std(onsets)
                delta = max(0.2, mean_onset + 0.5 * std_onset)  # Increased threshold
                
                peaks = librosa.util.peak_pick(
                    onsets,
                    pre_max=3,
                    post_max=3,
                    pre_avg=3,
                    post_avg=3,
                    delta=delta,
                    wait=3  # Increased wait time
                )
                
                if len(peaks) < 2:
                    return 0.0, 0.0, 0.0
                    
                # Calculate peak statistics
                peak_heights = onsets[peaks]
                intervals = np.diff(peaks)
                
                # Calculate regularity (inverse of coefficient of variation)
                regularity = 1.0 - np.std(intervals) / (np.mean(intervals) + 1e-6)
                # Calculate density (peaks per frame)
                density = len(peaks) / len(onsets)
                # Calculate strength (mean peak height)
                strength = np.mean(peak_heights)
                
                return regularity, density, strength
            
            # Get stats for each band
            bass_stats = get_onset_stats(bass_onsets)
            low_mid_stats = get_onset_stats(low_mid_onsets)
            mid_stats = get_onset_stats(mid_onsets)
            high_stats = get_onset_stats(high_onsets)
            
            # Calculate band scores
            def get_band_score(stats, weight):
                regularity, density, strength = stats
                
                # Penalize irregular rhythms more severely
                if regularity < 0.4:  # Increased threshold
                    return 0.0
                    
                # More strict density requirements
                if density < 0.1 or density > 0.4:  # Narrower range
                    return 0.0
                    
                # Calculate score with emphasis on regularity
                score = (
                    0.5 * regularity +  # More weight on regularity
                    0.3 * (1.0 - abs(0.25 - density) * 4) +  # Optimal density around 0.25
                    0.2 * strength  # Less weight on strength
                )
                
                return score * weight
            
            # Calculate weighted scores with more weight on bass
            bass_score = get_band_score(bass_stats, 0.5)  # More weight on bass
            low_mid_score = get_band_score(low_mid_stats, 0.3)
            mid_score = get_band_score(mid_stats, 0.1)
            high_score = get_band_score(high_stats, 0.1)
            
            # Combine scores
            total_score = bass_score + low_mid_score + mid_score + high_score
            
            # Calculate tempo-based score
            def estimate_tempo(onsets):
                if len(onsets) < 2:
                    return 0.0
                    
                # Calculate autocorrelation
                corr = np.correlate(onsets, onsets, mode='full')
                corr = corr[len(corr)//2:]
                
                # Find peaks in autocorrelation
                peaks = librosa.util.peak_pick(
                    corr,
                    pre_max=3,
                    post_max=3,
                    pre_avg=3,
                    post_avg=3,
                    delta=0.2,  # Increased threshold
                    wait=3  # Increased wait time
                )
                
                if len(peaks) < 2:
                    return 0.0
                    
                # Calculate tempo from peak intervals
                intervals = np.diff(peaks)
                tempo = 60.0 * self.sample_rate / (np.mean(intervals) * self.hop_length)
                
                # Score based on reasonable tempo range (60-180 BPM)
                tempo_score = np.exp(-0.5 * ((tempo - 120) / 40)**2)  # Narrower range
                
                return tempo_score
            
            # Calculate tempo score from bass onsets (most reliable for tempo)
            tempo_score = estimate_tempo(bass_onsets)
            
            # Combine with tempo score
            final_score = 0.7 * total_score + 0.3 * tempo_score
            
            # Calculate entropy for onset patterns
            def get_entropy(onsets):
                hist, _ = np.histogram(onsets, bins=20, density=True)
                entropy = -np.sum(hist * np.log2(hist + 1e-10))
                return entropy / np.log2(len(hist))
            
            # Calculate entropy for each band
            bass_entropy = get_entropy(bass_onsets)
            low_mid_entropy = get_entropy(low_mid_onsets)
            mid_entropy = get_entropy(mid_onsets)
            high_entropy = get_entropy(high_onsets)
            
            # Calculate weighted entropy (more weight on bass)
            avg_entropy = (
                0.5 * bass_entropy +
                0.3 * low_mid_entropy +
                0.1 * mid_entropy +
                0.1 * high_entropy
            )
            
            # Apply stronger entropy penalty
            if avg_entropy > 0.8:
                final_score *= 0.2  # Stronger penalty
            elif avg_entropy > 0.6:
                final_score *= 0.4  # Stronger penalty
            
            # Additional penalties for noise-like characteristics
            if np.mean([s[1] for s in [bass_stats, low_mid_stats, mid_stats, high_stats]]) > 0.5:
                final_score *= 0.3  # Penalize very dense onsets
                
            if np.mean([s[0] for s in [bass_stats, low_mid_stats, mid_stats, high_stats]]) < 0.3:
                final_score *= 0.3  # Penalize very irregular onsets
            
            return float(np.clip(final_score, 0, 1))
            
        except Exception as e:
            logger.error(f"Error in rhythm strength calculation: {str(e)}")
            return 0.0
        
    def _calculate_harmonic_ratio(self, mel_spectrogram: np.ndarray) -> float:
        """Calculate harmonic ratio from mel spectrogram."""
        try:
            if mel_spectrogram.shape[0] < 128:
                return 0.0
                
            # Split into frequency bands
            bass = mel_spectrogram[:30]      # 0-300 Hz
            low_mid = mel_spectrogram[30:60]  # 300-600 Hz
            mid = mel_spectrogram[60:90]      # 600-900 Hz
            high = mel_spectrogram[90:]       # >900 Hz
            
            # Calculate band statistics
            def get_band_stats(band):
                # Normalize band
                band_norm = librosa.util.normalize(band, axis=1)
                
                # Calculate spectral peaks
                peaks = []
                peak_heights = []
                for freq_bin in range(band_norm.shape[0]):
                    bin_peaks = librosa.util.peak_pick(
                        band_norm[freq_bin],
                        pre_max=3,
                        post_max=3,
                        pre_avg=3,
                        post_avg=3,
                        delta=0.2,
                        wait=2
                    )
                    if len(bin_peaks) > 0:
                        peaks.append(bin_peaks)
                        peak_heights.append(band_norm[freq_bin, bin_peaks])
                
                if not peaks:
                    return 0.0, 0.0, 0.0
                    
                # Calculate peak statistics
                avg_peaks = np.mean([len(p) for p in peaks])
                avg_height = np.mean([np.mean(h) for h in peak_heights])
                
                # Calculate peak regularity
                peak_distances = []
                for p in peaks:
                    if len(p) >= 2:
                        distances = np.diff(p)
                        peak_distances.extend(distances)
                        
                if peak_distances:
                    regularity = 1.0 - np.std(peak_distances) / (np.mean(peak_distances) + 1e-6)
                else:
                    regularity = 0.0
                
                return regularity, avg_peaks / band_norm.shape[1], avg_height
            
            # Get stats for each band
            bass_stats = get_band_stats(bass)
            low_mid_stats = get_band_stats(low_mid)
            mid_stats = get_band_stats(mid)
            high_stats = get_band_stats(high)
            
            # Calculate band scores
            def get_band_score(stats, weight):
                regularity, density, height = stats
                
                # Penalize irregular peaks
                if regularity < 0.2:
                    return 0.0
                    
                # Penalize too sparse or too dense peaks
                if density < 0.05 or density > 0.5:
                    return 0.0
                    
                # Calculate score
                score = (
                    0.4 * regularity +
                    0.3 * (1.0 - abs(0.2 - density) * 4) +  # Optimal density around 0.2
                    0.3 * height
                )
                
                return score * weight
            
            # Calculate weighted scores
            bass_score = get_band_score(bass_stats, 0.4)
            low_mid_score = get_band_score(low_mid_stats, 0.3)
            mid_score = get_band_score(mid_stats, 0.2)
            high_score = get_band_score(high_stats, 0.1)
            
            # Combine scores
            total_score = bass_score + low_mid_score + mid_score + high_score
            
            # Calculate harmonic relationships
            def get_harmonic_score(band1, band2):
                if band1.shape[1] != band2.shape[1]:
                    return 0.0
                    
                # Calculate correlation between bands
                corr = np.zeros((band1.shape[0], band2.shape[0]))
                for i in range(band1.shape[0]):
                    for j in range(band2.shape[0]):
                        c = np.corrcoef(band1[i], band2[j])[0, 1]
                        corr[i, j] = 0.0 if np.isnan(c) else abs(c)
                
                # Find maximum correlation for each frequency
                max_corr = np.max(corr, axis=1)
                return np.mean(max_corr)
            
            # Calculate harmonic relationships between bands
            harmonic_scores = [
                get_harmonic_score(bass, low_mid),
                get_harmonic_score(low_mid, mid),
                get_harmonic_score(mid, high)
            ]
            
            # Calculate harmonic score
            harmonic_score = np.mean(harmonic_scores)
            
            # Combine with total score
            final_score = 0.7 * total_score + 0.3 * harmonic_score
            
            # Calculate spectral entropy
            def get_entropy(band):
                # Calculate power spectrum
                power = np.mean(band**2, axis=1)
                # Normalize
                power = power / (np.sum(power) + 1e-6)
                # Calculate entropy
                entropy = -np.sum(power * np.log2(power + 1e-10))
                return entropy / np.log2(len(power))
            
            # Calculate entropy for each band
            entropies = [
                get_entropy(bass),
                get_entropy(low_mid),
                get_entropy(mid),
                get_entropy(high)
            ]
            
            # Apply entropy penalty
            avg_entropy = np.mean(entropies)
            if avg_entropy > 0.9:
                final_score *= 0.3
            elif avg_entropy > 0.7:
                final_score *= 0.6
            
            return float(np.clip(final_score, 0, 1))
            
        except Exception as e:
            logger.error(f"Error in harmonic ratio calculation: {str(e)}")
            return 0.0
        
    def _calculate_spectral_flux(self, mel_spectrogram: np.ndarray) -> float:
        """Calculate spectral flux from mel spectrogram."""
        # Normalize mel spectrogram
        mel_norm = librosa.util.normalize(mel_spectrogram, axis=0)
        
        # Calculate frame-to-frame difference
        diff = np.diff(mel_norm, axis=1)
        
        # Calculate mean absolute change
        flux = np.mean(np.abs(diff))
        
        # Scale flux to be between 0 and 1
        flux = np.clip(flux * 5.0, 0, 1)  # Multiply by 5 to amplify differences
        
        return float(flux)
        
    def get_audio_duration(self, audio_data: np.ndarray) -> float:
        """
        Calcule la durée de l'audio en secondes.
        
        Args:
            audio_data: Données audio sous forme de tableau numpy
            
        Returns:
            Durée en secondes
            
        Raises:
            TypeError: Si audio_data n'est pas un tableau numpy
            ValueError: Si audio_data est vide
        """
        if not isinstance(audio_data, np.ndarray):
            raise TypeError("Audio data must be a numpy array")
        if audio_data.size == 0:
            raise ValueError("Audio data cannot be empty")
            
        # Obtenir le nombre d'échantillons (gérer mono et stéréo)
        if len(audio_data.shape) == 1:
            # Mono
            n_samples = audio_data.shape[0]
        elif len(audio_data.shape) == 2:
            # Stéréo ou mono avec dimension explicite
            n_samples = audio_data.shape[0]
        else:
            raise ValueError(f"Unexpected audio data shape: {audio_data.shape}")
            
        # Calculer la durée en secondes
        duration = float(n_samples / self.sample_rate)
        
        # Journaliser la durée calculée
        logger.debug(f"Calculated audio duration: {duration:.2f} seconds from {n_samples} samples at {self.sample_rate} Hz")
        
        return duration
    
    def _calculate_chroma_variance(self, chroma: np.ndarray) -> float:
        """Calculate variance in chroma features to detect pitch content."""
        try:
            if chroma.shape[0] != 12:
                return 0.0
                
            # Calculate variance across time for each pitch class
            pitch_variances = np.var(chroma, axis=1)
            
            # Calculate mean variance across pitch classes
            mean_variance = np.mean(pitch_variances)
            
            # Normalize to [0, 1]
            normalized_variance = np.clip(mean_variance * 2, 0, 1)
            
            return float(normalized_variance)
            
        except Exception as e:
            logger.error(f"Error in chroma variance calculation: {str(e)}")
            return 0.0
            
    def _calculate_timbre_stability(self, mfcc: np.ndarray) -> float:
        """Calculate timbre stability from MFCC features."""
        try:
            if mfcc.shape[0] < 2:
                return 0.0
                
            # Skip first coefficient (energy)
            mfcc_delta = np.diff(mfcc[1:], axis=1)
            
            # Calculate mean absolute change
            mean_change = np.mean(np.abs(mfcc_delta))
            
            # Convert to stability score (inverse of change)
            stability = np.exp(-2.0 * mean_change)
            
            return float(np.clip(stability, 0, 1))
            
        except Exception as e:
            logger.error(f"Error in timbre stability calculation: {str(e)}")
            return 0.0