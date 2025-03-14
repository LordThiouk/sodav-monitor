"""
Audio analysis module for SODAV Monitor.

This module provides functionality for analyzing audio data, extracting features,
and determining if audio contains music.
"""

import io
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union

import librosa
import numpy as np
import scipy.signal
from scipy.io import wavfile

# Configure logging
logger = logging.getLogger(__name__)


class AudioAnalyzer:
    """
    Class for analyzing audio data and extracting features.

    This class provides methods for processing audio data, extracting features,
    and determining if audio contains music.
    """

    def __init__(self):
        """Initialize the AudioAnalyzer with default parameters."""
        self.sample_rate = 44100
        self.n_mfcc = 13
        self.n_chroma = 12
        self.music_threshold = 0.6

        # Ensure scipy.signal.hann is available for librosa
        if not hasattr(scipy.signal, "hann"):
            scipy.signal.hann = scipy.signal.windows.hann

    def process_audio(self, audio_data: bytes) -> Tuple[np.ndarray, int]:
        """
        Process raw audio data into a format suitable for analysis.

        Args:
            audio_data: Raw audio data as bytes

        Returns:
            Tuple containing the audio samples as numpy array and the sample rate
        """
        try:
            # Convert bytes to in-memory file-like object
            audio_io = io.BytesIO(audio_data)

            # Try to read as WAV first
            try:
                sample_rate, samples = wavfile.read(audio_io)

                # Convert to float32 for librosa compatibility
                if samples.dtype == np.int16:
                    samples = samples.astype(np.float32) / 32767.0
                elif samples.dtype == np.int32:
                    samples = samples.astype(np.float32) / 2147483647.0

                # If stereo, convert to mono by averaging channels
                if len(samples.shape) > 1 and samples.shape[1] > 1:
                    samples = np.mean(samples, axis=1)

            except Exception as e:
                # If WAV reading fails, try librosa
                logger.debug(f"WAV reading failed, trying librosa: {e}")
                audio_io.seek(0)

                # Save to temporary file for librosa to read
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_file.write(audio_data)
                    temp_path = temp_file.name

                try:
                    samples, sample_rate = librosa.load(temp_path, sr=self.sample_rate, mono=True)
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

            return samples, sample_rate

        except Exception as e:
            logger.error(f"Error processing audio data: {e}")
            raise ValueError(f"Failed to process audio data: {e}")

    def extract_features(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Extract audio features from raw audio data.

        Args:
            audio_data: Raw audio data as bytes

        Returns:
            Dictionary of extracted features
        """
        try:
            samples, sample_rate = self.process_audio(audio_data)

            # Extract features using librosa
            mfccs = librosa.feature.mfcc(y=samples, sr=sample_rate, n_mfcc=self.n_mfcc)
            chroma = librosa.feature.chroma_stft(y=samples, sr=sample_rate)
            spectral_centroid = librosa.feature.spectral_centroid(y=samples, sr=sample_rate)
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=samples, sr=sample_rate)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=samples, sr=sample_rate)
            zero_crossing_rate = librosa.feature.zero_crossing_rate(samples)

            # Calculate tempo and beat features
            onset_env = librosa.onset.onset_strength(y=samples, sr=sample_rate)
            tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sample_rate)

            # Calculate energy
            energy = np.sum(samples**2) / len(samples)

            # Calculate RMS
            rms = librosa.feature.rms(y=samples)[0]

            # Return features as dictionary
            features = {
                "mfccs": mfccs.mean(axis=1).tolist(),
                "chroma": chroma.mean(axis=1).tolist(),
                "spectral_centroid": float(spectral_centroid.mean()),
                "spectral_bandwidth": float(spectral_bandwidth.mean()),
                "spectral_rolloff": float(spectral_rolloff.mean()),
                "zero_crossing_rate": float(zero_crossing_rate.mean()),
                "tempo": float(tempo),
                "energy": float(energy),
                "rms": float(np.mean(rms)),
            }

            return features

        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            raise ValueError(f"Failed to extract features: {e}")

    def is_music(self, audio_data: bytes) -> bool:
        """
        Determine if audio data contains music.

        Args:
            audio_data: Raw audio data as bytes

        Returns:
            True if audio contains music, False otherwise
        """
        try:
            features = self.extract_features(audio_data)

            # Simple heuristic for music detection based on features
            # Higher spectral centroid, more zero crossings, and higher energy typically indicate music
            spectral_centroid = features["spectral_centroid"]
            zero_crossing_rate = features["zero_crossing_rate"]
            energy = features["energy"]
            tempo = features["tempo"]

            # Normalize features
            norm_spectral = min(1.0, spectral_centroid / 5000)
            norm_zcr = min(1.0, zero_crossing_rate / 0.2)
            norm_energy = min(1.0, energy / 0.1)
            norm_tempo = 1.0 if 60 <= tempo <= 200 else max(0.0, 1.0 - abs(tempo - 120) / 120)

            # Calculate music score
            music_score = (
                norm_spectral * 0.3 + norm_zcr * 0.2 + norm_energy * 0.3 + norm_tempo * 0.2
            )

            return music_score > self.music_threshold

        except Exception as e:
            logger.error(f"Error determining if audio is music: {e}")
            return False

    def calculate_duration(self, audio_data: bytes) -> float:
        """
        Calculate the duration of audio data in seconds.

        Args:
            audio_data: Raw audio data as bytes

        Returns:
            Duration in seconds
        """
        try:
            samples, sample_rate = self.process_audio(audio_data)
            duration = len(samples) / sample_rate
            return duration
        except Exception as e:
            logger.error(f"Error calculating audio duration: {e}")
            raise ValueError(f"Failed to calculate audio duration: {e}")
