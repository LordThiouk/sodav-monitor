import requests
import logging
from typing import Dict, Any, Optional, Tuple
import io
from pydub import AudioSegment
import os
from dotenv import load_dotenv
import numpy as np
import librosa
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('music_recognition.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class MusicRecognizer:
    def __init__(self, audd_api_key: Optional[str] = None):
        """Initialize music recognizer with API key"""
        self.audd_api_key = audd_api_key or os.getenv('AUDD_API_KEY')
        logger.info("Initializing MusicRecognizer")
        
        if not self.audd_api_key:
            logger.warning("AudD API key not found")
    
    def _analyze_audio_features(self, audio_data: bytes) -> Dict[str, float]:
        """
        Analyze audio features to determine if the content is music or speech
        Returns dict with features and likelihood scores
        """
        try:
            # Convert audio bytes to numpy array
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            
            # Convert to mono if stereo
            if audio.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            
            # Normalize samples
            samples = samples / np.max(np.abs(samples))
            
            # Get sample rate
            sample_rate = audio.frame_rate
            
            # Calculate features
            # Spectral Centroid - higher for music, lower for speech
            cent = librosa.feature.spectral_centroid(y=samples, sr=sample_rate)[0]
            
            # RMS Energy - music typically has more consistent energy
            rms = librosa.feature.rms(y=samples)[0]
            
            # Zero Crossing Rate - typically higher for speech
            zcr = librosa.feature.zero_crossing_rate(samples)[0]
            
            # Spectral Rolloff - typically higher for music
            rolloff = librosa.feature.spectral_rolloff(y=samples, sr=sample_rate)[0]
            
            # Calculate averages
            features = {
                'spectral_centroid_mean': float(np.mean(cent)),
                'rms_energy_std': float(np.std(rms)),  # Variation in energy
                'zero_crossing_rate_mean': float(np.mean(zcr)),
                'spectral_rolloff_mean': float(np.mean(rolloff)),
            }
            
            # Calculate music likelihood score (0-100)
            # Higher centroid, consistent energy, lower ZCR, higher rolloff = more likely to be music
            music_score = (
                (min(features['spectral_centroid_mean'] / 5000, 1.0) * 25) +  # 25% weight
                (max(1 - features['rms_energy_std'] * 10, 0.0) * 25) +  # 25% weight
                (max(1 - features['zero_crossing_rate_mean'] * 100, 0.0) * 25) +  # 25% weight
                (min(features['spectral_rolloff_mean'] / 12000, 1.0) * 25)  # 25% weight
            )
            
            features['music_likelihood'] = min(100, max(0, music_score))
            return features
            
        except Exception as e:
            logger.error(f"Error analyzing audio features: {str(e)}", exc_info=True)
            return {'music_likelihood': 50}  # Default to uncertain if analysis fails
    
    def recognize_from_audio_data(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Recognize music from audio data using AudD service
        """
        try:
            logger.info("Starting music recognition process")
            logger.debug(f"Received {len(audio_data)} bytes of audio data")
            
            # Prepare request data
            data = {
                'api_token': self.audd_api_key,
                'return': 'spotify,deezer,musicbrainz'
            }
            
            files = {
                'file': ('audio.mp3', audio_data, 'audio/mpeg')
            }
            
            # Make recognition request
            response = requests.post('https://api.audd.io/', data=data, files=files)
            logger.debug(f"AudD API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"AudD API error: {response.status_code}")
                return {"error": f"API error: {response.status_code}"}
            
            result = response.json()
            logger.debug(f"AudD API response: {result}")
            
            if result.get('status') == 'success' and result.get('result'):
                song = result['result']
                logger.info(f"Song detected: {song.get('title')} by {song.get('artist')}")
                
                # Extract metadata
                spotify_data = song.get('spotify', {})
                if isinstance(spotify_data, list) and len(spotify_data) > 0:
                    spotify_data = spotify_data[0]
                
                deezer_data = song.get('deezer', {})
                if isinstance(deezer_data, list) and len(deezer_data) > 0:
                    deezer_data = deezer_data[0]
                
                musicbrainz_data = song.get('musicbrainz', {})
                if isinstance(musicbrainz_data, list) and len(musicbrainz_data) > 0:
                    musicbrainz_data = musicbrainz_data[0]
                
                return {
                    "title": song.get('title'),
                    "artist": song.get('artist'),
                    "album": song.get('album'),
                    "isrc": musicbrainz_data.get('isrc') if isinstance(musicbrainz_data, dict) else None,
                    "confidence": 100,  # AudD doesn't provide confidence, assume 100 if match found
                    "detected_at": datetime.now().isoformat(),
                    "external_metadata": {
                        "spotify": spotify_data,
                        "deezer": deezer_data,
                        "musicbrainz": musicbrainz_data
                    }
                }
            else:
                logger.info("No music detected")
                return {"error": "No music detected"}
                
        except Exception as e:
            logger.error(f"Error in music recognition: {str(e)}", exc_info=True)
            return {"error": str(e)}
