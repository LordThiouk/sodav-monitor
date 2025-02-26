"""
Consolidated audio fingerprinting module for SODAV Monitor.
Combines functionality from fingerprint.py, audio_fingerprint.py, and fingerprint_generator.py
"""

import numpy as np
import librosa
import logging
from typing import Optional, Tuple, Dict, List, Any
import soundfile as sf
from io import BytesIO
from pydub import AudioSegment
import hashlib
from scipy import signal

logger = logging.getLogger(__name__)

class AudioFingerprinter:
    def __init__(self):
        """Initialize the audio fingerprinter with default parameters"""
        self.sample_rate = 44100
        self.n_mels = 128
        self.n_mfcc = 20
        self.fmax = 8000
        
    def process_audio_data(self, audio_data: bytes) -> Tuple[np.ndarray, int, int]:
        """
        Convert raw audio data to numpy array and extract basic properties.
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            Tuple of (samples, sample_rate, channels)
        """
        audio = AudioSegment.from_file(BytesIO(audio_data))
        samples = np.array(audio.get_array_of_samples())
        
        # Convert to mono if stereo
        if audio.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)
        
        # Normalize samples
        samples = samples.astype(float) / np.iinfo(samples.dtype).max
        
        return samples, audio.frame_rate, audio.channels

    def generate_fingerprint(self, audio_data: bytes) -> Optional[Tuple[float, str, Dict[str, Any]]]:
        """
        Generate an audio fingerprint and extract features.
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            Tuple of (duration_seconds, fingerprint_string, features_dict) or None if generation fails
        """
        try:
            samples, sr, channels = self.process_audio_data(audio_data)
            duration = len(samples) / sr
            
            # Extract core features
            mel_spec = librosa.feature.melspectrogram(
                y=samples,
                sr=sr,
                n_mels=self.n_mels,
                fmax=self.fmax
            )
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
            
            # Extract MFCC features
            mfcc = librosa.feature.mfcc(S=mel_spec_db, n_mfcc=self.n_mfcc)
            
            # Extract additional features
            chroma = librosa.feature.chroma_stft(y=samples, sr=sr)
            spectral_centroid = librosa.feature.spectral_centroid(y=samples, sr=sr)
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=samples, sr=sr)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=samples, sr=sr)
            
            # Find peaks for fingerprinting
            peaks = self._find_peaks(mel_spec_db)
            
            # Generate fingerprint hash
            features = np.concatenate([
                mfcc.flatten(),
                chroma.flatten(),
                spectral_centroid.flatten(),
                spectral_bandwidth.flatten(),
                spectral_rolloff.flatten()
            ])
            
            fingerprint = self._generate_hash(features, peaks)
            
            # Prepare feature dictionary
            features_dict = {
                'mfcc': mfcc.tolist(),
                'chroma': chroma.tolist(),
                'spectral_centroid': spectral_centroid.tolist(),
                'spectral_bandwidth': spectral_bandwidth.tolist(),
                'spectral_rolloff': spectral_rolloff.tolist(),
                'peaks': peaks
            }
            
            return duration, fingerprint, features_dict
            
        except Exception as e:
            logger.error(f"Error generating fingerprint: {str(e)}")
            return None
            
    def _find_peaks(self, spec: np.ndarray, threshold: float = 0.5) -> List[Tuple[int, int]]:
        """Find peaks in the spectrogram."""
        # Normalize spectrogram
        spec_normalized = (spec - np.min(spec)) / (np.max(spec) - np.min(spec))
        
        peaks = []
        for i in range(1, spec_normalized.shape[0] - 1):
            for j in range(1, spec_normalized.shape[1] - 1):
                if spec_normalized[i, j] > threshold:
                    # Check if it's a local maximum
                    window = spec_normalized[i-1:i+2, j-1:j+2]
                    if spec_normalized[i, j] == np.max(window):
                        peaks.append((i, j))
        
        return peaks
        
    def _generate_hash(self, features: np.ndarray, peaks: List[Tuple[int, int]]) -> str:
        """Generate a hash from features and peaks."""
        # Combine features and peaks into a single array
        peak_array = np.array(peaks).flatten() if peaks else np.array([])
        combined = np.concatenate([features, peak_array])
        
        # Generate SHA-256 hash
        hasher = hashlib.sha256()
        hasher.update(combined.tobytes())
        return hasher.hexdigest()
        
    def compare_fingerprints(self, fp1: str, fp2: str) -> float:
        """
        Compare two fingerprints and return similarity score.
        
        Args:
            fp1: First fingerprint hash
            fp2: Second fingerprint hash
            
        Returns:
            Similarity score between 0 and 1
        """
        if not fp1 or not fp2:
            return 0.0
            
        # Convert hashes to binary arrays
        bin1 = bin(int(fp1, 16))[2:].zfill(256)
        bin2 = bin(int(fp2, 16))[2:].zfill(256)
        
        # Calculate Hamming distance
        differences = sum(b1 != b2 for b1, b2 in zip(bin1, bin2))
        similarity = 1 - (differences / 256)
        
        return similarity
        
    def analyze_audio_characteristics(self, samples: np.ndarray, sr: int) -> Dict[str, float]:
        """
        Analyze audio characteristics for music detection.
        
        Args:
            samples: Audio samples
            sr: Sample rate
            
        Returns:
            Dictionary of audio characteristics
        """
        # Calculate frequency bands
        frequencies = np.fft.fftfreq(len(samples), 1/sr)
        spectrum = np.abs(np.fft.fft(samples))
        
        # Define frequency bands
        bass_mask = (frequencies >= 20) & (frequencies <= 250)
        mid_mask = (frequencies > 250) & (frequencies <= 2000)
        high_mask = (frequencies > 2000) & (frequencies <= 20000)
        
        # Calculate energy in each band
        bass_energy = np.sum(spectrum[bass_mask]) / len(spectrum)
        mid_energy = np.sum(spectrum[mid_mask]) / len(spectrum)
        high_energy = np.sum(spectrum[high_mask]) / len(spectrum)
        
        # Calculate rhythm strength
        tempo, _ = librosa.beat.beat_track(y=samples, sr=sr)
        onset_env = librosa.onset.onset_strength(y=samples, sr=sr)
        rhythm_strength = np.mean(onset_env)
        
        # Calculate spectral flux
        spec = np.abs(librosa.stft(samples))
        spectral_flux = np.mean(np.diff(spec, axis=1))
        
        # Calculate spectral centroid variance
        centroid = librosa.feature.spectral_centroid(y=samples, sr=sr)
        spectral_centroid_var = np.var(centroid)
        
        return {
            'bass_energy': float(bass_energy),
            'mid_energy': float(mid_energy),
            'high_energy': float(high_energy),
            'rhythm_strength': float(rhythm_strength),
            'spectral_flux': float(spectral_flux),
            'spectral_centroid_var': float(spectral_centroid_var),
            'tempo': float(tempo)
        } 