"""
Audio analysis functionality for SODAV Monitor.
Handles audio feature extraction and analysis.
"""

import logging
from typing import Dict, Any, Tuple, Union, List
import numpy as np
import librosa
from io import BytesIO
from pydub import AudioSegment
from scipy.signal import windows
from utils.logging_config import setup_logging

logger = setup_logging(__name__)

class AudioAnalyzer:
    """Audio analysis class for music detection."""
    def __init__(self, window_size=2048, hop_length=512, sample_rate=44100, min_duration=0.1):
        """Initialize audio analyzer with configurable parameters."""
        if window_size <= 0 or hop_length <= 0 or sample_rate <= 0 or min_duration <= 0:
            raise ValueError("Window size, hop length, sample rate, and min_duration must be positive")
        self.window_size = window_size
        self.hop_length = hop_length
        self.sample_rate = sample_rate
        self.min_duration = min_duration

    def process_audio(self, audio_data):
        """Process audio data and return normalized samples."""
        if not isinstance(audio_data, (bytes, np.ndarray)):
            raise ValueError("Invalid audio data type. Expected bytes or numpy array.")

        if not audio_data or (isinstance(audio_data, bytes) and len(audio_data) == 0):
            raise ValueError("Empty audio data provided")

        try:
            # Convert bytes to numpy array if needed
            if isinstance(audio_data, bytes):
                samples = np.frombuffer(audio_data, dtype=np.int16)
            else:
                samples = audio_data.copy()  # Make a copy to avoid modifying the input

            # Convert to float32 and normalize to [-1, 1]
            samples = samples.astype(np.float32)
            if np.issubdtype(samples.dtype, np.integer):
                samples = samples / 32767.0
            samples = np.clip(samples, -1.0, 1.0)

            # Ensure array is contiguous and in float32 format
            samples = np.ascontiguousarray(samples, dtype=np.float32)

            # Convert stereo to mono if needed
            if samples.ndim > 1:
                samples = np.mean(samples, axis=1)

            # Validate the processed samples
            if len(samples) == 0:
                raise ValueError("No valid audio samples found")

            # Pad short samples to window size
            original_length = len(samples)
            if original_length < self.window_size:
                pad_length = self.window_size - original_length
                samples = np.pad(samples, (0, pad_length), mode='constant')

            return samples, self.sample_rate, original_length

        except Exception as e:
            logger.error(f"Error processing audio data: {str(e)}")
            raise ValueError(f"Failed to process audio data: {str(e)}")

    def calculate_duration(self, audio_data):
        """Calculate the duration of the audio in seconds."""
        if not isinstance(audio_data, (bytes, np.ndarray)):
            raise ValueError("Invalid audio data type")

        if not audio_data or (isinstance(audio_data, bytes) and len(audio_data) == 0):
            raise ValueError("Empty audio data provided")
        
        try:
            _, sr, original_length = self.process_audio(audio_data)
            return float(original_length) / float(sr)
        except Exception as e:
            logger.error(f"Error calculating duration: {str(e)}")
            raise ValueError(f"Failed to calculate duration: {str(e)}")

    def extract_features(self, audio_data):
        """Extract audio features for music detection."""
        if not isinstance(audio_data, (bytes, np.ndarray)):
            raise ValueError("Invalid audio data type")

        if not audio_data or (isinstance(audio_data, bytes) and len(audio_data) == 0):
            raise ValueError("Empty audio data provided")

        try:
            samples, sr, original_length = self.process_audio(audio_data)
            
            # Calculate duration from original length
            duration = float(original_length) / float(sr)

            # Compute STFT with float32 output (reuse for multiple features)
            stft = librosa.stft(samples, n_fft=self.window_size, hop_length=self.hop_length, dtype=np.float32)
            stft_mag = np.abs(stft)
            
            # Compute mel spectrogram from STFT (reuse for multiple features)
            mel_spec = librosa.feature.melspectrogram(
                S=stft_mag**2,
                sr=sr,
                n_fft=self.window_size,
                hop_length=self.hop_length
            )

            # Compute spectral features efficiently (return means for scalar features)
            spectral_centroid = librosa.feature.spectral_centroid(
                S=stft_mag,
                sr=sr,
                n_fft=self.window_size,
                hop_length=self.hop_length
            )[0].mean()

            spectral_bandwidth = librosa.feature.spectral_bandwidth(
                S=stft_mag,
                sr=sr,
                n_fft=self.window_size,
                hop_length=self.hop_length
            )[0].mean()

            spectral_rolloff = librosa.feature.spectral_rolloff(
                S=stft_mag,
                sr=sr,
                n_fft=self.window_size,
                hop_length=self.hop_length
            )[0].mean()

            zero_crossing_rate = librosa.feature.zero_crossing_rate(
                y=samples,
                frame_length=self.window_size,
                hop_length=self.hop_length
            )[0].mean()

            # Compute MFCCs from mel spectrogram
            mfcc = librosa.feature.mfcc(
                S=librosa.power_to_db(mel_spec),
                sr=sr,
                n_mfcc=13
            )

            # Compute chroma features from STFT
            chroma = librosa.feature.chroma_stft(
                S=stft_mag,
                sr=sr,
                n_fft=self.window_size,
                hop_length=self.hop_length
            )

            # Compute onset strength and tempo
            onset_env = librosa.onset.onset_strength(
                S=mel_spec,
                sr=sr,
                hop_length=self.hop_length
            )
            tempo, beats = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=self.hop_length
            )

            # Compute harmonic and percussive components
            harmonic, percussive = librosa.effects.hpss(stft)
            harmonic_rms = np.sqrt(np.mean(np.abs(harmonic)**2, axis=0))
            percussive_rms = np.sqrt(np.mean(np.abs(percussive)**2, axis=0))

            # Return features dictionary with proper types (scalar values for non-array features)
            return {
                'duration': float(duration),
                'spectral_centroid': float(spectral_centroid),
                'spectral_bandwidth': float(spectral_bandwidth),
                'spectral_rolloff': float(spectral_rolloff),
                'zero_crossing_rate': float(zero_crossing_rate),
                'mfcc': mfcc,
                'chroma': chroma,
                'tempo': float(tempo),
                'beats': np.array(beats),
                'harmonic_rms': float(np.mean(harmonic_rms)),
                'percussive_rms': float(np.mean(percussive_rms)),
                'onset_strength': float(np.mean(onset_env))
            }
        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            raise ValueError(f"Failed to extract audio features: {str(e)}")

    def is_music(self, audio_data) -> bool:
        """Determine if the audio contains music."""
        if not isinstance(audio_data, (bytes, np.ndarray)):
            raise ValueError("Invalid audio data type")

        if not audio_data or (isinstance(audio_data, bytes) and len(audio_data) == 0):
            raise ValueError("Empty audio data provided")

        try:
            features = self.extract_features(audio_data)
            
            # Music detection criteria with refined thresholds
            criteria = {
                'harmonic': features['harmonic_rms'] > 0.2,  # Strong harmonic content
                'rhythm': (features['tempo'] >= 60 and features['tempo'] <= 180),  # Typical music tempo range
                'spectral': (features['spectral_centroid'] > 1000 and  # Higher frequency threshold
                           features['spectral_bandwidth'] > 2000),  # Higher bandwidth threshold
                'onset': features['onset_strength'] > 0.2,  # Strong onset strength
                'percussive': features['percussive_rms'] > 0.15,  # Significant percussive content
            }

            # Non-music criteria (speech/noise)
            non_music_criteria = {
                'high_zcr': features['zero_crossing_rate'] > 0.4,  # Very high zero-crossing rate
                'low_harmonic': features['harmonic_rms'] < 0.1,  # Very low harmonic content
                'irregular_tempo': features['tempo'] < 40 or features['tempo'] > 200,  # Irregular tempo
                'weak_onset': features['onset_strength'] < 0.1  # Very weak onset strength
            }

            # Check for silence
            if (features['spectral_centroid'] < 1e-4 or 
                features['onset_strength'] < 1e-4 or 
                (features['harmonic_rms'] < 1e-4 and features['percussive_rms'] < 1e-4)):
                return False

            # Audio must meet most music criteria and few non-music criteria
            music_score = sum(criteria.values())
            non_music_score = sum(non_music_criteria.values())

            return bool(music_score >= 3 and non_music_score <= 1)

        except Exception as e:
            logger.error(f"Error in music detection: {str(e)}")
            raise ValueError(f"Failed to detect music: {str(e)}")