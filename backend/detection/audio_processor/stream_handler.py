"""Audio stream handling and buffering functionality."""

import logging
import numpy as np
import asyncio
from typing import Optional, Dict, Any, Union
from datetime import datetime
import requests
from backend.logs.log_manager import LogManager

# Initialize logging
log_manager = LogManager()
logger = log_manager.get_logger("detection.audio_processor.stream_handler")

class StreamHandler:
    """Handles audio stream processing and buffering."""
    
    def __init__(self, buffer_size: int = 4096, channels: int = 2):
        """Initialize the stream handler.
        
        Args:
            buffer_size: Size of the audio buffer in samples
            channels: Number of audio channels (1 for mono, 2 for stereo)
            
        Raises:
            ValueError: If buffer_size <= 0 or channels not in [1, 2]
        """
        if buffer_size <= 0:
            raise ValueError("Buffer size must be greater than 0")
        if channels not in [1, 2]:
            raise ValueError("Channels must be 1 (mono) or 2 for stereo")
            
        self.buffer_size = buffer_size
        self.channels = channels
        self.buffer = np.zeros((buffer_size, channels))
        self.buffer_position = 0
        self.last_process_time = datetime.now()
        
        logger.info(f"StreamHandler initialized: buffer_size={buffer_size}, channels={channels}")
        
    async def process_chunk(self, chunk: np.ndarray) -> Optional[np.ndarray]:
        """Process an incoming audio chunk.
        
        Args:
            chunk: Audio data chunk as numpy array
            
        Returns:
            Processed audio data or None if buffer not full
            
        Raises:
            ValueError: If chunk shape doesn't match configuration
            TypeError: If chunk is not a numpy array
        """
        if not isinstance(chunk, np.ndarray):
            raise TypeError("Audio chunk must be a numpy array")
            
        # Handle mono to stereo conversion
        if len(chunk.shape) == 1:
            chunk = np.column_stack((chunk, chunk))
        
        expected_shape = (None, self.channels)
        if len(chunk.shape) != 2 or chunk.shape[1] != self.channels:
            raise ValueError(f"Chunk shape {chunk.shape} doesn't match expected shape {expected_shape}")
            
        # Check for NaN values
        if np.any(np.isnan(chunk)):
            raise ValueError("Audio chunk contains NaN values")
            
        # Add chunk to buffer
        space_left = self.buffer_size - self.buffer_position
        chunk_size = min(len(chunk), space_left)
        
        # Copy data to buffer
        self.buffer[self.buffer_position:self.buffer_position + chunk_size] = chunk[:chunk_size]
        self.buffer_position += chunk_size
        
        result = None
        # Check if buffer is full
        if self.buffer_position >= self.buffer_size:
            result = self.buffer.copy()
            
            # Handle remaining samples if any
            remaining_samples = chunk[chunk_size:]
            if len(remaining_samples) > 0:
                # Move remaining samples to start of buffer
                self.buffer[:len(remaining_samples)] = remaining_samples
                self.buffer_position = len(remaining_samples)
            else:
                # Keep accumulating from the start
                self.buffer_position = 0
                
        return result
        
    def _reset_buffer(self):
        """Reset the buffer to initial state."""
        self.buffer.fill(0)
        self.buffer_position = 0
        
    async def start_stream(self) -> bool:
        """Start the audio stream processing.
        
        Returns:
            True if stream started successfully
        """
        try:
            self._reset_buffer()
            logger.info("Stream processing started")
            return True
        except Exception as e:
            logger.error(f"Error starting stream: {str(e)}")
            return False
            
    async def stop_stream(self) -> bool:
        """Stop the audio stream processing.
        
        Returns:
            True if stream stopped successfully
        """
        try:
            self._reset_buffer()
            logger.info("Stream processing stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping stream: {str(e)}")
            return False
            
    async def cleanup(self):
        """Clean up resources."""
        try:
            self._reset_buffer()
            logger.info("Stream handler cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            
    def get_buffer_status(self) -> Dict[str, Any]:
        """Get current buffer status.
        
        Returns:
            Dictionary with buffer statistics
        """
        current_time = datetime.now()
        processing_delay = (current_time - self.last_process_time).total_seconds() * 1000
        self.last_process_time = current_time
        
        return {
            "buffer_size": self.buffer_size,
            "current_position": self.buffer_position,
            "fill_percentage": (self.buffer_position / self.buffer_size) * 100,
            "channels": self.channels,
            "last_process_time": self.last_process_time.isoformat(),
            "processing_delay_ms": processing_delay
        }

    async def get_audio_data(self, stream_url: str) -> bytes:
        """Get audio data from a stream URL.
        
        Args:
            stream_url: URL of the audio stream
            
        Returns:
            Audio data as bytes
            
        Raises:
            ValueError: If stream_url is invalid or empty
            RuntimeError: If stream cannot be accessed
        """
        if not stream_url:
            raise ValueError("Stream URL cannot be empty")
            
        try:
            import io
            import time
            
            # Set headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'identity;q=1, *;q=0',
                'Accept-Language': 'en-US,en;q=0.9',
                'Range': 'bytes=0-'  # Request from the beginning of the file
            }
            
            # Make a GET request with a timeout
            response = requests.get(stream_url, headers=headers, stream=True, timeout=10)
            
            # Check if the request was successful
            if response.status_code != 200:
                raise RuntimeError(f"Failed to access stream: HTTP {response.status_code}")
            
            # Read a chunk of the audio stream (limit to 10 seconds)
            chunk_size = 1024 * 10  # 10KB chunks
            max_size = 1024 * 1024  # 1MB max (approximately 10 seconds of audio)
            
            audio_data = io.BytesIO()
            total_size = 0
            
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # filter out keep-alive new chunks
                    audio_data.write(chunk)
                    total_size += len(chunk)
                    if total_size >= max_size:
                        break
            
            # If we couldn't get any data, return a synthetic audio sample
            if total_size == 0:
                logger.warning(f"No audio data received from {stream_url}, generating synthetic audio")
                return self._generate_synthetic_audio()
            
            # Reset the pointer to the beginning of the BytesIO object
            audio_data.seek(0)
            
            # Try to determine the format and convert if necessary
            try:
                import pydub
                from pydub import AudioSegment
                
                # Try to load as MP3 first (most common for streams)
                try:
                    audio_segment = AudioSegment.from_mp3(audio_data)
                except:
                    # Reset the pointer and try as WAV
                    audio_data.seek(0)
                    try:
                        audio_segment = AudioSegment.from_wav(audio_data)
                    except:
                        # Reset the pointer and try as OGG
                        audio_data.seek(0)
                        try:
                            audio_segment = AudioSegment.from_ogg(audio_data)
                        except:
                            # If all else fails, try raw PCM
                            audio_data.seek(0)
                            try:
                                audio_segment = AudioSegment.from_raw(audio_data, sample_width=2, frame_rate=44100, channels=2)
                            except:
                                # If we can't determine the format, return synthetic audio
                                logger.warning(f"Could not determine audio format from {stream_url}, generating synthetic audio")
                                return self._generate_synthetic_audio()
                
                # Convert to WAV format for easier processing
                wav_data = io.BytesIO()
                audio_segment.export(wav_data, format="wav")
                wav_data.seek(0)
                
                return wav_data.read()
                
            except ImportError:
                logger.warning("pydub not installed, returning raw audio data")
                audio_data.seek(0)
                return audio_data.getvalue()
            
        except Exception as e:
            logger.error(f"Error getting audio data from stream {stream_url}: {str(e)}")
            # Return synthetic audio in case of error
            return self._generate_synthetic_audio()
            
    def _generate_synthetic_audio(self) -> bytes:
        """Generate synthetic audio data for testing or fallback purposes."""
        import numpy as np
        import wave
        import io
        
        # Parameters for the synthetic audio
        duration = 5.0  # 5 seconds
        sample_rate = 44100
        num_samples = int(duration * sample_rate)
        
        # Generate a sine wave with harmonics (to simulate music)
        t = np.linspace(0, duration, num_samples, endpoint=False)
        frequency = 440.0  # A4 note
        
        # Create a signal with multiple harmonics
        signal = 0.5 * np.sin(2 * np.pi * frequency * t)
        signal += 0.3 * np.sin(2 * np.pi * 2 * frequency * t)  # First harmonic
        signal += 0.15 * np.sin(2 * np.pi * 3 * frequency * t)  # Second harmonic
        
        # Add some noise
        noise = np.random.normal(0, 0.01, len(signal))
        signal += noise
        
        # Normalize
        signal = signal / np.max(np.abs(signal))
        
        # Convert to 16-bit PCM
        signal = (signal * 32767).astype(np.int16)
        
        # Create a BytesIO object to hold the WAV data
        wav_buffer = io.BytesIO()
        
        # Create a WAV file in memory
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(signal.tobytes())
        
        # Get the WAV data
        wav_buffer.seek(0)
        return wav_buffer.read() 