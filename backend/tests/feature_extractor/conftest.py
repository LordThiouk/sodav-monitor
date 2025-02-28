"""Test configuration for feature extractor tests."""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock
import os
import soundfile as sf
import io
from typing import Dict, Any
import librosa

@pytest.fixture
def sample_audio_data():
    """Generate a 1-second sine wave at 440Hz."""
    duration = 1.0
    sample_rate = 22050
    t = np.linspace(0, duration, int(sample_rate * duration))
    return np.sin(2 * np.pi * 440 * t)

@pytest.fixture
def sample_stereo_audio():
    """Create stereo audio data."""
    mono = sample_audio_data()
    return np.vstack((mono, mono * 0.8))

@pytest.fixture
def sample_music_data():
    """Generate complex musical signal."""
    duration = 2.0
    sample_rate = 22050
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Combine multiple frequencies for a rich musical sound
    signal = (
        0.5 * np.sin(2 * np.pi * 440 * t) +  # A4 note
        0.3 * np.sin(2 * np.pi * 554.37 * t) +  # C#5 note
        0.2 * np.sin(2 * np.pi * 659.25 * t)    # E5 note
    )
    
    # Add amplitude modulation for rhythm
    envelope = 0.5 * (1 + np.sin(2 * np.pi * 4 * t))
    return signal * envelope

@pytest.fixture
def sample_speech_data():
    """Generate speech-like audio data."""
    duration = 2.0
    sample_rate = 22050
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a formant-like structure with frequency modulation
    f0 = 120  # Fundamental frequency
    formants = [500, 1500, 2500]  # Typical speech formants
    signal = np.zeros_like(t)
    
    for formant in formants:
        # Add frequency modulation
        fm = formant + 100 * np.sin(2 * np.pi * 3 * t)
        signal += np.sin(2 * np.pi * fm * t)
    
    # Add amplitude modulation for syllabic rhythm
    envelope = 0.5 * (1 + np.sin(2 * np.pi * 2 * t))
    return signal * envelope / len(formants)

@pytest.fixture
def mock_librosa(mocker):
    """Mock librosa functions for testing."""
    mock_lib = mocker.MagicMock()
    
    # Mock feature extraction functions
    def mock_melspectrogram(y=None, sr=22050, **kwargs):
        """Generate mock mel spectrogram with harmonic pattern."""
        n_mels = kwargs.get('n_mels', 128)
        n_frames = 100
        mel_spec = np.zeros((n_mels, n_frames))
        
        # Add harmonic bands
        for i in range(5):
            band_center = int(n_mels * (i + 1) / 6)
            band_width = 5
            mel_spec[band_center-band_width:band_center+band_width, :] = 0.8 - 0.1 * i
            
        # Add temporal modulation
        t = np.linspace(0, 2*np.pi, n_frames)
        modulation = 0.2 * np.sin(2*t)
        mel_spec = mel_spec * (1 + modulation)
        
        return mel_spec

    def mock_mfcc(y=None, sr=22050, **kwargs):
        """Generate mock MFCCs with temporal structure."""
        n_mfcc = kwargs.get('n_mfcc', 20)
        n_frames = 100
        mfcc = np.zeros((n_mfcc, n_frames))
        
        # Add temporal patterns
        t = np.linspace(0, 4*np.pi, n_frames)
        for i in range(n_mfcc):
            mfcc[i, :] = 0.5 * np.sin(t + i*np.pi/n_mfcc)
        
        return mfcc

    def mock_spectral_contrast(y=None, sr=22050, **kwargs):
        """Generate mock spectral contrast with clear peaks and valleys."""
        n_bands = 7
        n_frames = 100
        contrast = np.zeros((n_bands, n_frames))
        
        # Create distinct bands with different intensities
        for i in range(n_bands):
            contrast[i, :] = 0.8 - 0.1 * i
            # Add some temporal variation
            t = np.linspace(0, 2*np.pi, n_frames)
            contrast[i, :] *= (1 + 0.2 * np.sin(2*t + i*np.pi/n_bands))
        
        return contrast

    def mock_chroma_stft(y=None, sr=22050, **kwargs):
        """Generate mock chroma features with clear tonal content."""
        n_chroma = 12
        n_frames = 100
        chroma = np.zeros((n_chroma, n_frames))
        
        # Create a pattern simulating a chord progression
        t = np.linspace(0, 4*np.pi, n_frames)
        for i in range(n_chroma):
            if i in [0, 4, 7]:  # Major chord
                chroma[i, :] = 0.8 * (1 + 0.2 * np.sin(t))
        
        return chroma

    def mock_onset_strength(y=None, sr=22050, **kwargs):
        """Generate mock onset strength with clear peaks."""
        n_frames = 100
        t = np.linspace(0, 4*np.pi, n_frames)
        # Create regular onset pattern with some variation
        onset_env = 0.6 + 0.4 * np.sin(2*t) + 0.2 * np.sin(5*t)
        onset_env = np.maximum(onset_env, 0)
        return onset_env

    def mock_peak_pick(onset_envelope, **kwargs):
        """Generate mock peaks at regular intervals."""
        # Return indices of peaks approximately every 10 frames
        base_peaks = np.arange(5, len(onset_envelope)-5, 10)
        # Add small random variations to peak positions
        peaks = base_peaks + np.random.randint(-2, 3, size=len(base_peaks))
        peaks = np.clip(peaks, 0, len(onset_envelope)-1)
        return peaks.astype(int)

    def mock_fix_length(x, size):
        """Mock fix_length to handle both numpy arrays and mocks."""
        if isinstance(x, Mock):
            return np.zeros(size)
        if len(x) > size:
            return x[:size]
        return np.pad(x, (0, size - len(x)))

    def mock_normalize(x):
        """Mock normalize to handle both numpy arrays and mocks."""
        if isinstance(x, Mock):
            return np.zeros_like(x)
        return x / (np.max(np.abs(x)) + 1e-8)

    # Assign mock functions
    mock_lib.feature.melspectrogram = mock_melspectrogram
    mock_lib.feature.mfcc = mock_mfcc
    mock_lib.feature.spectral_contrast = mock_spectral_contrast
    mock_lib.feature.chroma_stft = mock_chroma_stft
    mock_lib.onset.onset_strength = mock_onset_strength
    mock_lib.util.peak_pick = mock_peak_pick
    mock_lib.util.fix_length = mock_fix_length
    mock_lib.util.normalize = mock_normalize
    mock_lib.power_to_db = lambda x: x
    
    return mock_lib

@pytest.fixture
def mock_features():
    """Generate mock features for testing."""
    # Create more realistic test features
    t = np.linspace(0, 4*np.pi, 100)
    
    # Mel spectrogram with clear harmonic structure
    mel_spec = np.zeros((128, 100))
    for i in range(5):
        center = 20 + i * 20
        band_width = 4
        intensity = 0.8 - i * 0.1
        mel_spec[center-band_width:center+band_width, :] = intensity * (1 + 0.5 * np.sin(t))
    
    # MFCC with temporal patterns
    mfcc = np.zeros((20, 100))
    for i in range(20):
        mfcc[i, :] = 0.5 * np.sin(t + i/10)
    
    # Spectral contrast with distinct bands
    contrast = np.zeros((7, 100))
    for i in range(7):
        freq = i + 1
        intensity = 0.9 - i * 0.1
        contrast[i, :] = intensity * np.sin(freq * t)
    
    # Chroma with clear tonal content
    chroma = np.zeros((12, 100))
    scale = [0, 2, 4, 5, 7, 9, 11]
    for i in scale:
        intensity = 0.8 - 0.1 * (i / 12)
        chroma[i, :] = intensity * (1 + 0.3 * np.sin(t))
    
    return {
        "mel_spectrogram": mel_spec,
        "mfcc": mfcc,
        "spectral_contrast": contrast,
        "chroma": chroma
    }

@pytest.fixture
def real_world_samples(tmpdir):
    """Create test audio files with real-world characteristics."""
    sample_rate = 22050
    duration = 3.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create test directory
    test_dir = tmpdir.mkdir("test_audio")
    
    # Generate music sample with clear rhythm and harmony
    music_signal = np.zeros_like(t)
    # Add fundamental and harmonics
    for i, freq in enumerate([440, 880, 1320]):  # A4, A5, E6
        music_signal += (0.5 ** i) * np.sin(2 * np.pi * freq * t)
    # Add rhythm
    rhythm = 0.5 * (1 + np.sin(2 * np.pi * 4 * t))  # 4 Hz rhythm
    music_signal *= rhythm
    music_path = os.path.join(test_dir, "music.wav")
    sf.write(music_path, music_signal, sample_rate)
    
    # Generate speech sample with natural characteristics
    speech_signal = np.zeros_like(t)
    # Add formants
    for formant in [500, 1500, 2500]:
        fm = formant + 100 * np.sin(2 * np.pi * 3 * t)
        speech_signal += np.sin(2 * np.pi * fm * t)
    # Add natural envelope
    envelope = 0.5 * (1 + np.sin(2 * np.pi * 2 * t))
    speech_signal *= envelope
    speech_path = os.path.join(test_dir, "speech.wav")
    sf.write(speech_path, speech_signal / 3, sample_rate)
    
    # Generate noise sample with realistic spectrum
    noise_signal = np.random.randn(len(t))
    # Apply pink noise filter
    freqs = np.fft.fftfreq(len(t))
    f_noise = np.fft.fft(noise_signal)
    f_noise *= 1 / np.sqrt(np.abs(freqs) + 1e-8)
    noise_signal = np.real(np.fft.ifft(f_noise))
    noise_path = os.path.join(test_dir, "noise.wav")
    sf.write(noise_path, noise_signal * 0.1, sample_rate)
    
    # Generate silence
    silence_signal = np.zeros_like(t)
    silence_path = os.path.join(test_dir, "silence.wav")
    sf.write(silence_path, silence_signal, sample_rate)
    
    return {
        "music": music_path,
        "speech": speech_path,
        "noise": noise_path,
        "silence": silence_path
    }

def mock_real_world_audio(category, name):
    """Generate mock audio data based on sample configuration."""
    def generate_audio():
        if category == "music_samples":
            t = np.linspace(0, 1, 22050)
            if name == "classical_piano":
                return np.sin(2 * np.pi * 440 * t) + 0.5 * np.sin(2 * np.pi * 880 * t)
            else:  # rock_guitar
                return np.sin(2 * np.pi * 147 * t) + 0.3 * np.sin(2 * np.pi * 220 * t)
        elif category == "speech_samples":
            t = np.linspace(0, 1, 22050)
            if name == "male_speech":
                return np.sin(2 * np.pi * 120 * t) * (1 + 0.5 * np.sin(2 * np.pi * 4 * t))
            else:  # female_speech
                return np.sin(2 * np.pi * 200 * t) * (1 + 0.5 * np.sin(2 * np.pi * 5 * t))
        else:  # mixed_samples
            t = np.linspace(0, 1, 22050)
            music = np.sin(2 * np.pi * 440 * t) + 0.5 * np.sin(2 * np.pi * 880 * t)
            speech = np.sin(2 * np.pi * 200 * t) * (1 + 0.5 * np.sin(2 * np.pi * 5 * t))
            return 0.7 * music + 0.3 * speech
    
    return generate_audio()

@pytest.fixture(scope="session")
def test_audio_files(tmp_path_factory) -> Dict[str, str]:
    """Create test audio files with different characteristics."""
    base_path = tmp_path_factory.mktemp("test_audio")
    sample_rate = 22050
    duration = 3  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create music-like audio (multiple frequencies)
    frequencies = [440, 880, 1320]  # A4, A5, E6
    music = np.sum([np.sin(2 * np.pi * f * t) for f in frequencies], axis=0) / len(frequencies)
    music_path = os.path.join(base_path, "music.wav")
    sf.write(music_path, music, sample_rate)
    
    # Create speech-like audio (single frequency with amplitude modulation)
    carrier = 200  # Hz
    modulator = 4  # Hz
    speech = np.sin(2 * np.pi * carrier * t) * (0.5 + 0.5 * np.sin(2 * np.pi * modulator * t))
    speech_path = os.path.join(base_path, "speech.wav")
    sf.write(speech_path, speech, sample_rate)
    
    # Create noise audio
    noise = np.random.normal(0, 0.1, size=len(t))
    noise_path = os.path.join(base_path, "noise.wav")
    sf.write(noise_path, noise, sample_rate)
    
    # Create silence audio
    silence = np.zeros_like(t)
    silence_path = os.path.join(base_path, "silence.wav")
    sf.write(silence_path, silence, sample_rate)
    
    return {
        "music": music_path,
        "speech": speech_path,
        "noise": noise_path,
        "silence": silence_path
    }

@pytest.fixture
def mock_mel_spectrogram() -> np.ndarray:
    """Create a mock mel spectrogram."""
    return np.random.rand(128, 100)

@pytest.fixture
def mock_mfcc() -> np.ndarray:
    """Create mock MFCCs."""
    return np.random.rand(20, 100)

@pytest.fixture
def mock_spectral_contrast() -> np.ndarray:
    """Create mock spectral contrast."""
    return np.random.rand(7, 100)

@pytest.fixture
def mock_chroma() -> np.ndarray:
    """Create mock chromagram."""
    return np.random.rand(12, 100)

@pytest.fixture
def mock_features(mock_mel_spectrogram, mock_mfcc, mock_spectral_contrast, mock_chroma) -> Dict[str, Any]:
    """Create a complete set of mock features."""
    return {
        "mel_spectrogram": mock_mel_spectrogram,
        "mfcc": mock_mfcc,
        "spectral_contrast": mock_spectral_contrast,
        "chroma": mock_chroma,
        "rhythm_strength": 0.8,
        "confidence": 0.85
    }

@pytest.fixture
def audio_bytes() -> bytes:
    """Create a simple audio signal and convert it to bytes."""
    sample_rate = 22050
    duration = 1  # second
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
    
    # Convert to WAV bytes
    audio_buffer = io.BytesIO()
    sf.write(audio_buffer, audio, sample_rate, format='WAV')
    return audio_buffer.getvalue() 