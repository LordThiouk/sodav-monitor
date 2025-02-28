"""Real-world scenario tests for the FeatureExtractor."""

import pytest
import numpy as np
import soundfile as sf
from backend.detection.audio_processor.feature_extractor import FeatureExtractor

@pytest.mark.real_world
class TestRealWorldScenarios:
    """Test FeatureExtractor with real-world audio samples."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up FeatureExtractor instance."""
        self.extractor = FeatureExtractor()
    
    @pytest.mark.asyncio
    async def test_music_detection(self, test_audio_files):
        """Test music detection with real music samples."""
        # Read music file
        audio_data, _ = sf.read(test_audio_files["music"])
        with open(test_audio_files["music"], 'rb') as f:
            audio_bytes = f.read()
            
        # Test feature extraction
        features = self.extractor.extract_features(audio_data)
        
        # Check if features is a dictionary
        assert features is not None, "Features should not be None"
        assert isinstance(features, dict), "Features should be a dictionary"
        
        # Check for required keys
        required_keys = ["mel_spectrogram", "mfcc", "spectral_contrast", "chroma"]
        missing_keys = [key for key in required_keys if key not in features]
        assert not missing_keys, f"Missing required features: {missing_keys}"
        
        # Test music detection
        is_music, confidence = self.extractor.is_music(features)
        
        # Check music detection result
        assert is_music == True, f"Expected music detection to be True, got {is_music} with confidence {confidence}"
        assert confidence >= 0.7, f"Expected confidence >= 0.7, got {confidence}"
        
        # Test full analysis pipeline
        analysis = await self.extractor.analyze_audio(audio_bytes)
        
        # Check analysis results
        assert analysis is not None, "Analysis should not be None"
        assert analysis["music_confidence"] >= 0.7, f"Expected analysis music_confidence >= 0.7, got {analysis['music_confidence']}"
    
    @pytest.mark.asyncio
    async def test_speech_detection(self, test_audio_files):
        """Test speech detection with real speech samples."""
        # Read speech file
        audio_data, _ = sf.read(test_audio_files["speech"])
        with open(test_audio_files["speech"], 'rb') as f:
            audio_bytes = f.read()
            
        # Test feature extraction
        features = self.extractor.extract_features(audio_data)
        
        # Test music detection (should identify as non-music)
        is_music, confidence = self.extractor.is_music(features)
        assert is_music is False
        assert confidence < 0.5  # Lower confidence for speech
        
        # Test full analysis pipeline
        analysis = await self.extractor.analyze_audio(audio_bytes)
        assert analysis is not None
        assert analysis["confidence"] < 0.5
    
    @pytest.mark.asyncio
    async def test_noise_handling(self, test_audio_files):
        """Test handling of noise audio."""
        # Read noise file
        audio_data, _ = sf.read(test_audio_files["noise"])
        with open(test_audio_files["noise"], 'rb') as f:
            audio_bytes = f.read()
            
        # Test feature extraction
        features = self.extractor.extract_features(audio_data)
        
        # Test music detection (should identify as non-music)
        is_music, confidence = self.extractor.is_music(features)
        assert is_music is False
        assert confidence < 0.3  # Very low confidence for noise
        
        # Test full analysis pipeline
        analysis = await self.extractor.analyze_audio(audio_bytes)
        assert analysis is not None
        assert analysis["confidence"] < 0.3
    
    @pytest.mark.asyncio
    async def test_silence_handling(self, test_audio_files):
        """Test handling of silence."""
        # Read silence file
        audio_data, _ = sf.read(test_audio_files["silence"])
        with open(test_audio_files["silence"], 'rb') as f:
            audio_bytes = f.read()
            
        # Test feature extraction
        features = self.extractor.extract_features(audio_data)
        
        # Test music detection (should identify as non-music)
        is_music, confidence = self.extractor.is_music(features)
        assert is_music is False
        assert confidence < 0.1  # Extremely low confidence for silence
        
        # Test full analysis pipeline
        analysis = await self.extractor.analyze_audio(audio_bytes)
        assert analysis is not None
        assert analysis["confidence"] < 0.1
    
    def test_feature_consistency(self, test_audio_files):
        """Test consistency of feature extraction across multiple runs."""
        audio_data, _ = sf.read(test_audio_files["music"])
        
        # Extract features multiple times
        features1 = self.extractor.extract_features(audio_data)
        features2 = self.extractor.extract_features(audio_data)
        
        # Compare features
        for key in features1:
            if isinstance(features1[key], np.ndarray):
                np.testing.assert_array_almost_equal(features1[key], features2[key])
            else:
                assert features1[key] == features2[key]
    
    @pytest.mark.asyncio
    async def test_processing_time(self, test_audio_files):
        """Test processing time for different audio types."""
        import time
        
        async def measure_processing_time(file_path):
            with open(file_path, 'rb') as f:
                audio_bytes = f.read()
            start_time = time.time()
            await self.extractor.analyze_audio(audio_bytes)
            return time.time() - start_time
        
        # Test processing time for each audio type
        processing_times = {}
        for audio_type, file_path in test_audio_files.items():
            processing_time = await measure_processing_time(file_path)
            processing_times[audio_type] = processing_time
            
            # Processing should take less than 1 second for 3-second audio
            assert processing_time < 1.0, f"Processing {audio_type} took too long: {processing_time:.2f}s" 