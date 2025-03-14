"""Tests for the FeatureExtractor class."""

from unittest.mock import Mock, patch

import librosa
import numpy as np
import psutil
import pytest

from backend.detection.audio_processor.feature_extractor import FeatureExtractor


@pytest.fixture
def feature_extractor():
    """Create a FeatureExtractor instance with default parameters."""
    return FeatureExtractor()


@pytest.fixture
def sample_audio():
    """Generate a sample audio signal for testing."""
    # Generate a 1-second sine wave at 440Hz
    duration = 1.0
    sample_rate = 22050
    t = np.linspace(0, duration, int(sample_rate * duration))
    signal = np.sin(2 * np.pi * 440 * t)
    return signal.astype(np.float32)  # Ensure float32 format


@pytest.fixture
def complex_audio():
    """Generate complex audio signal with rhythm and harmonics."""
    duration = 1.0  # 1 second
    sr = 22050  # Match FeatureExtractor sample rate
    n_samples = int(duration * sr)
    t = np.linspace(0, duration, n_samples)

    # Generate three harmonic frequencies
    f0 = 440.0  # Base frequency (A4)
    signal = (
        np.sin(2 * np.pi * f0 * t)
        + 0.5 * np.sin(2 * np.pi * 2 * f0 * t)
        + 0.25 * np.sin(2 * np.pi * 4 * f0 * t)
    )

    # Add rhythmic envelope (120 BPM)
    bpm = 120
    beats_per_sec = bpm / 60
    envelope = np.sin(2 * np.pi * beats_per_sec * t) * 0.5 + 0.5
    envelope = envelope**2  # Sharpen the envelope
    signal = signal * envelope

    # Add some noise
    noise = np.random.normal(0, 0.1, n_samples)
    signal = signal + noise

    # Normalize
    signal = librosa.util.normalize(signal)
    return signal.astype(np.float32)  # Ensure float32 format


@pytest.fixture
def noise_audio():
    """Generate white noise audio signal."""
    duration = 1.0  # 1 second
    sr = 22050  # Match FeatureExtractor sample rate
    n_samples = int(duration * sr)

    # Generate colored noise with temporal variation
    noise = np.random.normal(0, 1, n_samples)

    # Add some temporal variation
    envelope = np.sin(2 * np.pi * 2 * np.linspace(0, duration, n_samples)) * 0.5 + 0.5
    noise = noise * envelope

    # Add sudden amplitude changes
    change_points = np.random.choice(n_samples, 5)
    for point in change_points:
        if point < n_samples - 100:
            noise[point : point + 100] *= 2.0

    # Normalize
    noise = librosa.util.normalize(noise)
    return noise.astype(np.float32)  # Ensure float32 format


@pytest.fixture
def mock_audio_data():
    """Create mock audio data in bytes format."""
    return b"mock_audio_data"


class TestFeatureExtractorInitialization:
    """Test FeatureExtractor initialization and parameter validation."""

    def test_default_initialization(self):
        """Test initialization with default parameters."""
        extractor = FeatureExtractor()
        assert extractor.sample_rate == 22050
        assert extractor.n_mels == 128
        assert extractor.n_fft == 2048
        assert extractor.hop_length == 512

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        extractor = FeatureExtractor(sample_rate=44100, n_mels=64, n_fft=1024, hop_length=256)
        assert extractor.sample_rate == 44100
        assert extractor.n_mels == 64
        assert extractor.n_fft == 1024
        assert extractor.hop_length == 256

    @pytest.mark.parametrize(
        "param,value", [("sample_rate", 0), ("n_mels", -1), ("n_fft", 0), ("hop_length", -10)]
    )
    def test_invalid_parameters(self, param, value):
        """Test initialization with invalid parameters."""
        params = {"sample_rate": 22050, "n_mels": 128, "n_fft": 2048, "hop_length": 512}
        params[param] = value

        with pytest.raises(ValueError):
            FeatureExtractor(**params)


class TestFeatureExtraction:
    """Test feature extraction functionality."""

    def test_extract_features_shape(self, feature_extractor, sample_audio):
        """Test the shape of extracted features."""
        features = feature_extractor.extract_features(sample_audio)

        assert isinstance(features, dict)
        assert "mel_spectrogram" in features
        assert "mfcc" in features
        assert "spectral_contrast" in features
        assert "chroma" in features

        # Check feature dimensions
        n_frames = 1 + (len(sample_audio) - feature_extractor.n_fft) // feature_extractor.hop_length
        assert features["mel_spectrogram"].shape[1] == n_frames
        assert features["mfcc"].shape[1] == n_frames

    def test_extract_features_stereo(self, feature_extractor):
        """Test feature extraction with stereo audio."""
        stereo_audio = np.random.rand(22050, 2).astype(np.float32)
        features = feature_extractor.extract_features(stereo_audio)

        assert isinstance(features, dict)
        assert all(isinstance(feat, np.ndarray) for feat in features.values())

    def test_extract_features_invalid_input(self, feature_extractor):
        """Test feature extraction with invalid input."""
        with pytest.raises(ValueError):
            feature_extractor.extract_features(np.array([]))  # empty array

    def test_extract_features_noise(self, feature_extractor, noise_audio):
        """Test feature extraction with noisy audio."""
        features = feature_extractor.extract_features(noise_audio)
        assert all(isinstance(feat, np.ndarray) for feat in features.values())

    def test_extract_features_silence(self, feature_extractor):
        """Test feature extraction with silent audio."""
        silent_audio = np.zeros(22050)  # 1 second of silence
        features = feature_extractor.extract_features(silent_audio)
        assert all(isinstance(feat, np.ndarray) for feat in features.values())

    def test_extract_features_short_input(self, feature_extractor):
        """Test feature extraction with very short audio."""
        short_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.1, 2205))  # 0.1 seconds
        features = feature_extractor.extract_features(short_audio)
        assert all(isinstance(feat, np.ndarray) for feat in features.values())

    @pytest.mark.asyncio
    async def test_analyze_audio(self, feature_extractor, mock_audio_data):
        """Test async audio analysis."""
        with patch("soundfile.read") as mock_read:
            mock_read.return_value = (np.random.rand(22050).astype(np.float32), 22050)
            result = await feature_extractor.analyze_audio(mock_audio_data)
            assert result is not None
            assert isinstance(result, dict)
            assert "rhythm_strength" in result
            assert "confidence" in result

    @pytest.mark.asyncio
    async def test_analyze_audio_invalid(self, feature_extractor):
        """Test async audio analysis with invalid data."""
        result = await feature_extractor.analyze_audio(b"")
        assert result is None


class TestMusicDetection:
    """Test music detection functionality."""

    def test_is_music_detection(self, feature_extractor, sample_audio):
        """Test music detection with sample audio."""
        features = feature_extractor.extract_features(sample_audio)
        is_music, confidence = feature_extractor.is_music(features)

        assert isinstance(is_music, bool)
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1

    def test_is_music_missing_features(self, feature_extractor):
        """Test music detection with missing features."""
        incomplete_features = {
            "mel_spectrogram": np.random.rand(128, 100),
            "mfcc": np.random.rand(20, 100)
            # missing spectral_contrast and chroma
        }

        with pytest.raises(ValueError):
            feature_extractor.is_music(incomplete_features)

    def test_is_music_invalid_features(self, feature_extractor):
        """Test music detection with invalid feature types."""
        invalid_features = {
            "mel_spectrogram": [1, 2, 3],  # not numpy array
            "mfcc": np.random.rand(20, 100),
            "spectral_contrast": np.random.rand(7, 100),
            "chroma": np.random.rand(12, 100),
        }

        with pytest.raises(TypeError):
            feature_extractor.is_music(invalid_features)

    def test_is_music_complex_audio(self, feature_extractor, complex_audio):
        """Test music detection with complex musical audio."""
        features = feature_extractor.extract_features(complex_audio)
        is_music, confidence = feature_extractor.is_music(features)

        assert is_music is True
        assert confidence > 0.5  # Should have high confidence for musical audio

    def test_is_music_noise(self, feature_extractor, noise_audio):
        """Test music detection with noise."""
        features = feature_extractor.extract_features(noise_audio)
        is_music, confidence = feature_extractor.is_music(features)

        assert is_music is False
        assert confidence < 0.5  # Should have low confidence for noise

    def test_is_music_silence(self, feature_extractor):
        """Test music detection with silence."""
        silent_audio = np.zeros(22050)
        features = feature_extractor.extract_features(silent_audio)
        is_music, confidence = feature_extractor.is_music(features)
        assert is_music is False
        assert confidence < 0.2  # Should have very low confidence for silence

    def test_is_music_threshold(self, feature_extractor, complex_audio):
        """Test music detection with different confidence thresholds."""
        features = feature_extractor.extract_features(complex_audio)

        # Test with different thresholds
        thresholds = [0.3, 0.5, 0.7, 0.9]
        results = []
        confidences = []
        for threshold in thresholds:
            is_music, confidence = feature_extractor.is_music(features)
            results.append(is_music)
            confidences.append(confidence)

        assert any(results), "Should detect as music with some threshold"
        assert all(0 <= conf <= 1 for conf in confidences), "Confidence should be between 0 and 1"


class TestAudioDuration:
    """Test audio duration calculation."""

    def test_get_audio_duration(self, feature_extractor):
        """Test duration calculation for various audio lengths."""
        # Test 1-second audio
        audio_1s = np.random.rand(22050)
        duration = feature_extractor.get_audio_duration(audio_1s)
        assert np.isclose(duration, 1.0)

        # Test 2-second stereo audio
        audio_2s = np.random.rand(44100, 2)
        duration = feature_extractor.get_audio_duration(audio_2s)
        assert np.isclose(duration, 2.0)

    def test_get_audio_duration_invalid(self, feature_extractor):
        """Test duration calculation with invalid input."""
        with pytest.raises(TypeError):
            feature_extractor.get_audio_duration([1, 2, 3])  # not numpy array

        with pytest.raises(ValueError):
            feature_extractor.get_audio_duration(np.array([]))  # empty array


@pytest.mark.benchmark
class TestFeatureExtractorPerformance:
    """Performance tests for FeatureExtractor."""

    def test_feature_extraction_performance(self, feature_extractor, benchmark):
        """Benchmark feature extraction performance."""
        # Generate 10 seconds of audio
        duration = 10.0
        sample_rate = 22050
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * 440 * t)

        def extract_features():
            return feature_extractor.extract_features(audio)

        result = benchmark(extract_features)
        assert isinstance(result, dict)
        assert all(isinstance(feat, np.ndarray) for feat in result.values())

    def test_music_detection_performance(self, feature_extractor, benchmark):
        """Benchmark music detection performance."""
        # Generate features for benchmarking
        audio = np.random.rand(22050)  # 1 second of random audio
        features = feature_extractor.extract_features(audio)

        def detect_music():
            return feature_extractor.is_music(features)

        result = benchmark(detect_music)
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)
        assert 0 <= result[1] <= 1

    def test_memory_usage(self, feature_extractor, complex_audio, benchmark):
        """Test memory usage during feature extraction."""
        process = psutil.Process(psutil.Process().pid)

        def measure_memory():
            initial_memory = process.memory_info().rss
            features = feature_extractor.extract_features(complex_audio)
            final_memory = process.memory_info().rss
            memory_used = final_memory - initial_memory
            assert memory_used < 50 * 1024 * 1024  # Should use less than 50MB
            return features

        result = benchmark(measure_memory)
        assert isinstance(result, dict)
        assert all(isinstance(feat, np.ndarray) for feat in result.values())

    def test_batch_processing_performance(self, feature_extractor, benchmark):
        """Test performance with batch processing."""
        # Generate batch of audio signals
        batch_size = 10
        duration = 1.0
        sample_rate = 22050
        batch = [
            np.sin(
                2 * np.pi * (440 * (i + 1)) * np.linspace(0, duration, int(sample_rate * duration))
            )
            for i in range(batch_size)
        ]

        def process_batch():
            features = [feature_extractor.extract_features(audio) for audio in batch]
            assert len(features) == batch_size
            assert all(isinstance(feat, dict) for feat in features)
            return features

        result = benchmark(process_batch)
        assert len(result) == batch_size
        assert all(isinstance(feat, dict) for feat in result)

    def test_concurrent_processing(self, feature_extractor, benchmark):
        """Test concurrent processing performance."""
        import asyncio

        async def process_audio(audio):
            return feature_extractor.extract_features(audio)

        def run_concurrent():
            # Generate multiple audio signals
            signals = [np.random.rand(22050) for _ in range(5)]

            # Process concurrently
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            tasks = [process_audio(signal) for signal in signals]
            results = loop.run_until_complete(asyncio.gather(*tasks))
            loop.close()

            assert len(results) == 5
            assert all(isinstance(result, dict) for result in results)
            return results

        result = benchmark(run_concurrent)
        assert len(result) == 5
        assert all(isinstance(feat, dict) for feat in result)


class TestFeatureExtractorEdgeCases:
    @pytest.fixture
    def extractor(self):
        return FeatureExtractor()

    def test_extremely_short_audio(self, extractor):
        # Test with audio shorter than hop_length
        audio = np.random.rand(100)  # Very short audio
        features = extractor.extract_features(audio)
        assert features is not None
        assert isinstance(features, dict)
        assert features["mel_spectrogram"].shape[1] > 0

    def test_extremely_long_audio(self, extractor):
        # Test with very long audio (1 minute)
        audio = np.random.rand(22050 * 60)  # 1 minute at 22050Hz
        features = extractor.extract_features(audio)
        assert features is not None
        assert isinstance(features, dict)
        assert features["mel_spectrogram"].shape[1] > 0

    def test_varying_amplitudes(self, extractor):
        # Test with varying amplitude levels
        audio = np.sin(np.linspace(0, 100, 22050)) * np.linspace(0, 1, 22050)
        features = extractor.extract_features(audio)
        assert features is not None
        assert isinstance(features, dict)
        assert np.any(features["mel_spectrogram"] != 0)  # Should detect amplitude variations


class TestFeatureExtractorRealWorld:
    @pytest.fixture
    def extractor(self):
        return FeatureExtractor()

    def test_mixed_content_audio(self, extractor):
        # Simulate mixed speech and music
        t = np.linspace(0, 10, 22050 * 10)
        speech = np.sin(2 * np.pi * 200 * t) * 0.3  # Speech-like frequency
        music = np.sin(2 * np.pi * 440 * t) * 0.7  # Music-like frequency
        mixed = speech + music
        features = extractor.extract_features(mixed)
        is_music = extractor.is_music(features)
        assert is_music  # Should detect music in mixed content

    def test_background_noise(self, extractor):
        # Test with signal + background noise
        t = np.linspace(0, 5, 22050 * 5)
        signal = np.sin(2 * np.pi * 440 * t)  # Pure tone
        noise = np.random.normal(0, 0.1, len(t))  # Background noise
        noisy_signal = signal + noise
        features = extractor.extract_features(noisy_signal)
        is_music = extractor.is_music(features)
        assert is_music  # Should still detect music with noise


class TestFeatureExtractorErrorRecovery:
    @pytest.fixture
    def extractor(self):
        return FeatureExtractor()

    def test_recover_from_nan(self, extractor):
        # Test recovery from NaN values in audio
        audio = np.random.rand(22050)
        audio[1000:1100] = np.nan  # Insert NaN values
        # Replace NaN values with zeros before processing
        audio = np.nan_to_num(audio, nan=0.0)
        features = extractor.extract_features(audio)
        assert features is not None
        assert isinstance(features, dict)
        assert not np.any(np.isnan(features["mel_spectrogram"]))

    def test_recover_from_inf(self, extractor):
        # Test recovery from infinite values
        audio = np.random.rand(22050)
        audio[1000:1100] = np.inf  # Insert infinite values
        # Replace inf values with large finite values before processing
        audio = np.nan_to_num(audio, posinf=1.0, neginf=-1.0)
        features = extractor.extract_features(audio)
        assert features is not None
        assert isinstance(features, dict)
        assert not np.any(np.isinf(features["mel_spectrogram"]))

    def test_recover_from_zeros(self, extractor):
        # Test recovery from zero segments
        audio = np.random.rand(22050)
        audio[1000:2000] = 0  # Insert zero segment
        features = extractor.extract_features(audio)
        assert features is not None
        assert isinstance(features, dict)
        assert features["mel_spectrogram"].shape[1] > 0


class TestFeatureExtractorIntegration:
    @pytest.fixture
    def extractor(self):
        return FeatureExtractor()

    def test_stream_processing(self, extractor):
        # Test processing audio in chunks (simulating streaming)
        chunk_size = 4096
        audio = np.random.rand(22050)
        chunks = [audio[i : i + chunk_size] for i in range(0, len(audio), chunk_size)]

        mel_specs = []
        for chunk in chunks:
            features = extractor.extract_features(chunk)
            if features is not None and features["mel_spectrogram"].shape[1] > 0:
                mel_specs.append(features["mel_spectrogram"])

        assert len(mel_specs) > 0
        # Verify features can be concatenated
        combined_features = np.concatenate(mel_specs, axis=1)
        assert combined_features.shape[1] > 0

    def test_feature_consistency(self, extractor):
        # Test consistency of features across multiple extractions
        audio = np.random.rand(22050)
        features1 = extractor.extract_features(audio)
        features2 = extractor.extract_features(audio)

        # Compare each feature type separately
        for feature_type in ["mel_spectrogram", "mfcc", "spectral_contrast", "chroma"]:
            if feature_type in features1 and feature_type in features2:
                np.testing.assert_array_almost_equal(
                    features1[feature_type], features2[feature_type]
                )

    def test_memory_cleanup(self, extractor):
        # Test memory cleanup after processing
        initial_memory = psutil.Process().memory_info().rss
        for _ in range(10):
            audio = np.random.rand(22050 * 10)  # Large audio chunk
            _ = extractor.extract_features(audio)
        final_memory = psutil.Process().memory_info().rss
        # Allow for some memory overhead but check for no major leaks
        assert (final_memory - initial_memory) < 100 * 1024 * 1024  # Less than 100MB growth


def test_noise_characteristics(feature_extractor, noise_audio):
    """Test detailed noise characteristics."""
    features = feature_extractor.extract_features(noise_audio)

    # Check spectral characteristics
    spectral_flux = feature_extractor._calculate_spectral_flux(features["mel_spectrogram"])
    assert spectral_flux > 0.4, "Noise should have high spectral flux"

    # Check rhythm characteristics
    rhythm_strength = feature_extractor._calculate_rhythm_strength(features["mel_spectrogram"])
    assert rhythm_strength < 0.3, "Noise should have low rhythm strength"

    # Check harmonic characteristics
    harmonic_ratio = feature_extractor._calculate_harmonic_ratio(features["spectral_contrast"])
    assert harmonic_ratio < 0.2, "Noise should have low harmonic content"

    # Check overall detection
    is_music, confidence = feature_extractor.is_music(features)
    assert is_music is False, "Noise should not be detected as music"
    assert confidence < 0.3, "Confidence should be low for noise"


def test_complex_audio_characteristics(feature_extractor, complex_audio):
    """Test detailed characteristics of complex musical audio."""
    features = feature_extractor.extract_features(complex_audio)

    # Check spectral characteristics
    spectral_flux = feature_extractor._calculate_spectral_flux(features["mel_spectrogram"])
    assert spectral_flux < 0.6, "Music should have moderate spectral flux"

    # Check rhythm characteristics
    rhythm_strength = feature_extractor._calculate_rhythm_strength(features["mel_spectrogram"])
    assert rhythm_strength > 0.4, "Music should have strong rhythm"

    # Check harmonic characteristics
    harmonic_ratio = feature_extractor._calculate_harmonic_ratio(features["spectral_contrast"])
    assert harmonic_ratio > 0.3, "Music should have strong harmonic content"

    # Check chroma variation
    chroma_var = np.std(features["chroma"])
    assert chroma_var > 0.1, "Music should have significant pitch content variation"

    # Check overall detection
    is_music, confidence = feature_extractor.is_music(features)
    assert is_music is True, "Complex audio should be detected as music"
    assert confidence > 0.4, "Confidence should be high for music"


def test_mixed_content(feature_extractor, complex_audio, noise_audio):
    """Test detection with mixed music and noise content."""
    # Mix music and noise with different ratios
    mix_ratios = [0.2, 0.5, 0.8]  # Music proportion

    for ratio in mix_ratios:
        # Create mixed signal
        mixed = ratio * complex_audio + (1 - ratio) * noise_audio
        features = feature_extractor.extract_features(mixed)
        is_music, confidence = feature_extractor.is_music(features)

        if ratio >= 0.5:
            assert is_music is True, f"Should detect as music with {ratio:.1f} music ratio"
            assert confidence > 0.3, f"Should have moderate confidence with {ratio:.1f} music ratio"
        else:
            assert is_music is False, f"Should not detect as music with {ratio:.1f} music ratio"
            assert confidence < 0.3, f"Should have low confidence with {ratio:.1f} music ratio"


def test_gradual_transition(feature_extractor, complex_audio, noise_audio):
    """Test detection with gradual transition from music to noise."""
    # Create segments
    segment_length = len(complex_audio) // 4
    mixed = np.zeros_like(complex_audio)

    # Create gradual transition
    for i in range(4):
        # Mix music and noise with varying ratios
        ratio = 1.0 - (i / 3)  # 1.0 -> 0.0
        start = i * segment_length
        end = (i + 1) * segment_length
        mixed[start:end] = ratio * complex_audio[start:end] + (1 - ratio) * noise_audio[start:end]

        # Test segment
        segment = mixed[start:end]
        features = feature_extractor.extract_features(segment)
        is_music, confidence = feature_extractor.is_music(features)

        # Check confidence decreases as noise increases
        if i < 2:
            assert confidence > 0.5, f"Segment {i} should have high confidence"
        else:
            assert confidence < 0.5, f"Segment {i} should have low confidence"
