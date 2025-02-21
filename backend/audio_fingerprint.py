import numpy as np
import librosa
import logging
from typing import Optional, Tuple, Dict
import soundfile as sf
from io import BytesIO
from pydub import AudioSegment
import tempfile
import os
import hashlib

logger = logging.getLogger(__name__)

def generate_fingerprint(audio_data: bytes) -> Optional[Tuple[float, str]]:
    """
    Generate an audio fingerprint using librosa features.
    
    Args:
        audio_data: Raw audio data in bytes
        
    Returns:
        Tuple of (duration_seconds, fingerprint_string) or None if generation fails
    """
    try:
        # Convert audio to WAV format
        audio = AudioSegment.from_file(BytesIO(audio_data))
        samples = np.array(audio.get_array_of_samples())
        
        # Convert to mono if stereo
        if audio.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)
        
        # Normalize samples
        samples = samples.astype(float) / np.iinfo(samples.dtype).max
        
        # Extract features
        mel_spec = librosa.feature.melspectrogram(y=samples, sr=audio.frame_rate)
        mfcc = librosa.feature.mfcc(S=librosa.power_to_db(mel_spec), n_mfcc=20)
        chroma = librosa.feature.chroma_stft(y=samples, sr=audio.frame_rate)
        
        # Combine features
        features = np.concatenate([
            mfcc.flatten(),
            chroma.flatten(),
            librosa.feature.spectral_centroid(y=samples, sr=audio.frame_rate).flatten(),
            librosa.feature.spectral_bandwidth(y=samples, sr=audio.frame_rate).flatten(),
            librosa.feature.spectral_rolloff(y=samples, sr=audio.frame_rate).flatten()
        ])
        
        # Generate hash from features
        fingerprint = hashlib.md5(features.tobytes()).hexdigest()
        duration = len(samples) / audio.frame_rate
        
        return duration, fingerprint
        
    except Exception as e:
        logger.error(f"Error in fingerprint generation: {str(e)}")
        return None

def compare_fingerprints(fp1: str, fp2: str) -> float:
    """
    Compare two fingerprints and return a similarity score.
    For MD5 hashes, we can only check exact matches.
    
    Args:
        fp1: First fingerprint string (MD5 hash)
        fp2: Second fingerprint string (MD5 hash)
        
    Returns:
        100.0 if fingerprints match, 0.0 otherwise
    """
    try:
        return 100.0 if fp1 == fp2 else 0.0
        
    except Exception as e:
        logger.error(f"Error comparing fingerprints: {str(e)}")
        return 0.0

def get_audio_features(audio_data: bytes) -> dict:
    """
    Extract audio features for additional comparison.
    
    Args:
        audio_data: Raw audio data in bytes
        
    Returns:
        Dictionary of audio features
    """
    try:
        # Convert audio to numpy array
        audio = AudioSegment.from_file(BytesIO(audio_data))
        samples = np.array(audio.get_array_of_samples())
        
        # Convert to mono if stereo
        if audio.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)
        
        # Normalize samples
        samples = samples.astype(float) / np.iinfo(samples.dtype).max
        
        # Extract features
        spectral_centroid = librosa.feature.spectral_centroid(y=samples, sr=audio.frame_rate)
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=samples, sr=audio.frame_rate)
        spectral_rolloff = librosa.feature.spectral_rolloff(y=samples, sr=audio.frame_rate)
        zero_crossing_rate = librosa.feature.zero_crossing_rate(samples)
        
        return {
            "spectral_centroid_mean": float(np.mean(spectral_centroid)),
            "spectral_bandwidth_mean": float(np.mean(spectral_bandwidth)),
            "spectral_rolloff_mean": float(np.mean(spectral_rolloff)),
            "zero_crossing_rate_mean": float(np.mean(zero_crossing_rate)),
            "duration": len(samples) / audio.frame_rate
        }
        
    except Exception as e:
        logger.error(f"Error extracting audio features: {str(e)}")
        return {} 