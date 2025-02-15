import musicbrainzngs
import logging
from typing import Dict, Any, Optional
import io
from pydub import AudioSegment
import os
from datetime import datetime
from config import Config
import librosa
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class MusicBrainzRecognizer:
    def __init__(self):
        """Initialize MusicBrainz recognizer"""
        # Set up MusicBrainz
        musicbrainzngs.set_useragent(
            Config.MUSICBRAINZ_APP_NAME,
            "1.0",
            "https://github.com/LordThiouk/sodav-monitor"
        )
    
    def _analyze_audio_features(self, audio_data: bytes) -> Dict[str, float]:
        """
        Analyze audio features to determine if the content is music
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
            
            # Calculate statistics
            features = {
                "centroid_mean": float(np.mean(cent)),
                "centroid_std": float(np.std(cent)),
                "rms_mean": float(np.mean(rms)),
                "rms_std": float(np.std(rms)),
                "zcr_mean": float(np.mean(zcr)),
                "zcr_std": float(np.std(zcr))
            }
            
            # Calculate music likelihood score (0-100)
            # Higher centroid mean and RMS with lower variance typically indicates music
            music_score = (
                (features["centroid_mean"] / 5000) * 30 +  # Up to 30 points for high centroid
                (1 - features["centroid_std"] / features["centroid_mean"]) * 20 +  # Up to 20 points for consistent centroid
                (features["rms_mean"] * 100) * 30 +  # Up to 30 points for high RMS
                (1 - features["zcr_mean"]) * 20  # Up to 20 points for low zero crossing rate
            )
            
            # Clip score to 0-100 range
            music_score = max(0, min(100, music_score))
            features["music_likelihood"] = music_score
            
            return features
            
        except Exception as e:
            logger.error(f"Error analyzing audio features: {str(e)}")
            return {"error": str(e)}
    
    def recognize_from_audio_data(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Analyze audio and search MusicBrainz if it appears to be music
        """
        try:
            logger.info("Starting music recognition process")
            
            # First analyze audio features
            features = self._analyze_audio_features(audio_data)
            
            if "error" in features:
                return {"error": f"Failed to analyze audio: {features['error']}"}
            
            music_likelihood = features.get("music_likelihood", 0)
            logger.info(f"Music likelihood score: {music_likelihood}")
            
            if music_likelihood < 60:  # Threshold for music detection
                return {"error": "Audio does not appear to be music"}
            
            # Load audio for fingerprinting
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            duration_ms = len(audio)  # Get duration in milliseconds
            duration_minutes = duration_ms / 1000 / 60  # Convert to minutes
            
            # Convert to WAV for fingerprinting
            wav_data = io.BytesIO()
            audio.export(wav_data, format="wav")
            wav_data.seek(0)
            
            # Generate fingerprint using acoustid
            import acoustid
            try:
                if not Config.ACOUSTID_API_KEY:
                    raise ValueError("ACOUSTID_API_KEY not set in environment. Please get an API key from https://acoustid.org/api-key")
                    
                duration, fingerprint = acoustid.fingerprint_file(wav_data)
                matches = acoustid.lookup(Config.ACOUSTID_API_KEY, fingerprint, duration)
                
                if not matches:
                    return {"error": "No matching recordings found"}
                
                # Get the best match
                best_match = matches[0]
                recording_id = best_match.get('recordings', [{}])[0].get('id')
                
                if not recording_id:
                    return {"error": "No recording ID found"}
                
                # Get detailed recording info from MusicBrainz
                try:
                    mb_recording = musicbrainzngs.get_recording_by_id(
                        recording_id,
                        includes=["artists", "releases", "isrcs"]
                    )
                    
                    if not mb_recording or "recording" not in mb_recording:
                        return {"error": "Recording not found in MusicBrainz"}
                    
                    recording = mb_recording["recording"]
                    
                    # Get release info if available
                    release = None
                    if "release-list" in recording:
                        release_id = recording["release-list"][0]["id"]
                        try:
                            release_info = musicbrainzngs.get_release_by_id(
                                release_id,
                                includes=["labels"]
                            )
                            if release_info and "release" in release_info:
                                release = release_info["release"]
                        except Exception as e:
                            logger.error(f"Error getting detailed release info: {str(e)}")
                    
                    # Get duration from MusicBrainz or use calculated duration
                    mb_duration_ms = recording.get("length", 0)
                    if isinstance(mb_duration_ms, str):
                        try:
                            mb_duration_ms = float(mb_duration_ms)
                        except (ValueError, TypeError):
                            mb_duration_ms = 0
                    
                    # Use MusicBrainz duration if available, otherwise use calculated duration
                    final_duration_minutes = (mb_duration_ms / 1000 / 60) if mb_duration_ms > 0 else duration_minutes
                    
                    # Calculate confidence based on acoustid score and our music likelihood
                    acoustid_score = float(best_match.get('score', 0))
                    combined_confidence = (acoustid_score * 80 + (music_likelihood / 100) * 20)
                    
                    return {
                        "title": recording.get("title", "Unknown"),
                        "artist": recording.get("artist-credit-phrase", "Unknown Artist"),
                        "album": release["title"] if release else None,
                        "release_date": release.get("date") if release else None,
                        "isrc": recording.get("isrc-list", [None])[0] if "isrc-list" in recording else None,
                        "label": release["label-info-list"][0]["label"]["name"] if release and "label-info-list" in release else None,
                        "external_metadata": {
                            "musicbrainz_id": recording.get("id"),
                            "release_id": release["id"] if release else None,
                            "acoustid": best_match.get('id')
                        },
                        "confidence": combined_confidence,
                        "duration_minutes": final_duration_minutes
                    }
                    
                except Exception as e:
                    logger.error(f"Error getting MusicBrainz recording: {str(e)}")
                    return {"error": f"MusicBrainz lookup failed: {str(e)}"}
                    
            except acoustid.FingerprintGenerationError as e:
                logger.error(f"Error generating fingerprint: {str(e)}")
                return {"error": f"Fingerprint generation failed: {str(e)}"}
            except acoustid.WebServiceError as e:
                logger.error(f"AcoustID service error: {str(e)}")
                return {"error": f"AcoustID service error: {str(e)}"}
            except ValueError as e:
                logger.error(f"Error with AcoustID API key: {str(e)}")
                return {"error": str(e)}
                
        except Exception as e:
            logger.error(f"Error in music recognition: {str(e)}")
            return {"error": str(e)}
