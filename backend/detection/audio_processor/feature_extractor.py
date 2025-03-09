"""Audio feature extraction and analysis functionality."""

import logging
import numpy as np
import librosa
import soundfile as sf
from typing import Dict, Any, Optional, Tuple
import io
from datetime import datetime
from backend.utils.logging_config import setup_logging
from backend.logs.log_manager import LogManager

# Initialize logging
log_manager = LogManager()
logger = log_manager.get_logger("detection.audio_processor.feature_extractor")

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
            logger.info(
                f"Music detection: rhythm={rhythm_strength:.2f}, harmonic={harmonic_ratio:.2f}, "
                f"flux={spectral_flux:.2f}, chroma={chroma_variance:.2f}, timbre={timbre_stability:.2f}"
            )
            
            # Ajustement: si l'harmonie est très élevée mais le rythme est faible, 
            # nous augmentons artificiellement le rythme pour compenser
            if harmonic_ratio > 0.8 and rhythm_strength < 0.2:
                adjusted_rhythm = 0.3 + (harmonic_ratio - 0.8) * 0.5
                logger.info(f"Adjusting rhythm strength from {rhythm_strength:.2f} to {adjusted_rhythm:.2f} due to high harmonic ratio")
                rhythm_strength = adjusted_rhythm
            
            # Calculate primary and secondary scores
            primary_score = (
                0.5 * rhythm_strength +     # Rhythm is important
                0.5 * harmonic_ratio        # Harmonic content equally important
            )
            
            secondary_score = (
                0.3 * (1.0 - spectral_flux) +  # Low flux indicates stability
                0.4 * timbre_stability +       # Stable timbre helps
                0.3 * chroma_variance          # Pitch variation helps
            )
            
            # Combine scores with emphasis on primary features
            base_confidence = 0.7 * primary_score + 0.3 * secondary_score
            
            # Apply penalties for weak primary features
            if rhythm_strength < 0.2 and harmonic_ratio < 0.2:  # Reduced thresholds
                base_confidence *= 0.6  # Both primary features weak
                logger.info(f"Applied penalty: both primary features weak (rhythm={rhythm_strength:.2f}, harmonic={harmonic_ratio:.2f})")
            elif rhythm_strength < 0.1 or harmonic_ratio < 0.1:  # Reduced thresholds
                base_confidence *= 0.8  # One primary feature very weak
                logger.info(f"Applied penalty: one primary feature very weak (rhythm={rhythm_strength:.2f}, harmonic={harmonic_ratio:.2f})")
            
            # Ajustement: si l'harmonie est très élevée, nous augmentons le score final
            if harmonic_ratio > 0.8:
                harmonic_bonus = 0.1 + (harmonic_ratio - 0.8) * 0.5
                adjusted_confidence = base_confidence + harmonic_bonus
                logger.info(f"Applied harmonic bonus: {harmonic_bonus:.2f}, adjusting confidence from {base_confidence:.2f} to {adjusted_confidence:.2f}")
                base_confidence = adjusted_confidence
                
            # Apply threshold and return result
            is_music = base_confidence >= 0.4  # Reduced threshold from 0.5 to 0.4
            
            logger.info(f"Final music detection: is_music={is_music}, confidence={base_confidence:.2f}")
            
            # Return tuple of (is_music, confidence)
            return (is_music, base_confidence)
            
        except Exception as e:
            logger.error(f"Error in music detection: {str(e)}")
            return (False, 0.0)  # Default to not music with zero confidence
        
    def _calculate_rhythm_strength(self, mel_spectrogram: np.ndarray) -> float:
        """Calculate rhythm strength from mel spectrogram."""
        try:
            if mel_spectrogram.shape[0] < 128:
                logger.warning(f"Mel spectrogram too small: {mel_spectrogram.shape}")
                return 0.0
                
            # Split into frequency bands
            bass = mel_spectrogram[:30]      # 0-300 Hz
            low_mid = mel_spectrogram[30:60]  # 300-600 Hz
            mid = mel_spectrogram[60:90]      # 600-900 Hz
            high = mel_spectrogram[90:]       # >900 Hz
            
            # Log band shapes for debugging
            logger.debug(f"Band shapes: bass={bass.shape}, low_mid={low_mid.shape}, mid={mid.shape}, high={high.shape}")
            
            # Calculate onset envelope for each band
            def get_onset_envelope(band):
                # Calculate power spectrogram
                power = librosa.power_to_db(band, ref=np.max)
                # Calculate onset envelope
                onset_env = np.diff(power, axis=1)
                onset_env = np.maximum(0, onset_env)  # Keep only positive changes
                return onset_env
                
            try:
                bass_onsets = get_onset_envelope(bass)
                low_mid_onsets = get_onset_envelope(low_mid)
                mid_onsets = get_onset_envelope(mid)
                high_onsets = get_onset_envelope(high)
                
                # Log onset shapes for debugging
                logger.debug(f"Onset shapes: bass={bass_onsets.shape}, low_mid={low_mid_onsets.shape}, mid={mid_onsets.shape}, high={high_onsets.shape}")
                
            except Exception as e:
                logger.error(f"Error calculating onset envelopes: {str(e)}")
                return 0.0
                
            # Calculate statistics for each band
            def get_onset_stats(onsets):
                if onsets.size == 0:
                    return {
                        "mean": 0.0,
                        "std": 0.0,
                        "max": 0.0,
                        "energy": 0.0
                    }
                    
                # Calculate statistics
                mean = np.mean(onsets)
                std = np.std(onsets)
                max_val = np.max(onsets)
                energy = np.sum(onsets ** 2)
                
                return {
                    "mean": float(mean),
                    "std": float(std),
                    "max": float(max_val),
                    "energy": float(energy)
                }
                
            bass_stats = get_onset_stats(bass_onsets)
            low_mid_stats = get_onset_stats(low_mid_onsets)
            mid_stats = get_onset_stats(mid_onsets)
            high_stats = get_onset_stats(high_onsets)
            
            # Log statistics for debugging
            logger.debug(f"Bass stats: {bass_stats}")
            logger.debug(f"Low-mid stats: {low_mid_stats}")
            logger.debug(f"Mid stats: {mid_stats}")
            logger.debug(f"High stats: {high_stats}")
            
            # Calculate band scores
            def get_band_score(stats, weight):
                # Normalize energy
                energy = min(1.0, stats["energy"] / 1000.0)
                # Calculate score based on energy and variability
                score = weight * (0.7 * energy + 0.3 * (stats["std"] / (stats["mean"] + 1e-5)))
                return score
                
            # Weights for each band (bass is most important for rhythm)
            bass_weight = 0.5
            low_mid_weight = 0.3
            mid_weight = 0.15
            high_weight = 0.05
            
            bass_score = get_band_score(bass_stats, bass_weight)
            low_mid_score = get_band_score(low_mid_stats, low_mid_weight)
            mid_score = get_band_score(mid_stats, mid_weight)
            high_score = get_band_score(high_stats, high_weight)
            
            # Log band scores for debugging
            logger.debug(f"Band scores: bass={bass_score:.4f}, low_mid={low_mid_score:.4f}, mid={mid_score:.4f}, high={high_score:.4f}")
            
            # Calculate tempo
            def estimate_tempo(onsets):
                if onsets.size == 0:
                    return 0.0
                    
                # Sum onsets across frequency bands
                onset_sum = np.sum(onsets, axis=0)
                
                # Calculate autocorrelation
                corr = np.correlate(onset_sum, onset_sum, mode='full')
                corr = corr[corr.size//2:]
                
                # Find peaks in autocorrelation
                # Correction de l'appel à peak_pick qui a changé dans la version de librosa
                try:
                    # Utiliser localmax qui est plus stable entre les versions
                    from librosa.util import localmax
                    # Créer un masque pour les maxima locaux
                    peaks_mask = localmax(corr)
                    # Appliquer un seuil
                    threshold = 0.5 * np.max(corr)
                    peaks_mask = peaks_mask & (corr > threshold)
                    # Obtenir les indices des pics
                    peaks = np.where(peaks_mask)[0]
                except Exception as e:
                    logger.error(f"Error in peak detection: {str(e)}")
                    return 0.0
                
                if len(peaks) == 0:
                    return 0.0
                    
                # Calculate tempo from peak intervals
                intervals = np.diff(peaks)
                if intervals.size == 0:
                    return 0.0
                    
                # Convert to BPM
                tempo = 60.0 / (np.median(intervals) * 0.01)  # Assuming 100ms hop size
                return min(300.0, max(40.0, tempo))  # Limit to reasonable range
                
            # Combine onsets for tempo estimation
            combined_onsets = np.vstack([bass_onsets, low_mid_onsets, mid_onsets, high_onsets])
            tempo = estimate_tempo(combined_onsets)
            
            # Calculate entropy (measure of randomness)
            def get_entropy(onsets):
                if onsets.size == 0:
                    return 0.0
                    
                # Flatten and normalize
                flat = onsets.flatten()
                if np.sum(flat) == 0:
                    return 0.0
                    
                # Normalize to probability distribution
                prob = flat / np.sum(flat)
                # Remove zeros
                prob = prob[prob > 0]
                # Calculate entropy
                entropy = -np.sum(prob * np.log2(prob))
                # Normalize to [0, 1]
                max_entropy = np.log2(len(prob))
                if max_entropy == 0:
                    return 0.0
                    
                return entropy / max_entropy
                
            # Calculate entropy for each band
            bass_entropy = get_entropy(bass_onsets)
            low_mid_entropy = get_entropy(low_mid_onsets)
            mid_entropy = get_entropy(mid_onsets)
            high_entropy = get_entropy(high_onsets)
            
            # Average entropy (lower is better for music)
            avg_entropy = (bass_entropy + low_mid_entropy + mid_entropy + high_entropy) / 4.0
            entropy_score = 1.0 - avg_entropy  # Invert so higher is better
            
            # Log entropy scores for debugging
            logger.debug(f"Entropy scores: bass={bass_entropy:.4f}, low_mid={low_mid_entropy:.4f}, mid={mid_entropy:.4f}, high={high_entropy:.4f}, avg={avg_entropy:.4f}")
            
            # Combine scores
            band_score = bass_score + low_mid_score + mid_score + high_score
            
            # Adjust for tempo (bonus for music-like tempo)
            tempo_factor = 1.0
            if 60 <= tempo <= 200:  # Most music is in this range
                tempo_factor = 1.2
                
            # Final rhythm strength score
            rhythm_strength = min(1.0, band_score * tempo_factor * (0.8 + 0.2 * entropy_score))
            
            logger.info(f"Rhythm strength calculation: band_score={band_score:.4f}, tempo={tempo:.1f}, tempo_factor={tempo_factor:.1f}, entropy_score={entropy_score:.4f}, final={rhythm_strength:.4f}")
            
            return rhythm_strength
            
        except Exception as e:
            logger.error(f"Error calculating rhythm strength: {str(e)}")
            return 0.0
        
    def _calculate_harmonic_ratio(self, mel_spectrogram: np.ndarray) -> float:
        """Calculate harmonic ratio from mel spectrogram."""
        try:
            if mel_spectrogram.shape[0] < 128:
                logger.warning(f"Mel spectrogram too small for harmonic ratio: {mel_spectrogram.shape}")
                return 0.0
                
            # Split into frequency bands
            low = mel_spectrogram[:40]       # 0-400 Hz
            mid_low = mel_spectrogram[40:80]  # 400-800 Hz
            mid_high = mel_spectrogram[80:100]  # 800-1000 Hz
            high = mel_spectrogram[100:]      # >1000 Hz
            
            # Log band shapes for debugging
            logger.debug(f"Harmonic band shapes: low={low.shape}, mid_low={mid_low.shape}, mid_high={mid_high.shape}, high={high.shape}")
            
            # Calculate statistics for each band
            def get_band_stats(band):
                # Normalize band
                if np.max(band) > 0:
                    band_norm = band / np.max(band)
                else:
                    band_norm = band
                    
                # Calculate statistics
                mean = np.mean(band_norm)
                std = np.std(band_norm)
                max_val = np.max(band_norm)
                energy = np.sum(band_norm ** 2)
                
                # Calculate spectral flatness (Wiener entropy)
                if np.all(band_norm == 0):
                    flatness = 0.0
                else:
                    # Add small constant to avoid log(0)
                    band_pos = band_norm + 1e-10
                    # Geometric mean / arithmetic mean
                    flatness = np.exp(np.mean(np.log(band_pos))) / np.mean(band_pos)
                    
                return {
                    "mean": float(mean),
                    "std": float(std),
                    "max": float(max_val),
                    "energy": float(energy),
                    "flatness": float(flatness)
                }
                
            low_stats = get_band_stats(low)
            mid_low_stats = get_band_stats(mid_low)
            mid_high_stats = get_band_stats(mid_high)
            high_stats = get_band_stats(high)
            
            # Log statistics for debugging
            logger.debug(f"Low band stats: {low_stats}")
            logger.debug(f"Mid-low band stats: {mid_low_stats}")
            logger.debug(f"Mid-high band stats: {mid_high_stats}")
            logger.debug(f"High band stats: {high_stats}")
            
            # Calculate band scores
            def get_band_score(stats, weight):
                # Harmonic sounds have low flatness
                harmonic_factor = 1.0 - stats["flatness"]
                # Energy factor
                energy_factor = min(1.0, stats["energy"] / 10.0)
                # Variability factor
                var_factor = stats["std"] / (stats["mean"] + 1e-5)
                
                # Combine factors
                score = weight * (0.5 * harmonic_factor + 0.3 * energy_factor + 0.2 * var_factor)
                return score
                
            # Weights for each band (mid ranges are most important for harmony)
            low_weight = 0.2
            mid_low_weight = 0.4
            mid_high_weight = 0.3
            high_weight = 0.1
            
            low_score = get_band_score(low_stats, low_weight)
            mid_low_score = get_band_score(mid_low_stats, mid_low_weight)
            mid_high_score = get_band_score(mid_high_stats, mid_high_weight)
            high_score = get_band_score(high_stats, high_weight)
            
            # Log band scores for debugging
            logger.debug(f"Harmonic band scores: low={low_score:.4f}, mid_low={mid_low_score:.4f}, mid_high={mid_high_score:.4f}, high={high_score:.4f}")
            
            # Calculate harmonic relationships between bands
            def get_harmonic_score(band1, band2):
                if band1.size == 0 or band2.size == 0:
                    return 0.0
                    
                # Normalize bands
                if np.max(band1) > 0:
                    band1_norm = band1 / np.max(band1)
                else:
                    band1_norm = band1
                    
                if np.max(band2) > 0:
                    band2_norm = band2 / np.max(band2)
                else:
                    band2_norm = band2
                    
                # Calculate correlation
                corr = np.corrcoef(np.mean(band1_norm, axis=0), np.mean(band2_norm, axis=0))[0, 1]
                # Handle NaN
                if np.isnan(corr):
                    corr = 0.0
                    
                # Scale to [0, 1]
                corr = (corr + 1.0) / 2.0
                
                return corr
                
            # Calculate harmonic relationships
            low_mid_low_score = get_harmonic_score(low, mid_low)
            mid_low_mid_high_score = get_harmonic_score(mid_low, mid_high)
            mid_high_high_score = get_harmonic_score(mid_high, high)
            
            # Log harmonic relationship scores
            logger.debug(f"Harmonic relationships: low-mid_low={low_mid_low_score:.4f}, mid_low-mid_high={mid_low_mid_high_score:.4f}, mid_high-high={mid_high_high_score:.4f}")
            
            # Calculate entropy (measure of randomness)
            def get_entropy(band):
                # Calculate power spectrum
                power = librosa.power_to_db(band, ref=np.max)
                
                # Flatten and normalize
                flat = power.flatten()
                if np.sum(flat) == 0:
                    return 0.0
                    
                # Normalize to probability distribution
                prob = flat / np.sum(flat)
                # Remove zeros
                prob = prob[prob > 0]
                # Calculate entropy
                entropy = -np.sum(prob * np.log2(prob))
                # Normalize to [0, 1]
                max_entropy = np.log2(len(prob))
                if max_entropy == 0:
                    return 0.0
                    
                return entropy / max_entropy
                
            # Calculate entropy for each band
            low_entropy = get_entropy(low)
            mid_low_entropy = get_entropy(mid_low)
            mid_high_entropy = get_entropy(mid_high)
            high_entropy = get_entropy(high)
            
            # Average entropy (lower is better for harmonic content)
            avg_entropy = (low_entropy + mid_low_entropy + mid_high_entropy + high_entropy) / 4.0
            entropy_score = 1.0 - avg_entropy  # Invert so higher is better
            
            # Log entropy scores
            logger.debug(f"Harmonic entropy scores: low={low_entropy:.4f}, mid_low={mid_low_entropy:.4f}, mid_high={mid_high_entropy:.4f}, high={high_entropy:.4f}, avg={avg_entropy:.4f}")
            
            # Combine scores
            band_score = low_score + mid_low_score + mid_high_score + high_score
            relationship_score = (low_mid_low_score + mid_low_mid_high_score + mid_high_high_score) / 3.0
            
            # Final harmonic ratio score
            harmonic_ratio = min(1.0, 0.5 * band_score + 0.3 * relationship_score + 0.2 * entropy_score)
            
            logger.info(f"Harmonic ratio calculation: band_score={band_score:.4f}, relationship_score={relationship_score:.4f}, entropy_score={entropy_score:.4f}, final={harmonic_ratio:.4f}")
            
            return harmonic_ratio
            
        except Exception as e:
            logger.error(f"Error calculating harmonic ratio: {str(e)}")
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