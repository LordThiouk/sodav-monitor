"""
Tests for the AudioFingerprinter class.
"""

from io import BytesIO

import numpy as np
import pytest
from detection.audio_processor.fingerprint import AudioFingerprinter
from pydub import AudioSegment


@pytest.fixture
def audio_fingerprinter():
    """Fixture to create an AudioFingerprinter instance."""
    return AudioFingerprinter()


@pytest.fixture
def sample_audio_data():
    """Fixture to create sample audio data for testing."""
    # Generate a simple sine wave
    sample_rate = 44100
    duration = 1.0  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration))
    samples = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave

    # Convert to 16-bit PCM
    samples = (samples * 32767).astype(np.int16)

    # Create audio segment
    audio = AudioSegment(samples.tobytes(), frame_rate=sample_rate, sample_width=2, channels=1)

    # Get audio data
    buffer = BytesIO()
    audio.export(buffer, format="wav")
    return buffer.getvalue()


def test_process_audio_data(audio_fingerprinter, sample_audio_data):
    """Test processing of raw audio data."""
    samples, sr, channels = audio_fingerprinter.process_audio_data(sample_audio_data)

    assert isinstance(samples, np.ndarray)
    assert sr == 44100
    assert channels == 1
    assert len(samples) > 0
    assert np.abs(samples).max() <= 1.0  # Check normalization


def test_generate_fingerprint(audio_fingerprinter, sample_audio_data):
    """Test fingerprint generation."""
    result = audio_fingerprinter.generate_fingerprint(sample_audio_data)

    assert result is not None
    duration, fingerprint, features = result

    assert isinstance(duration, float)
    assert isinstance(fingerprint, str)
    assert len(fingerprint) == 64  # SHA-256 hex digest length

    # Check features dictionary
    assert isinstance(features, dict)
    required_features = [
        "mfcc",
        "chroma",
        "spectral_centroid",
        "spectral_bandwidth",
        "spectral_rolloff",
        "peaks",
    ]
    for feature in required_features:
        assert feature in features


def test_find_peaks(audio_fingerprinter):
    """Test peak finding in spectrogram."""
    # Create a simple spectrogram with known peaks
    spec = np.zeros((10, 10))
    spec[2, 2] = 1.0
    spec[7, 7] = 1.0

    peaks = audio_fingerprinter._find_peaks(spec, threshold=0.5)

    assert len(peaks) == 2
    assert (2, 2) in peaks
    assert (7, 7) in peaks


def test_compare_fingerprints(audio_fingerprinter):
    """Test fingerprint comparison."""
    # Same fingerprints should have similarity 1.0
    fp1 = "a" * 64
    assert audio_fingerprinter.compare_fingerprints(fp1, fp1) == 1.0

    # Different fingerprints should have similarity < 1.0
    fp2 = "b" * 64
    assert audio_fingerprinter.compare_fingerprints(fp1, fp2) < 1.0

    # Empty fingerprints should have similarity 0.0
    assert audio_fingerprinter.compare_fingerprints("", "") == 0.0
    assert audio_fingerprinter.compare_fingerprints(fp1, "") == 0.0


def test_analyze_audio_characteristics(audio_fingerprinter, sample_audio_data):
    """Test audio characteristics analysis."""
    # Process audio data first
    samples, sr, _ = audio_fingerprinter.process_audio_data(sample_audio_data)

    # Analyze characteristics
    characteristics = audio_fingerprinter.analyze_audio_characteristics(samples, sr)

    # Check required characteristics
    required_characteristics = [
        "bass_energy",
        "mid_energy",
        "high_energy",
        "rhythm_strength",
        "spectral_flux",
        "spectral_centroid_var",
        "tempo",
    ]

    for characteristic in required_characteristics:
        assert characteristic in characteristics
        assert isinstance(characteristics[characteristic], float)
        assert characteristics[characteristic] >= 0.0


def test_error_handling(audio_fingerprinter):
    """Test error handling with invalid audio data."""
    # Test with invalid audio data
    invalid_data = b"not audio data"
    result = audio_fingerprinter.generate_fingerprint(invalid_data)
    assert result is None
