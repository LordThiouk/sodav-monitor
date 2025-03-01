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