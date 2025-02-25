import numpy as np
import librosa
from typing import List, Tuple

def generate_fingerprint(y: np.ndarray, sr: int) -> str:
    """
    Generate an acoustic fingerprint from audio data.
    This is a simplified version of the fingerprinting algorithm.
    For production use, you might want to use more sophisticated algorithms.
    """
    # Extract mel spectrogram
    mel_spec = librosa.feature.melspectrogram(
        y=y,
        sr=sr,
        n_mels=128,
        fmax=8000
    )
    
    # Convert to log scale
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    
    # Extract peaks (landmark points)
    peaks = _find_peaks(mel_spec_db)
    
    # Generate hash from peaks
    fingerprint = _generate_hash_from_peaks(peaks)
    
    return fingerprint

def _find_peaks(spec: np.ndarray, threshold: float = 0.5) -> List[Tuple[int, int]]:
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

def _generate_hash_from_peaks(peaks: List[Tuple[int, int]]) -> str:
    """Generate a hash string from peak points."""
    if not peaks:
        return ""
    
    # Sort peaks by time
    peaks.sort(key=lambda x: x[1])
    
    # Generate hash by considering pairs of peaks
    hashes = []
    for i in range(len(peaks) - 1):
        for j in range(1, min(4, len(peaks) - i)):
            p1 = peaks[i]
            p2 = peaks[i + j]
            
            # Create a hash from the frequency and time differences
            freq_diff = p2[0] - p1[0]
            time_diff = p2[1] - p1[1]
            
            # Combine values into a single hash
            point_hash = (p1[0] * 1000000 + p1[1] * 1000 + freq_diff * 100 + time_diff)
            hashes.append(str(point_hash))
    
    return ','.join(hashes)
