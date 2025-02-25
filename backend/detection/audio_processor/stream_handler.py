"""Module de gestion des flux audio."""

import aiohttp
import logging
import io
import av
from typing import Dict, Any, Optional, Tuple
import numpy as np
from pydub import AudioSegment
from ...utils.logging_config import setup_logging

logger = setup_logging(__name__)

class StreamHandler:
    """Gestionnaire des flux audio."""
    
    def __init__(self):
        """Initialise le gestionnaire de flux."""
        self.logger = logging.getLogger(__name__)
        self.chunk_size = 4096
        self.sample_rate = 22050
        self.min_duration = 8
        self.max_duration = 20
    
    async def process_stream(
        self,
        stream_url: str,
        feature_extractor: 'FeatureExtractor',
        track_manager: 'TrackManager',
        station_id: Optional[int] = None
    ) -> Optional[Dict]:
        """Traite un flux audio."""
        try:
            # Télécharge et analyse le flux audio
            audio_data = await self._download_audio_chunk(stream_url)
            if not audio_data:
                return {"error": "Impossible de télécharger l'audio"}
            
            # Compresse l'audio pour optimiser le traitement
            compressed_audio = self._compress_audio(audio_data)
            
            # Extrait les caractéristiques audio
            features = await feature_extractor.analyze_audio(compressed_audio)
            
            # Si les caractéristiques sont valides, traite la piste
            if features and features.get("confidence", 0) > 0.5:
                return await track_manager.process_track(features, station_id)
            
            return {"status": "Aucune musique détectée"}
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement du flux {stream_url}: {str(e)}")
            return {"error": str(e)}
    
    async def _download_audio_chunk(self, url: str) -> Optional[bytes]:
        """Télécharge un segment audio depuis l'URL."""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.logger.error(f"Erreur HTTP {response.status} pour {url}")
                        return None
                    
                    # Lit les premiers chunks du flux
                    chunks = []
                    total_size = 0
                    max_size = 1024 * 1024  # 1MB maximum
                    
                    async for chunk in response.content.iter_chunked(self.chunk_size):
                        chunks.append(chunk)
                        total_size += len(chunk)
                        if total_size >= max_size:
                            break
                    
                    return b"".join(chunks)
                    
        except Exception as e:
            self.logger.error(f"Erreur lors du téléchargement depuis {url}: {str(e)}")
            return None
    
    def _compress_audio(self, audio_data: bytes) -> bytes:
        """Compresse les données audio pour optimiser le traitement."""
        try:
            # Convertit les données brutes en AudioSegment
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            
            # Normalise le volume
            normalized_audio = audio.normalize()
            
            # Convertit en mono et réduit la qualité
            compressed = normalized_audio.set_channels(1).set_frame_rate(22050)
            
            # Exporte en format compressé
            buffer = io.BytesIO()
            compressed.export(buffer, format="wav")
            return buffer.getvalue()
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la compression audio: {str(e)}")
            return audio_data
    
    async def check_stream_status(self, url: str) -> dict:
        """Vérifie l'état d'un flux audio."""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    return {
                        "status": response.status,
                        "content_type": response.headers.get("content-type", ""),
                        "is_alive": response.status == 200
                    }
        except Exception as e:
            return {
                "status": 0,
                "error": str(e),
                "is_alive": False
            } 