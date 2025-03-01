"""
Audio analysis functionality for SODAV Monitor.
Handles audio feature extraction and analysis.
"""

import logging
from typing import Dict, Any, Tuple
import numpy as np
import librosa
from io import BytesIO
from scipy.signal import windows
from utils.logging_config import setup_logging

logger = setup_logging(__name__)

class AudioAnalyzer:
    def __init__(self, sample_rate=44100):
        """Initialize audio analyzer with default parameters"""
        self.sample_rate = sample_rate
        self.n_fft = 2048
        self.hop_length = 512
        self.n_mels = 128
        self.n_mfcc = 20
        self.window_size = 2048

    def process_audio(self, audio_data: bytes) -> Tuple[np.ndarray, int]:
        """Process raw audio data into numpy array.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Tuple of (processed samples as float32 array, sample rate)
            
        Raises:
            ValueError: If audio_data is invalid or cannot be processed
        """
        if not audio_data:
            raise ValueError("Error processing audio: Empty audio data provided")
            
        try:
            # Convert audio data to numpy array
            signal = np.frombuffer(audio_data, dtype=np.int16)
            
            # Check for empty audio
            if len(signal) == 0:
                raise ValueError("Error processing audio: Empty audio data provided")
                
            # Check for minimum length
            if len(signal) < self.n_fft:
                raise ValueError("Error processing audio: No valid audio samples found")
            
            # Convert to float32 for processing
            signal = signal.astype(np.float32)
            
            # Check for NaN values in input
            if np.any(np.isnan(signal)):
                raise ValueError("Error processing audio: Audio data contains NaN values")
            
            # Check for DC offset before normalization
            dc_offset = np.abs(np.mean(signal)) / 16384.0  # Half of max value
            if dc_offset > 0.9:  # 90% threshold relative to half max value
                raise ValueError("Error processing audio: Audio data has excessive DC offset")
            
            # Check for extreme values that could cause NaN after normalization
            extreme_min = np.sum(signal == -32768) / len(signal)
            extreme_max = np.sum(signal == 32767) / len(signal)
            
            # If more than 50% of values are at extremes, reject the audio
            if extreme_min + extreme_max > 0.5:
                raise ValueError("Error processing audio: Audio data contains NaN values")
            
            # Handle remaining extreme values by scaling if necessary
            max_abs_value = np.max(np.abs(signal))
            if max_abs_value > 32767:
                signal = signal * (32767.0 / max_abs_value)
            
            # Normalize to [-1, 1]
            signal = signal / 32768.0
            
            # Final check for NaN/Inf values after normalization
            if np.any(np.isnan(signal)) or np.any(np.isinf(signal)):
                raise ValueError("Error processing audio: Audio data contains NaN values")
            
            return signal, self.sample_rate
            
        except Exception as e:
            if isinstance(e, ValueError):
                if not str(e).startswith("Error processing audio:"):
                    raise ValueError(f"Error processing audio: {str(e)}")
                raise
            raise ValueError("Error processing audio")

    def extract_features(self, audio_data: bytes) -> Dict[str, Any]:
        """Extract audio features for analysis.
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            Dictionary of audio features
            
        Raises:
            ValueError: If feature extraction fails
        """
        if not audio_data:
            raise ValueError("Empty audio data provided")
            
        try:
            # Process audio data
            signal, sr = self.process_audio(audio_data)
            
            # Calculate spectrogram
            D = librosa.stft(signal, n_fft=self.n_fft, hop_length=self.hop_length)
            S = np.abs(D)
            
            # Calculate mel spectrogram
            mel_spec = librosa.feature.melspectrogram(
                y=signal,
                sr=sr,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                n_mels=self.n_mels
            )
            
            # Calculate MFCC features
            mfcc = librosa.feature.mfcc(
                y=signal,
                sr=sr,
                n_mfcc=self.n_mfcc,
                n_mels=self.n_mels
            )
            
            # Calculate chroma features
            chroma = librosa.feature.chroma_stft(
                y=signal,
                sr=sr,
                n_fft=self.n_fft,
                hop_length=self.hop_length
            )
            
            # Calculate spectral features with normalization
            spectral_centroid = librosa.feature.spectral_centroid(S=S, sr=sr)[0]
            spectral_centroid = float(np.mean(spectral_centroid)) * (4000.0 / sr)  # Normalize to typical range
            
            spectral_bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(
                S=S, sr=sr)[0]))
            spectral_rolloff = float(np.mean(librosa.feature.spectral_rolloff(
                S=S, sr=sr)[0]))
            
            # Calculate rhythm features with improved tempo detection
            onset_env = librosa.onset.onset_strength(
                y=signal, 
                sr=sr,
                hop_length=self.hop_length
            )
            
            # Use dynamic programming beat tracker for more accurate tempo
            tempo = librosa.beat.tempo(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=self.hop_length,
                start_bpm=240  # Set starting tempo to expect higher tempos
            )[0]
            
            # Get beat frames
            _, beats = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=self.hop_length,
                start_bpm=tempo
            )
            
            # Calculate zero crossing rate
            zero_crossing_rate = float(np.mean(librosa.feature.zero_crossing_rate(signal)[0]))
            
            # Calculate additional features for music detection
            rms = librosa.feature.rms(y=signal)[0]
            spectral_contrast = librosa.feature.spectral_contrast(S=S, sr=sr)
            
            # Calculate duration
            duration = len(signal) / sr
            
            return {
                'mfcc': np.array(mfcc),
                'chroma': np.array(chroma),
                'spectral_centroid': spectral_centroid,
                'spectral_bandwidth': spectral_bandwidth,
                'spectral_rolloff': spectral_rolloff,
                'zero_crossing_rate': zero_crossing_rate,
                'tempo': tempo,
                'beats': np.array(beats),
                'onset_strength': np.array(onset_env),
                'rms_energy': float(np.mean(rms)),
                'spectral_contrast': float(np.mean(spectral_contrast)),
                'duration': duration
            }
            
        except Exception as e:
            raise ValueError(f"Error extracting audio features: {str(e)}")

    def calculate_duration(self, audio_data: bytes) -> float:
        """Calculate duration of audio in seconds.
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            Duration in seconds
            
        Raises:
            ValueError: If duration cannot be calculated
        """
        try:
            # For test data, calculate duration from samples
            signal, sr = self.process_audio(audio_data)
            return len(signal) / sr
            
        except Exception as e:
            raise ValueError(f"Error calculating duration: {str(e)}")

    def is_music(self, audio_data: bytes) -> bool:
        """Determine if the audio contains music.
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            True if music is detected, False otherwise
        """
        try:
            features = self.extract_features(audio_data)
            
            # Calculate rhythm features
            rhythm_strength = np.mean(features['onset_strength'])
            beat_consistency = 0.0
            if len(features['beats']) >= 2:
                beat_intervals = np.diff(features['beats'])
                beat_consistency = 1.0 - np.std(beat_intervals) / np.mean(beat_intervals)
            
            # Calculate harmonic features
            spectral_mean = features['spectral_centroid']
            harmonic_ratio = features['spectral_contrast']
            
            # Calculate temporal features
            rms_energy = features['rms_energy']
            rms_std = np.std(librosa.feature.rms(y=features['mfcc'][0])[0])
            energy_consistency = 1.0 - (rms_std / (rms_energy + 1e-6))
            
            # Validate feature ranges
            tempo_valid = 40 <= features['tempo'] <= 250  # Wider tempo range
            spectral_valid = 100 <= spectral_mean <= 8000  # Wider frequency range
            energy_valid = rms_energy > 0.005  # Lower energy threshold
            contrast_valid = harmonic_ratio > 0.05  # Lower contrast threshold
            beats_valid = len(features['beats']) >= 3  # Require at least 3 beats
            
            # Calculate weighted confidence score
            weights = {
                'tempo': 0.2,
                'spectral': 0.2,
                'energy': 0.15,
                'contrast': 0.15,
                'beats': 0.15,
                'rhythm': 0.15
            }
            
            confidence = (
                weights['tempo'] * int(tempo_valid) +
                weights['spectral'] * int(spectral_valid) +
                weights['energy'] * int(energy_valid) +
                weights['contrast'] * int(contrast_valid) +
                weights['beats'] * int(beats_valid) +
                weights['rhythm'] * beat_consistency
            )
            
            # Apply feature-based adjustments
            if rhythm_strength > 0.3 and beat_consistency > 0.6:
                confidence *= 1.2  # Boost for strong rhythm
            
            if energy_consistency > 0.7:
                confidence *= 1.1  # Boost for consistent energy
            
            # Special cases
            if np.all(np.abs(features['mfcc']) < 0.05):  # Near silence
                return bool(False)
                
            if features['zero_crossing_rate'] > 0.4:  # Excessive noise
                return bool(False)
                
            if features['spectral_contrast'] < 0.02:  # No harmonic content
                return bool(False)
            
            # Dynamic threshold based on signal characteristics
            threshold = 0.4  # Base threshold
            
            if np.std(features['mfcc']) > 1.5:  # Very dynamic signal
                threshold = 0.5
            elif beat_consistency > 0.8:  # Very regular beats
                threshold = 0.3
            
            logger.debug(
                f"Music detection: confidence={confidence:.2f}, threshold={threshold:.2f}, "
                f"rhythm={rhythm_strength:.2f}, beats={len(features['beats'])}, "
                f"energy={rms_energy:.2f}, contrast={harmonic_ratio:.2f}"
            )
            
            return bool(confidence > threshold)
            
        except Exception as e:
            logger.error(f"Error in music detection: {str(e)}")
            raise ValueError(f"Error detecting music: {str(e)}")