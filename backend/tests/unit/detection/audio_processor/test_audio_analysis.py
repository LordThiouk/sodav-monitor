"""Tests for the audio analysis module."""

import os
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import librosa
import numpy as np
import pytest
import scipy.signal

from backend.detection.audio_processor.audio_analysis import AudioAnalyzer

# Patch scipy.signal.hann for librosa's internal use
if not hasattr(scipy.signal, "hann"):
    scipy.signal.hann = scipy.signal.windows.hann


@pytest.fixture
def analyzer():
    """Create an AudioAnalyzer instance for testing."""
    return AudioAnalyzer()


@pytest.fixture
def mock_audio_data():
    """Create mock audio data for testing."""
    # Create a simple sine wave
    sample_rate = 44100
    duration = 1.0  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Create a more complex signal with harmonics for better feature detection
    f0 = 440  # A4 note
    signal = np.sin(2 * np.pi * f0 * t)  # Fundamental
    signal += 0.5 * np.sin(2 * np.pi * 2 * f0 * t)  # First harmonic
    signal += 0.25 * np.sin(2 * np.pi * 3 * f0 * t)  # Second harmonic

    # Add amplitude modulation for rhythm
    modulation = 1 + 0.2 * np.sin(2 * np.pi * 4 * t)
    signal *= modulation

    # Convert to 16-bit PCM
    signal = (signal * 32767).astype(np.int16)

    return signal.tobytes()


def test_process_audio_mono(analyzer, mock_audio_data):
    """Test processing mono audio data."""
    samples, sr = analyzer.process_audio(mock_audio_data)

    assert isinstance(samples, np.ndarray)
    assert sr == 44100
    assert len(samples.shape) == 1  # Mono audio
    assert np.abs(samples).max() <= 1.0  # Check normalization


def test_process_audio_stereo(analyzer):
    """Test processing stereo audio data."""
    # Create stereo audio data
    sample_rate = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    channel1 = np.sin(2 * np.pi * 440 * t)
    channel2 = np.sin(2 * np.pi * 880 * t)
    stereo = np.vstack((channel1, channel2)).T
    stereo = (stereo * 32767).astype(np.int16)

    audio_data = stereo.tobytes()
    samples, sr = analyzer.process_audio(audio_data)

    assert isinstance(samples, np.ndarray)
    assert sr == 44100
    assert len(samples.shape) == 1  # Should be converted to mono
    assert np.abs(samples).max() <= 1.0


def test_extract_features(audio_analyzer, sample_audio_data):
    """Test feature extraction"""
    features = audio_analyzer.extract_features(sample_audio_data)

    # Check required features
    assert "mfcc" in features
    assert "spectral_centroid" in features
    assert "spectral_rolloff" in features
    assert "zero_crossing_rate" in features

    # Check feature types
    assert isinstance(features["mfcc"], np.ndarray)
    assert isinstance(features["spectral_centroid"], float)
    assert isinstance(features["spectral_rolloff"], float)
    assert isinstance(features["zero_crossing_rate"], float)


def test_calculate_duration(analyzer, mock_audio_data):
    """Test audio duration calculation."""
    duration = analyzer.calculate_duration(mock_audio_data)

    assert isinstance(duration, float)
    assert duration > 0
    assert abs(duration - 1.0) < 0.1  # Should be close to 1 second


def test_is_music_with_music(analyzer, mock_audio_data):
    """Test music detection with musical content."""
    assert analyzer.is_music(mock_audio_data) is True


def test_is_music_with_speech(analyzer):
    """Test music detection with speech content."""
    # Create speech-like signal (more noise, less harmonic)
    sample_rate = 44100
    duration = 3.0
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Create noise with speech-like characteristics
    np.random.seed(42)  # For reproducibility
    noise = np.random.normal(0, 0.5, len(t))

    # Add some formant-like frequencies
    formants = [500, 1500, 2500]  # Typical speech formants
    signal = noise
    for f in formants:
        signal += 0.3 * np.sin(2 * np.pi * f * t)

    # Add amplitude modulation at speech rate (4-8 Hz)
    modulation = 1 + 0.5 * np.sin(2 * np.pi * 6 * t)
    signal *= modulation

    # Convert to audio data
    signal = (signal * 32767).astype(np.int16)

    assert analyzer.is_music(signal.tobytes()) is False


def test_is_music_error_handling(analyzer):
    """Test error handling in music detection."""
    with pytest.raises(ValueError, match="Empty audio data provided"):
        analyzer.is_music(b"")
    with pytest.raises(ValueError):
        analyzer.is_music(b"invalid audio data")


def test_extract_features_error_handling(analyzer):
    """Test error handling in feature extraction."""
    with pytest.raises(ValueError, match="Empty audio data provided"):
        analyzer.extract_features(b"")
    with pytest.raises(ValueError):
        analyzer.extract_features(b"invalid audio data")


def test_process_audio_error_handling(analyzer):
    """Test error handling in audio processing."""
    with pytest.raises(ValueError, match="Empty audio data provided"):
        analyzer.process_audio(b"")
    with pytest.raises(ValueError):
        analyzer.process_audio(b"invalid audio data")


def test_calculate_duration_error_handling(analyzer):
    """Test error handling in duration calculation."""
    with pytest.raises(ValueError, match="Empty audio data provided"):
        analyzer.calculate_duration(b"")
    with pytest.raises(ValueError):
        analyzer.calculate_duration(b"invalid audio data")


@pytest.fixture
def complex_mock_audio():
    """Create complex mock audio data with multiple instruments."""
    sample_rate = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Bass line (low frequency)
    bass = 0.5 * np.sin(2 * np.pi * 60 * t)

    # Lead melody (mid frequency with vibrato)
    vibrato = np.sin(2 * np.pi * 5 * t)  # 5 Hz vibrato
    melody = 0.8 * np.sin(2 * np.pi * 440 * (1 + 0.1 * vibrato) * t)

    # High frequency percussion
    percussion = np.random.normal(0, 0.1, len(t))
    percussion *= (np.sin(2 * np.pi * 4 * t) > 0).astype(float)  # 4 Hz rhythm

    # Combine and normalize
    signal = bass + melody + percussion
    signal = signal / np.max(np.abs(signal))

    # Convert to 16-bit PCM
    signal = (signal * 32767).astype(np.int16)

    return signal.tobytes()


@pytest.fixture
def different_sample_rates():
    """Create audio data with different sample rates."""
    sample_rates = [8000, 16000, 44100, 48000]
    audio_data = {}

    for sr in sample_rates:
        t = np.linspace(0, 1.0, sr)
        signal = np.sin(2 * np.pi * 440 * t)
        signal = (signal * 32767).astype(np.int16)
        audio_data[sr] = signal.tobytes()

    return audio_data


def test_process_audio_different_sample_rates(analyzer, different_sample_rates):
    """Test processing audio with different sample rates."""
    for sr, audio_data in different_sample_rates.items():
        samples, sample_rate = analyzer.process_audio(audio_data)
        assert isinstance(samples, np.ndarray)
        assert len(samples) > 0
        assert np.abs(samples).max() <= 1.0


def test_extract_features_complex_audio(analyzer, complex_mock_audio):
    """Test feature extraction with complex audio containing multiple instruments."""
    features = analyzer.extract_features(complex_mock_audio)

    # Verify spectral features reflect complexity
    assert features["spectral_bandwidth"] > 0  # Should have wide bandwidth
    assert features["spectral_rolloff"] > 0  # Should have high-frequency content
    assert features["zero_crossing_rate"] > 0  # Should have many zero crossings

    # Verify rhythmic features
    assert features["tempo"] > 0  # Should detect tempo
    assert len(features["beats"]) > 0  # Should detect beats
    assert np.mean(features["onset_strength"]) > 0  # Should have strong onsets


def test_is_music_with_complex_audio(analyzer, complex_mock_audio):
    """Test music detection with complex audio."""
    assert analyzer.is_music(complex_mock_audio) is True

    # Test with modified versions
    samples = np.frombuffer(complex_mock_audio, dtype=np.int16)
    samples_float = samples.astype(np.float32) / 32768.0

    # Test with quieter audio
    quiet = (samples_float * 0.1).astype(np.float32)
    quiet = (quiet * 32768.0).astype(np.int16).tobytes()
    assert analyzer.is_music(quiet) is True

    # Test with added noise
    noisy = samples_float + np.random.normal(0, 0.2, len(samples_float))
    noisy = np.clip(noisy, -1, 1)
    noisy = (noisy * 32768.0).astype(np.int16).tobytes()
    assert analyzer.is_music(noisy) is True


@pytest.mark.parametrize("window_size", [1024, 2048, 4096])
def test_feature_extraction_different_windows(analyzer, mock_audio_data, window_size):
    """Test feature extraction with different window sizes."""
    analyzer.window_size = window_size
    features = analyzer.extract_features(mock_audio_data)

    assert isinstance(features, dict)
    assert all(isinstance(features[k], (np.ndarray, float)) for k in features)
    assert features["duration"] > 0


def test_performance_large_audio(analyzer):
    """Test performance with large audio file."""
    # Create 30 seconds of audio
    sample_rate = 44100
    duration = 30.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    signal = np.sin(2 * np.pi * 440 * t)
    signal = (signal * 32767).astype(np.int16)

    import time

    start_time = time.time()

    features = analyzer.extract_features(signal.tobytes())

    processing_time = time.time() - start_time
    assert processing_time < 10.0  # Should process within 10 seconds
    assert isinstance(features, dict)
    assert features["duration"] == pytest.approx(duration, rel=0.1)


@patch("librosa.feature.mfcc")
@patch("librosa.feature.chroma_stft")
@patch("librosa.feature.spectral_centroid")
def test_librosa_integration(
    mock_spectral_centroid, mock_chroma_stft, mock_mfcc, analyzer, mock_audio_data
):
    """Test integration with librosa features."""
    # Mock librosa feature outputs
    mock_mfcc.return_value = np.random.rand(20, 100)
    mock_chroma_stft.return_value = np.random.rand(12, 100)
    mock_spectral_centroid.return_value = np.random.rand(1, 100)

    features = analyzer.extract_features(mock_audio_data)

    assert mock_mfcc.called
    assert mock_chroma_stft.called
    assert mock_spectral_centroid.called
    assert isinstance(features["mfcc"], np.ndarray)
    assert isinstance(features["chroma"], np.ndarray)
    assert isinstance(features["spectral_centroid"], float)


def test_edge_cases(analyzer):
    """Test edge cases in audio processing."""
    # Test with very short audio (< 1024 samples)
    short_signal = np.sin(np.linspace(0, 2 * np.pi, 512))
    short_audio = (short_signal * 32767).astype(np.int16).tobytes()

    with pytest.raises(ValueError, match="No valid audio samples found"):
        analyzer.process_audio(short_audio)

    # Test with silence
    silence = np.zeros(44100, dtype=np.int16).tobytes()
    assert analyzer.is_music(silence) is False

    # Test with DC offset
    dc_signal = np.ones(44100, dtype=np.int16) * 16384  # Half of max value
    with pytest.raises(ValueError, match="Audio data has excessive DC offset"):
        analyzer.process_audio(dc_signal.tobytes())

    # Test with pure noise
    np.random.seed(42)
    noise = np.random.normal(0, 32767 / 4, 44100).astype(np.int16)
    assert analyzer.is_music(noise.tobytes()) is False

    # Test with invalid values that will cause NaN
    signal = np.ones(4096, dtype=np.int16)
    signal[::2] = -32768  # Set every other value to minimum int16
    signal[1::2] = 32767  # Set remaining values to maximum int16
    invalid_audio = signal.tobytes()
    with pytest.raises(ValueError, match="Error processing audio: Audio data contains NaN values"):
        analyzer.process_audio(invalid_audio)


@pytest.fixture
def audio_analyzer():
    """Fixture for AudioAnalyzer instance"""
    return AudioAnalyzer()


@pytest.fixture
def sample_audio_data():
    """Fixture for generating sample audio data"""
    # Generate a simple sine wave
    sample_rate = 44100
    duration = 3  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration))
    frequency = 440  # Hz (A4 note)
    samples = np.sin(2 * np.pi * frequency * t)

    # Convert to 16-bit PCM
    samples = (samples * 32767).astype(np.int16)

    # Convert to bytes
    return samples.tobytes()


def test_init(audio_analyzer):
    """Test AudioAnalyzer initialization"""
    assert audio_analyzer.sample_rate == 44100


def test_process_audio(audio_analyzer, sample_audio_data):
    """Test audio processing"""
    samples, rate = audio_analyzer.process_audio(sample_audio_data)
    assert isinstance(samples, np.ndarray)
    assert rate == 44100
    assert len(samples) > 0


def test_is_music(audio_analyzer, sample_audio_data):
    """Test music detection"""
    is_music = audio_analyzer.is_music(sample_audio_data)
    assert isinstance(is_music, bool)


def test_invalid_audio_data(audio_analyzer):
    """Test handling of invalid audio data"""
    invalid_data = b"not audio data"

    with pytest.raises(ValueError):
        audio_analyzer.process_audio(invalid_data)


def test_empty_audio_data(audio_analyzer):
    """Test handling of empty audio data"""
    empty_data = b""

    with pytest.raises(ValueError):
        audio_analyzer.process_audio(empty_data)


def test_feature_extraction_with_noise(audio_analyzer):
    """Test feature extraction with noisy audio"""
    # Generate noise
    np.random.seed(42)
    noise = np.random.normal(0, 0.1, 44100 * 3)
    noise = (noise * 32767).astype(np.int16).tobytes()

    features = audio_analyzer.extract_features(noise)
    assert "mfcc" in features
    assert features["zero_crossing_rate"] > 0.4  # Noise has high zero crossing rate


def test_music_detection_threshold(audio_analyzer, sample_audio_data):
    """Test music detection thresholds"""
    # Pure tone should be detected as music
    assert audio_analyzer.is_music(sample_audio_data)

    # Noise should not be detected as music
    noise = np.random.normal(0, 0.1, 44100 * 3)
    noise = (noise * 32767).astype(np.int16).tobytes()
    assert not audio_analyzer.is_music(noise)


def test_spectral_feature_validation(audio_analyzer):
    """Test validation of spectral features."""
    # Generate test signal with known spectral content
    sample_rate = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Create signal with specific frequency components
    signal = (
        np.sin(2 * np.pi * 100 * t)
        + np.sin(2 * np.pi * 1000 * t)  # Bass frequency
        + np.sin(2 * np.pi * 5000 * t)  # Mid frequency  # High frequency
    )

    # Convert to audio data
    signal = (signal * 32767).astype(np.int16).tobytes()

    # Extract features
    features = audio_analyzer.extract_features(signal)

    # Validate spectral centroid (should be in mid-range due to frequency distribution)
    assert 500 < features["spectral_centroid"] < 3000


def test_rhythm_analysis(audio_analyzer):
    """Test rhythm detection and analysis."""
    # Generate rhythmic signal
    sample_rate = 44100
    duration = 4.0
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Create base signal
    signal = np.sin(2 * np.pi * 440 * t)

    # Add rhythm through amplitude modulation
    rhythm_freq = 4  # 4 Hz = 240 BPM
    envelope = 0.5 * (1 + np.sin(2 * np.pi * rhythm_freq * t))
    signal = signal * envelope

    # Convert to audio data
    signal = (signal * 32767).astype(np.int16).tobytes()

    # Extract features
    features = audio_analyzer.extract_features(signal)

    # Validate tempo detection (should be close to 240 BPM)
    assert 220 < features["tempo"] < 260


@pytest.mark.asyncio
async def test_concurrent_processing(audio_analyzer):
    """Test concurrent audio processing."""
    import asyncio

    # Generate multiple audio segments
    sample_rate = 44100
    duration = 1.0
    segments = []
    for freq in [440, 880, 1320]:  # Different frequencies
        t = np.linspace(0, duration, int(sample_rate * duration))
        signal = np.sin(2 * np.pi * freq * t)
        signal = (signal * 32767).astype(np.int16).tobytes()
        segments.append(signal)

    # Process segments concurrently
    async def process_segment(segment):
        features = audio_analyzer.extract_features(segment)
        return features

    tasks = [process_segment(segment) for segment in segments]
    results = await asyncio.gather(*tasks)

    # Validate results
    assert len(results) == len(segments)
    for features in results:
        assert isinstance(features, dict)
        assert "mfcc" in features
        assert "spectral_centroid" in features
        assert features["duration"] == pytest.approx(1.0, rel=0.1)


def test_memory_optimization(audio_analyzer):
    """Test memory usage during processing."""
    import os

    import psutil

    process = psutil.Process(os.getpid())

    # Generate large audio segment
    sample_rate = 44100
    duration = 10.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    signal = np.sin(2 * np.pi * 440 * t)
    signal = (signal * 32767).astype(np.int16).tobytes()

    # Measure memory before processing
    mem_before = process.memory_info().rss

    # Process audio
    features = audio_analyzer.extract_features(signal)

    # Measure memory after processing
    mem_after = process.memory_info().rss

    # Calculate memory usage
    mem_used = mem_after - mem_before

    # Memory usage should be reasonable (< 100MB for 10s audio)
    assert mem_used < 100 * 1024 * 1024
    assert isinstance(features, dict)
    assert features["duration"] == pytest.approx(10.0, rel=0.1)


def test_error_recovery(audio_analyzer):
    """Test error recovery in audio processing."""
    # Test recovery from invalid audio format
    with pytest.raises(ValueError, match="Error processing audio"):
        audio_analyzer.process_audio(b"invalid data")

    # Test recovery from corrupted audio
    corrupted_audio = np.random.bytes(1000)
    with pytest.raises(ValueError):
        audio_analyzer.process_audio(corrupted_audio)

    # Test recovery from zero-length audio
    with pytest.raises(ValueError, match="Error processing audio: Empty audio data provided"):
        audio_analyzer.process_audio(b"")

    # Test with invalid values that will cause NaN
    signal = np.ones(4096, dtype=np.int16)
    signal[::2] = -32768  # Set every other value to minimum int16
    signal[1::2] = 32767  # Set remaining values to maximum int16
    invalid_audio = signal.tobytes()
    with pytest.raises(ValueError, match="Error processing audio: Audio data contains NaN values"):
        audio_analyzer.process_audio(invalid_audio)
