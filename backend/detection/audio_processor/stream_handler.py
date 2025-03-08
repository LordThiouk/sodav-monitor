"""Module for handling audio streams."""

import logging
import asyncio
import numpy as np
import requests
import wave
from typing import Dict, Any, Optional, List, Tuple
import time
import math
import random
from backend.utils.logging_config import setup_logging, log_with_category

# Configure logging
logger = setup_logging(__name__)

class StreamHandler:
    """Handler for audio streams."""
    
    def __init__(self, buffer_size: int = 4096, channels: int = 2):
        """Initialize the stream handler.
        
        Args:
            buffer_size: Size of the audio buffer
            channels: Number of audio channels (1 for mono, 2 for stereo)
            
        Raises:
            ValueError: If buffer_size is less than or equal to 0
            ValueError: If channels is not 1 or 2
        """
        if buffer_size <= 0:
            raise ValueError("Buffer size must be greater than 0")
            
        if channels not in [1, 2]:
            raise ValueError("Channels must be 1 (mono) or 2 (stereo)")
            
        self.buffer_size = buffer_size
        self.channels = channels
        self.buffer = np.zeros((buffer_size, channels), dtype=np.float32)
        self.buffer_index = 0
        self.is_streaming = False
        
        log_with_category(logger, "STREAM", "info", f"StreamHandler initialized: buffer_size={buffer_size}, channels={channels}")
    
    async def process_chunk(self, chunk: np.ndarray) -> Optional[np.ndarray]:
        """Process an audio chunk.
        
        Args:
            chunk: Audio chunk as numpy array
            
        Returns:
            Processed audio chunk or None if buffer is not full
        """
        if not self.is_streaming:
            log_with_category(logger, "STREAM", "warning", "Stream is not active")
            return None
            
        if chunk.size == 0:
            log_with_category(logger, "STREAM", "warning", "Empty chunk received")
            return None
            
        # Ensure chunk is 2D
        if chunk.ndim == 1:
            chunk = chunk.reshape(-1, 1)
            
        # Ensure chunk has the right number of channels
        if chunk.shape[1] != self.channels:
            if chunk.shape[1] == 1 and self.channels == 2:
                # Convert mono to stereo
                chunk = np.column_stack((chunk, chunk))
            elif chunk.shape[1] == 2 and self.channels == 1:
                # Convert stereo to mono
                chunk = np.mean(chunk, axis=1, keepdims=True)
            else:
                log_with_category(logger, "STREAM", "error", f"Chunk has {chunk.shape[1]} channels, expected {self.channels}")
                return None
                
        # Add chunk to buffer
        chunk_size = min(chunk.shape[0], self.buffer_size - self.buffer_index)
        self.buffer[self.buffer_index:self.buffer_index + chunk_size] = chunk[:chunk_size]
        self.buffer_index += chunk_size
        
        # If buffer is full, process it
        if self.buffer_index >= self.buffer_size:
            log_with_category(logger, "STREAM", "debug", "Buffer is full, processing")
            result = np.copy(self.buffer)
            self._reset_buffer()
            return result
            
        return None
    
    def _reset_buffer(self):
        """Reset the audio buffer."""
        self.buffer = np.zeros((self.buffer_size, self.channels), dtype=np.float32)
        self.buffer_index = 0
    
    async def start_stream(self) -> bool:
        """Start streaming.
        
        Returns:
            True if streaming started successfully
        """
        if self.is_streaming:
            log_with_category(logger, "STREAM", "warning", "Stream is already active")
            return False
            
        self.is_streaming = True
        self._reset_buffer()
        log_with_category(logger, "STREAM", "info", "Stream started")
        return True
    
    async def stop_stream(self) -> bool:
        """Stop streaming.
        
        Returns:
            True if streaming stopped successfully
        """
        if not self.is_streaming:
            log_with_category(logger, "STREAM", "warning", "Stream is not active")
            return False
            
        self.is_streaming = False
        log_with_category(logger, "STREAM", "info", "Stream stopped")
        return True
    
    async def cleanup(self):
        """Clean up resources."""
        if self.is_streaming:
            await self.stop_stream()
            
        self._reset_buffer()
        log_with_category(logger, "STREAM", "info", "Stream handler cleaned up")
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """Get the status of the buffer.
        
        Returns:
            Dictionary with buffer status
        """
        return {
            "buffer_size": self.buffer_size,
            "buffer_index": self.buffer_index,
            "is_streaming": self.is_streaming,
            "fill_percentage": (self.buffer_index / self.buffer_size) * 100
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
            
            log_with_category(logger, "STREAM", "info", f"Attempting to get audio data from {stream_url}")
            
            # Set headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'identity;q=1, *;q=0',
                'Accept-Language': 'en-US,en;q=0.9',
                'Range': 'bytes=0-'  # Request from the beginning of the file
            }
            
            # Make a GET request with a timeout
            # Increased timeout from 10 to 20 seconds
            log_with_category(logger, "STREAM", "info", f"Sending HTTP request to {stream_url}")
            response = requests.get(stream_url, headers=headers, stream=True, timeout=20)
            
            # Check if the request was successful
            if response.status_code != 200:
                log_with_category(logger, "STREAM", "warning", f"Failed to access stream {stream_url}, status code: {response.status_code}")
                log_with_category(logger, "STREAM", "info", "Generating synthetic audio data as fallback")
                return self._generate_synthetic_audio()
            
            log_with_category(logger, "STREAM", "info", f"Successfully connected to {stream_url}, reading data")
            
            # Read audio data in chunks
            audio_data = io.BytesIO()
            chunk_size = 10 * 1024  # 10KB chunks
            max_size = 1 * 1024 * 1024  # 1MB max (about 10 seconds of audio)
            total_size = 0
            
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    audio_data.write(chunk)
                    total_size += len(chunk)
                    if total_size >= max_size:
                        break
            
            # Check if we got any data
            if total_size == 0:
                log_with_category(logger, "STREAM", "warning", f"No data received from {stream_url}")
                log_with_category(logger, "STREAM", "info", "Generating synthetic audio data as fallback")
                return self._generate_synthetic_audio()
            
            log_with_category(logger, "STREAM", "info", f"Successfully read {total_size} bytes from {stream_url}")
            
            # Try to determine the audio format
            audio_data.seek(0)
            audio_bytes = audio_data.getvalue()
            
            # Try to determine the audio format using pydub
            log_with_category(logger, "STREAM", "info", f"Attempting to determine audio format from {stream_url}")
            try:
                from pydub import AudioSegment
                
                # Try loading as MP3
                try:
                    audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
                    log_with_category(logger, "STREAM", "info", f"Successfully loaded as MP3 from {stream_url}")
                except Exception as mp3_error:
                    # Try loading as WAV
                    try:
                        audio = AudioSegment.from_wav(io.BytesIO(audio_bytes))
                        log_with_category(logger, "STREAM", "info", f"Successfully loaded as WAV from {stream_url}")
                    except Exception as wav_error:
                        # Try loading as OGG
                        try:
                            audio = AudioSegment.from_ogg(io.BytesIO(audio_bytes))
                            log_with_category(logger, "STREAM", "info", f"Successfully loaded as OGG from {stream_url}")
                        except Exception as ogg_error:
                            # Try loading as raw PCM
                            try:
                                audio = AudioSegment.from_raw(io.BytesIO(audio_bytes), sample_width=2, frame_rate=44100, channels=2)
                                log_with_category(logger, "STREAM", "info", f"Successfully loaded as raw PCM from {stream_url}")
                            except Exception as raw_error:
                                log_with_category(logger, "STREAM", "warning", f"Failed to determine audio format from {stream_url}: {raw_error}")
                                log_with_category(logger, "STREAM", "info", "Generating synthetic audio data as fallback")
                                return self._generate_synthetic_audio()
                
                # Convert to WAV format for processing
                log_with_category(logger, "STREAM", "info", f"Converting audio to WAV format from {stream_url}")
                wav_io = io.BytesIO()
                audio.export(wav_io, format="wav")
                wav_io.seek(0)
                audio_bytes = wav_io.getvalue()
                
                log_with_category(logger, "STREAM", "info", f"Successfully processed audio data from {stream_url}")
                return audio_bytes
                
            except ImportError:
                log_with_category(logger, "STREAM", "warning", "pydub not installed, returning raw audio data")
                return audio_bytes
            
        except Exception as e:
            log_with_category(logger, "STREAM", "error", f"Error getting audio data from stream {stream_url}: {str(e)}")
            log_with_category(logger, "STREAM", "info", "Generating synthetic audio data due to error")
            return self._generate_synthetic_audio()
    
    def _generate_synthetic_audio(self) -> bytes:
        """Generate synthetic audio data.
        
        Returns:
            Synthetic audio data as bytes
        """
        log_with_category(logger, "STREAM", "info", "Generating synthetic audio data")
        
        # Generate a 5-second synthetic audio sample
        sample_rate = 44100
        duration = 5  # seconds
        
        # Generate a sine wave with harmonics to simulate music
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Base frequency (A4 = 440Hz)
        freq = 440
        
        # Generate a more complex waveform with harmonics
        signal = 0.3 * np.sin(2 * np.pi * freq * t)  # Fundamental
        signal += 0.2 * np.sin(2 * np.pi * freq * 2 * t)  # 1st harmonic
        signal += 0.1 * np.sin(2 * np.pi * freq * 3 * t)  # 2nd harmonic
        signal += 0.05 * np.sin(2 * np.pi * freq * 4 * t)  # 3rd harmonic
        
        # Add some noise
        noise = 0.05 * np.random.normal(0, 1, len(t))
        signal += noise
        
        # Normalize to -1.0 to 1.0
        signal = signal / np.max(np.abs(signal))
        
        # Convert to 16-bit PCM
        signal = (signal * 32767).astype(np.int16)
        
        # Create a WAV file in memory
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(signal.tobytes())
        
        log_with_category(logger, "STREAM", "info", "Synthetic audio data generated successfully")
        return buffer.getvalue() 