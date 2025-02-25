import numpy as np
import io
from pydub import AudioSegment
from typing import Dict, Any, Optional
import logging
from scipy import signal
import librosa
import soundfile as sf
from ..models.models import Track, TrackDetection
from datetime import datetime, timedelta
import asyncio
import aiohttp
import tempfile
import os

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self, acoustid_api_key: Optional[str] = None, audd_api_key: Optional[str] = None):
        """Initialize audio processor with API keys for music recognition services"""
        self.acoustid_api_key = acoustid_api_key
        self.audd_api_key = audd_api_key
    
    def detect_track(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Detect if audio contains music and identify the track
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            Dictionary containing detection results and track information
        """
        try:
            from .music_recognition import MusicRecognizer
            
            logger.info("Converting audio data...")
            # Convert audio to numpy array for analysis
            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            samples = np.array(audio.get_array_of_samples())
            
            logger.info(f"Audio properties: {audio.channels} channels, {audio.frame_rate}Hz, {len(samples)} samples")
            
            # Analyze audio characteristics
            analysis = self._analyze_audio(samples, audio.frame_rate, audio.channels)
            
            # Determine if music is playing based on analysis
            is_music = self._is_music_playing(analysis)
            
            logger.info(f"Music detection results:")
            logger.info(f"Is music: {is_music}")
            logger.info(f"Confidence: {analysis['music_confidence']:.2f}%")
            logger.info(f"Bass energy: {analysis['frequency_distribution']['low']:.2f}%")
            logger.info(f"Mid energy: {analysis['frequency_distribution']['mid']:.2f}%")
            logger.info(f"High energy: {analysis['frequency_distribution']['high']:.2f}%")
            logger.info(f"Rhythm strength: {analysis['rhythm_strength']:.2f}%")
            
            result = {
                "is_music": is_music,
                "confidence": analysis["music_confidence"],
                "analysis": analysis
            }
            
            # If we're confident it's music, try to identify the track
            if is_music and analysis["music_confidence"] > 60:
                logger.info("Attempting to identify track...")
                recognizer = MusicRecognizer(self.acoustid_api_key, self.audd_api_key)
                track_info = recognizer.recognize_from_audio_data(audio_data)
                if "error" not in track_info:
                    logger.info(f"Track identified: {track_info.get('title')} by {track_info.get('artist')}")
                    result["track_info"] = track_info
                else:
                    logger.warning(f"Track identification failed: {track_info.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting track: {str(e)}")
            return {
                "error": str(e),
                "is_music": False,
                "confidence": 0
            }
    
    def _analyze_audio(self, samples: np.ndarray, sample_rate: int, channels: int) -> Dict[str, Any]:
        """Analyze audio characteristics"""
        try:
            # Convert to mono if stereo
            if channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            
            # Normalize samples
            samples = samples / np.iinfo(samples.dtype).max
            
            # Apply pre-emphasis filter
            pre_emphasis = 0.97
            emphasized_samples = np.append(samples[0], samples[1:] - pre_emphasis * samples[:-1])
            
            # Calculate spectrogram
            frequencies, times, spectrogram = signal.spectrogram(
                emphasized_samples,
                fs=sample_rate,
                nperseg=2048,
                noverlap=1024,
                window='hann'
            )
            
            # Calculate average magnitude for each frequency band
            bass_mask = frequencies < 250
            mid_mask = (frequencies >= 250) & (frequencies < 4000)
            high_mask = frequencies >= 4000
            
            bass_energy = np.mean(np.mean(spectrogram[bass_mask], axis=1)) * 100
            mid_energy = np.mean(np.mean(spectrogram[mid_mask], axis=1)) * 100
            high_energy = np.mean(np.mean(spectrogram[high_mask], axis=1)) * 100
            
            total_energy = bass_energy + mid_energy + high_energy
            if total_energy > 0:
                bass_energy = (bass_energy / total_energy) * 100
                mid_energy = (mid_energy / total_energy) * 100
                high_energy = (high_energy / total_energy) * 100
            
            # Detect rhythm
            rhythm_strength = self._detect_rhythm_strength(emphasized_samples, sample_rate)
            
            # Calculate spectral flux
            spectral_flux = np.mean(np.diff(np.sum(spectrogram, axis=0)))
            
            # Calculate spectral centroid
            spectral_centroid = np.sum(frequencies[:, np.newaxis] * spectrogram, axis=0) / np.sum(spectrogram, axis=0)
            spectral_centroid_var = np.var(spectral_centroid)
            
            # Calculate music confidence
            music_confidence = self._calculate_music_confidence(
                bass_energy, mid_energy, high_energy, rhythm_strength,
                spectral_flux, spectral_centroid_var
            )
            
            return {
                "frequency_distribution": {
                    "low": bass_energy,
                    "mid": mid_energy,
                    "high": high_energy
                },
                "rhythm_strength": rhythm_strength,
                "spectral_features": {
                    "flux": float(spectral_flux),
                    "centroid_variance": float(spectral_centroid_var)
                },
                "music_confidence": music_confidence,
                "audio_quality": {
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "duration": len(samples) / sample_rate
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing audio: {str(e)}")
            return {
                "frequency_distribution": {"low": 0, "mid": 0, "high": 0},
                "rhythm_strength": 0,
                "spectral_features": {"flux": 0, "centroid_variance": 0},
                "music_confidence": 0,
                "audio_quality": {
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "duration": 0
                }
            }
    
    def _detect_rhythm_strength(self, samples: np.ndarray, sample_rate: int) -> float:
        """
        Detect rhythm strength in audio using onset detection
        Returns value between 0-100
        """
        try:
            # Calculate onset envelope using spectral flux
            hop_length = 512
            frame_length = 2048
            
            # Calculate STFT
            stft = np.abs(signal.stft(
                samples,
                nperseg=frame_length,
                noverlap=frame_length - hop_length,
                window='hann'
            )[2])
            
            # Calculate spectral flux
            onset_env = np.sum(np.diff(stft, axis=1), axis=0)
            onset_env = np.maximum(onset_env, 0)
            
            if len(onset_env) == 0:
                return 0
            
            # Normalize
            onset_env = onset_env / np.max(onset_env)
            
            # Calculate tempo and onset strength
            tempo_frame = 10  # seconds
            frame_samples = int(tempo_frame * sample_rate / hop_length)
            if len(onset_env) >= frame_samples:
                onset_env = onset_env[:frame_samples]
            
            # Calculate autocorrelation
            ac = signal.correlate(onset_env, onset_env, mode='full')
            ac = ac[len(ac)//2:]
            
            # Find peaks in autocorrelation
            peaks, properties = signal.find_peaks(
                ac,
                distance=20,
                prominence=0.05
            )
            
            if len(peaks) == 0:
                return 0
            
            # Calculate rhythm strength based on peak prominences
            prominences = properties['prominences']
            rhythm_strength = np.mean(prominences) * 100
            
            return min(100, max(0, rhythm_strength))
            
        except Exception as e:
            logger.error(f"Error detecting rhythm: {str(e)}")
            return 0
    
    def _calculate_music_confidence(self, bass: float, mid: float, high: float,
                                 rhythm: float, spectral_flux: float,
                                 spectral_centroid_var: float) -> float:
        """
        Calculate confidence that audio contains music
        Returns value between 0-100
        """
        try:
            # Weights for different factors
            weights = {
                "bass": 0.25,
                "mid": 0.15,
                "high": 0.1,
                "rhythm": 0.3,
                "spectral_flux": 0.1,
                "spectral_variance": 0.1
            }
            
            # Normalize spectral features
            spectral_flux_norm = min(100, spectral_flux * 100)
            spectral_var_norm = min(100, spectral_centroid_var / 1000)
            
            # Calculate frequency balance score (penalize if too unbalanced)
            freq_balance = 100 - (
                abs(bass - 33.3) +
                abs(mid - 33.3) +
                abs(high - 33.3)
            ) / 3
            
            # Combined score
            confidence = (
                weights["bass"] * bass +
                weights["mid"] * mid +
                weights["high"] * high +
                weights["rhythm"] * rhythm +
                weights["spectral_flux"] * spectral_flux_norm +
                weights["spectral_variance"] * spectral_var_norm
            )
            
            # Adjust based on frequency balance
            confidence = (confidence * 0.7 + freq_balance * 0.3)
            
            # Additional boost if strong rhythm and balanced spectrum
            if rhythm > 70 and freq_balance > 60:
                confidence *= 1.2
            
            return min(100, max(0, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating music confidence: {str(e)}")
            return 0
    
    def _is_music_playing(self, analysis: Dict[str, Any]) -> bool:
        """Determine if audio contains music based on analysis results"""
        try:
            confidence = analysis["music_confidence"]
            rhythm = analysis["rhythm_strength"]
            freq_dist = analysis["frequency_distribution"]
            
            # More sophisticated music detection criteria
            is_music = (
                confidence > 50 and  # Overall confidence
                rhythm > 30 and      # Some rhythmic content
                freq_dist["low"] > 20 and  # Sufficient bass
                freq_dist["mid"] > 15      # Sufficient mids
            )
            
            return is_music
            
        except Exception as e:
            logger.error(f"Error in music detection: {str(e)}")
            return False
    
    def lookup_isrc(self, isrc: str) -> Dict[str, Any]:
        """Look up song details by ISRC code"""
        from .music_recognition import MusicRecognizer
        recognizer = MusicRecognizer(self.acoustid_api_key, self.audd_api_key)
        return recognizer.get_song_details(isrc)

__all__ = ['AudioProcessor']
