"""Audio stream handling and buffering functionality."""

import logging
import numpy as np
import asyncio
from typing import Optional, Dict, Any, Union
from datetime import datetime

logger = logging.getLogger(__name__)

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

    async def get_audio_data(self, stream_url: str) -> np.ndarray:
        """Get audio data from a stream URL.
        
        Args:
            stream_url: URL of the audio stream
            
        Returns:
            Audio data as numpy array
            
        Raises:
            ValueError: If stream_url is invalid or empty
            RuntimeError: If stream cannot be accessed
        """
        if not stream_url:
            raise ValueError("Stream URL cannot be empty")
            
        try:
            # En environnement de production, cette méthode devrait:
            # 1. Se connecter au flux audio
            # 2. Capturer un segment audio
            # 3. Convertir en tableau numpy
            # 4. Retourner les données
            
            # Pour les tests, générer un signal audio plus réaliste
            # au lieu de simplement utiliser des données aléatoires
            
            # Paramètres du signal
            duration = 5.0  # 5 secondes de données audio
            sample_rate = 44100  # Fréquence d'échantillonnage standard
            t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
            
            # Générer un signal sinusoïdal (simulant une note de musique)
            # Fréquence de 440 Hz (La4)
            frequency = 440.0
            amplitude = 0.5
            
            # Créer un signal avec plusieurs harmoniques pour simuler un son musical
            signal = amplitude * np.sin(2 * np.pi * frequency * t)
            signal += 0.3 * np.sin(2 * np.pi * 2 * frequency * t)  # Première harmonique
            signal += 0.15 * np.sin(2 * np.pi * 3 * frequency * t)  # Deuxième harmonique
            signal += 0.05 * np.sin(2 * np.pi * 4 * frequency * t)  # Troisième harmonique
            
            # Ajouter un peu de bruit pour simuler un signal réel
            noise = np.random.normal(0, 0.01, len(signal))
            signal += noise
            
            # Normaliser le signal
            signal = signal / np.max(np.abs(signal))
            
            # Convertir en format stéréo si nécessaire
            if self.channels == 2:
                # Créer un signal stéréo légèrement différent sur chaque canal
                signal2 = signal * 0.98 + np.random.normal(0, 0.005, len(signal))
                stereo_signal = np.column_stack((signal, signal2))
                return stereo_signal
            else:
                # Format mono
                return signal.reshape(-1, 1)
            
        except Exception as e:
            logger.error(f"Error getting audio data from stream {stream_url}: {str(e)}")
            raise RuntimeError(f"Failed to get audio data: {str(e)}") 