"""Test configuration for feature extractor tests."""

import pytest
import numpy as np
from unittest.mock import Mock

@pytest.fixture
def sample_audio_data():
    """Generate sample audio data for testing."""
    # Generate a 1-second sine wave at 440Hz (A4 note)
    duration = 1.0
    sample_rate = 22050
    t = np.linspace(0, duration, int(sample_rate * duration))
    return np.sin(2 * np.pi * 440 * t)

@pytest.fixture
def sample_stereo_audio():
    """Generate sample stereo audio data for testing."""
    # Generate two channels of audio
    duration = 1.0
    sample_rate = 22050
    t = np.linspace(0, duration, int(sample_rate * duration))
    channel1 = np.sin(2 * np.pi * 440 * t)  # A4 note
    channel2 = np.sin(2 * np.pi * 880 * t)  # A5 note
    return np.vstack((channel1, channel2)).T

@pytest.fixture
def sample_music_data():
    """Generate sample music-like audio data."""
    duration = 1.0
    sample_rate = 22050
    t = np.linspace(0, duration, int(sample_rate * duration))
    # Combine multiple frequencies to create a more complex signal
    signal = (
        np.sin(2 * np.pi * 440 * t) +   # A4
        np.sin(2 * np.pi * 880 * t) +   # A5
        np.sin(2 * np.pi * 1320 * t)    # E5
    )
    return signal / 3  # Normalize amplitude

@pytest.fixture
def sample_speech_data():
    """Generate sample speech-like audio data."""
    duration = 1.0
    sample_rate = 22050
    t = np.linspace(0, duration, int(sample_rate * duration))
    # Create a signal with characteristics more like speech
    signal = np.sin(2 * np.pi * 150 * t)  # Fundamental frequency
    # Add some random modulation
    modulation = np.random.normal(0, 0.1, len(t))
    return signal * (1 + modulation)

@pytest.fixture
def mock_librosa(mocker):
    """Mock librosa functions for testing."""
    mock = mocker.MagicMock()
    
    # Configure mock functions to return numpy arrays
    mock.feature.melspectrogram.return_value = mock_melspectrogram()
    mock.feature.mfcc.return_value = mock_mfcc()
    mock.feature.spectral_contrast.return_value = mock_spectral_contrast()
    mock.feature.chroma_stft.return_value = mock_chroma()
    
    # Configure power_to_db to return the input array
    mock.power_to_db = lambda x, **kwargs: x
    
    return mock

def mock_melspectrogram(y=None):
    """Mock mel spectrogram with shape (128, 100)."""
    if y is None:
        return np.random.rand(128, 100)
    
    # Generate mel spectrogram based on signal characteristics
    fft = np.fft.fft(y)
    peak_ratio = np.max(fft) / np.mean(fft)
    
    if peak_ratio > 5:  # Music-like signal
        mel_spec = np.random.rand(128, 100) * 0.8 + 0.2
    else:  # Speech or noise
        mel_spec = np.random.rand(128, 100) * 0.4
    
    return mel_spec

def mock_mfcc():
    """Mock MFCC features with shape (20, 100)."""
    return np.random.rand(20, 100)

def mock_spectral_contrast():
    """Mock spectral contrast features with shape (7, 100)."""
    return np.random.rand(7, 100)

def mock_chroma():
    """Mock chroma features with shape (12, 100)."""
    return np.random.rand(12, 100)

def mock_power_to_db(S, ref=1.0, amin=1e-10, top_db=80.0):
    """Mock power_to_db function."""
    log_spec = 10.0 * np.log10(np.maximum(amin, S))
    if callable(ref):
        ref_value = ref(S)
    else:
        ref_value = ref
    log_spec -= 10.0 * np.log10(np.maximum(amin, ref_value))
    return np.maximum(log_spec, log_spec.max() - top_db)

def mock_beat_track(onset_envelope=None, sr=22050, **kwargs):
    """Mock beat tracking function."""
    if onset_envelope is None:
        onset_envelope = np.random.rand(100)
    # Return mock tempo and beat frames
    tempo = 120.0  # Mock tempo in BPM
    beat_frames = np.arange(0, len(onset_envelope), len(onset_envelope) // 8)  # 8 beats
    return tempo, beat_frames

def mock_onset_strength(S=None, sr=None, **kwargs):
    # For testing purposes, we always return 100 frames
    n_frames = 100
    
    if S is None:
        return np.random.rand(n_frames)
    
    # Calculate mean energy in lower frequency bands
    energy = np.mean(S[:40], axis=0)  # Focus on lower frequencies
    
    # For music: Strong, regular onsets
    if np.max(S) > 0.8:  # Music-like mel spectrogram
        # Create regular beat pattern with varying strength
        onsets = np.zeros_like(energy)  # Match the shape of energy
        # Add strong beats every 4 frames (simulating 4/4 time)
        onsets[::4] = 0.95 + 0.05 * np.random.rand(len(onsets[::4]))
        # Add weaker beats on off-beats
        onsets[2::4] = 0.5 + 0.1 * np.random.rand(len(onsets[2::4]))
        # Modulate with energy envelope
        onsets *= 0.7 + 0.3 * (energy / np.max(energy))
    else:  # Speech or noise
        # Create irregular onsets with varying strength
        onsets = np.random.rand(*energy.shape) * 0.5
        # Add occasional stronger onsets
        onsets[np.random.rand(*energy.shape) > 0.8] *= 2.0

    return onsets

def mock_peak_pick(onset_env, pre_max=3, post_max=3, pre_avg=3, post_avg=3, delta=0.2, wait=1):
    """Mock peak picking function."""
    # Find peaks using a simple threshold-based approach
    peaks = []
    for i in range(pre_max, len(onset_env) - post_max):
        if onset_env[i] > delta:
            if onset_env[i] == max(onset_env[i-pre_max:i+post_max+1]):
                # Check if it's significantly above the local average
                pre_avg_val = np.mean(onset_env[i-pre_avg:i])
                post_avg_val = np.mean(onset_env[i:i+post_avg])
                if onset_env[i] > pre_avg_val + delta and onset_env[i] > post_avg_val + delta:
                    # Ensure minimum distance between peaks
                    if not peaks or (i - peaks[-1]) >= wait:
                        peaks.append(i)
    return np.array(peaks)

@pytest.fixture
def real_world_samples():
    """Provide a set of real-world audio samples with known characteristics."""
    import os
    import json
    
    # Define sample data with expected characteristics
    samples = {
        "music_samples": [
            {
                "name": "classical_piano",
                "features": {
                    "tempo_range": (60, 120),
                    "frequency_peaks": [440, 880, 1760],  # A4, A5, A6
                    "expected_confidence": 0.95
                }
            },
            {
                "name": "rock_guitar",
                "features": {
                    "tempo_range": (120, 160),
                    "frequency_peaks": [82, 147, 196],  # E2, D3, G3
                    "expected_confidence": 0.90
                }
            }
        ],
        "speech_samples": [
            {
                "name": "male_speech",
                "features": {
                    "frequency_range": (85, 180),
                    "expected_confidence": 0.3
                }
            },
            {
                "name": "female_speech",
                "features": {
                    "frequency_range": (165, 255),
                    "expected_confidence": 0.3
                }
            }
        ],
        "mixed_samples": [
            {
                "name": "music_with_vocals",
                "features": {
                    "tempo_range": (90, 130),
                    "frequency_peaks": [440, 880],
                    "expected_confidence": 0.85
                }
            }
        ]
    }
    
    return samples

@pytest.fixture
def mock_real_world_audio(real_world_samples):
    """Generate mock audio data that matches real-world characteristics."""
    
    def generate_audio(sample_type, name):
        sample_rate = 22050
        duration = 3.0  # 3 seconds
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        if sample_type == "music_samples":
            sample = next(s for s in real_world_samples[sample_type] if s["name"] == name)
            # Generate complex musical signal
            signal = np.zeros_like(t)
            for freq in sample["features"]["frequency_peaks"]:
                signal += np.sin(2 * np.pi * freq * t)
            # Add harmonics
            for freq in sample["features"]["frequency_peaks"]:
                signal += 0.5 * np.sin(2 * np.pi * freq * 2 * t)  # First harmonic
            # Add amplitude modulation for tempo
            tempo = np.mean(sample["features"]["tempo_range"])
            signal *= (1 + 0.2 * np.sin(2 * np.pi * (tempo/60) * t))
            
        elif sample_type == "speech_samples":
            sample = next(s for s in real_world_samples[sample_type] if s["name"] == name)
            # Generate speech-like signal
            freq_range = sample["features"]["frequency_range"]
            fundamental = np.mean(freq_range)
            signal = np.sin(2 * np.pi * fundamental * t)
            # Add natural variations
            signal *= (1 + 0.3 * np.random.normal(0, 1, len(t)))
            # Add formants
            for formant in [fundamental*2, fundamental*3, fundamental*4]:
                signal += 0.3 * np.sin(2 * np.pi * formant * t)
            
        elif sample_type == "mixed_samples":
            sample = next(s for s in real_world_samples[sample_type] if s["name"] == name)
            # Combine music and speech characteristics
            # Musical component
            signal = np.zeros_like(t)
            for freq in sample["features"]["frequency_peaks"]:
                signal += np.sin(2 * np.pi * freq * t)
            # Add vocal-like modulation
            vocal_freq = 220  # Average vocal frequency
            signal += 0.5 * np.sin(2 * np.pi * vocal_freq * t) * (1 + 0.3 * np.random.normal(0, 1, len(t)))
            
        # Normalize
        signal = signal / np.max(np.abs(signal))
        return signal
    
    return generate_audio 