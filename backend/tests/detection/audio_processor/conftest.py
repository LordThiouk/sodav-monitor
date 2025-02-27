"""Test configuration for feature extractor tests."""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.database import Base, RadioStation, Track, TrackDetection

@pytest.fixture
def real_world_samples():
    """Provide a set of real-world audio samples with known characteristics."""
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

@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    return create_engine('sqlite:///:memory:')

@pytest.fixture(scope="session")
def tables(engine):
    """Create all database tables."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(engine, tables):
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def mock_real_world_audio():
    """Generate mock audio data for different sample types."""
    def generate_audio(sample_type: str, name: str) -> np.ndarray:
        """Generate audio data based on sample type and name."""
        duration = 1.0  # 1 second
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        if sample_type == "music_samples":
            if name == "classical_piano":
                # Generate piano-like sound with harmonics
                audio = np.sin(2 * np.pi * 440 * t) * 0.5  # A4 note
                audio += np.sin(2 * np.pi * 880 * t) * 0.3  # First harmonic
                audio += np.sin(2 * np.pi * 1320 * t) * 0.2  # Second harmonic
            else:  # rock_guitar
                # Generate distorted guitar-like sound
                audio = np.sin(2 * np.pi * 196 * t)  # G3 note
                audio = np.clip(audio * 1.5, -1, 1)  # Add distortion
                
        elif sample_type == "speech_samples":
            if name == "male_speech":
                # Generate male speech-like formants
                f0 = 120  # Fundamental frequency for male voice
                audio = np.sin(2 * np.pi * f0 * t) * 0.3
                for formant in [500, 1500, 2500]:
                    audio += np.sin(2 * np.pi * formant * t) * 0.2
            else:  # female_speech
                # Generate female speech-like formants
                f0 = 210  # Fundamental frequency for female voice
                audio = np.sin(2 * np.pi * f0 * t) * 0.3
                for formant in [550, 1650, 2750]:
                    audio += np.sin(2 * np.pi * formant * t) * 0.2
                    
        else:  # mixed_samples
            # Generate mixed music and speech
            music = np.sin(2 * np.pi * 440 * t) * 0.4
            speech = np.sin(2 * np.pi * 165 * t) * 0.3
            for formant in [500, 1500, 2500]:
                speech += np.sin(2 * np.pi * formant * t) * 0.1
            audio = music + speech
            
        # Normalize audio
        audio = audio / np.max(np.abs(audio))
        return audio
        
    return generate_audio

@pytest.fixture
def mock_librosa():
    """Mock librosa functions for testing."""
    mock = Mock()
    
    # Mock load to return 1 second of silence
    mock.load.return_value = (np.zeros(22050), 22050)
    
    # Mock feature extraction functions
    mock.feature.melspectrogram.return_value = np.random.rand(128, 100)
    mock.feature.mfcc.return_value = np.random.rand(20, 100)
    mock.feature.spectral_contrast.return_value = np.random.rand(7, 100)
    mock.feature.chroma_stft.return_value = np.random.rand(12, 100)
    
    # Mock onset detection with proper numpy array
    mock.onset.onset_strength.return_value = np.random.rand(100)
    
    # Mock beat tracking with proper return values
    mock.beat.beat_track.return_value = (120.0, np.array([10, 20, 30, 40]))
    
    # Mock power to db conversion
    mock.power_to_db.return_value = np.random.rand(128, 100)
    
    # Mock utilities
    mock.util.normalize.side_effect = lambda x: x / (np.max(np.abs(x)) + 1e-6)
    
    return mock

@pytest.fixture
def sample_radio_station(db_session):
    """Create a sample radio station for testing."""
    station = RadioStation(
        name="Test Radio",
        url="http://test-stream.com/stream",
        status="active"
    )
    db_session.add(station)
    db_session.commit()
    return station

@pytest.fixture
def sample_track(db_session):
    """Create a sample track for testing."""
    track = Track(
        title="Test Song",
        artist="Test Artist",
        duration=180.0,
        fingerprint="test_fingerprint",
        fingerprint_raw=b"test_raw_fingerprint"
    )
    db_session.add(track)
    db_session.commit()
    return track

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
    """Mock onset strength function."""
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