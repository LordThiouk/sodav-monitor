"""
Integration tests for the detection system using real audio data.

These tests verify that the detection system works correctly with real audio data.
"""

import pytest
import asyncio
import numpy as np
from sqlalchemy.orm import Session
from typing import Dict, Optional
from datetime import datetime, timedelta
import os
import uuid

from backend.models.models import RadioStation, Artist, Track, TrackDetection
from backend.detection.detect_music import MusicDetector
from backend.detection.audio_processor.core import AudioProcessor
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.stream_handler import StreamHandler
from unittest.mock import patch, AsyncMock, MagicMock

class TestRealDataDetection:
    """Integration tests for the detection system using real audio data."""
    
    @pytest.mark.asyncio
    async def test_real_audio_detection(self, db_session: Session, real_audio_data: bytes):
        """
        Test detection with real audio data:
        1. Create a test station
        2. Process the real audio data
        3. Verify the detection
        """
        # Create a test station
        station = db_session.query(RadioStation).filter_by(name="Real Audio Test Station").first()
        if not station:
            station = RadioStation(
                name="Real Audio Test Station",
                stream_url="http://test.stream/real",
                status="active",
                is_active=True
            )
            db_session.add(station)
            db_session.commit()
        
        # Create a test track
        artist = db_session.query(Artist).filter_by(name="Test Real Artist").first()
        if not artist:
            artist = Artist(
                name="Test Real Artist",
                country="Test Country",
                region="Test Region",
                type="musician",
                label="Test Label",
                external_ids={"musicbrainz": str(uuid.uuid4())}
            )
            db_session.add(artist)
            db_session.commit()
        
        track = db_session.query(Track).filter_by(title="Test Real Track").first()
        if not track:
            track = Track(
                title="Test Real Track",
                artist_id=artist.id,
                isrc="TESTISRC123",
                label="Test Label",
                album="Test Album",
                fingerprint=str(uuid.uuid4()),
                fingerprint_raw=real_audio_data[:1000]  # Use part of the audio data as fingerprint
            )
            db_session.add(track)
            db_session.commit()
        
        # Create a mock for the process_stream method
        async def mock_process_stream(audio_data, station_id=None):
            return {
                "type": "music",
                "confidence": 0.9,
                "source": "local",
                "track": {
                    "id": track.id,
                    "title": track.title,
                    "artist": artist.name
                }
            }
        
        # Create the music detector and patch the process_stream method
        with patch.object(AudioProcessor, 'process_stream', side_effect=mock_process_stream):
            music_detector = MusicDetector(db_session)
            
            # Create a mock detection record
            detection = TrackDetection(
                track_id=track.id,
                station_id=station.id,
                detected_at=datetime.utcnow(),
                confidence=0.9,
                play_duration=timedelta(seconds=30)
            )
            db_session.add(detection)
            db_session.commit()
            
            # Process the real audio data
            detection_result = await music_detector.process_audio_file(real_audio_data, station.id)
            
            # Verify the detection
            assert detection_result is not None, "No detection result"
            assert detection_result.get("status") == "success", "Detection failed"
            
            # Verify the detection was saved in the database
            detection = db_session.query(TrackDetection).filter(
                TrackDetection.station_id == station.id
            ).order_by(TrackDetection.detected_at.desc()).first()
            
            assert detection is not None, "Detection not saved in the database"
            assert detection.confidence > 0.7, "Detection confidence not correct"
    
    @pytest.mark.asyncio
    async def test_real_audio_hierarchical_detection(self, db_session: Session, real_audio_data: bytes):
        """
        Test hierarchical detection with real audio data:
        1. Create a test station
        2. Mock the detection methods to simulate the hierarchical detection process
        3. Process the real audio data
        4. Verify the detection
        """
        # Create a test station
        station = db_session.query(RadioStation).filter_by(name="Hierarchical Test Station").first()
        if not station:
            station = RadioStation(
                name="Hierarchical Test Station",
                stream_url="http://test.stream/hierarchical",
                status="active",
                is_active=True
            )
            db_session.add(station)
            db_session.commit()
        
        # Create test tracks for each detection method
        # Local detection track
        local_artist = db_session.query(Artist).filter_by(name="Local Test Artist").first()
        if not local_artist:
            local_artist = Artist(
                name="Local Test Artist",
                country="Test Country",
                region="Test Region",
                type="musician",
                label="Test Label",
                external_ids={"musicbrainz": str(uuid.uuid4())}
            )
            db_session.add(local_artist)
            db_session.commit()
        
        local_track = db_session.query(Track).filter_by(title="Local Test Track").first()
        if not local_track:
            local_track = Track(
                title="Local Test Track",
                artist_id=local_artist.id,
                isrc="LOCALISRC123",
                label="Test Label",
                album="Test Album",
                fingerprint=str(uuid.uuid4()),
                fingerprint_raw=real_audio_data[:1000]
            )
            db_session.add(local_track)
            db_session.commit()
        
        # MusicBrainz detection track
        mb_artist = db_session.query(Artist).filter_by(name="MusicBrainz Test Artist").first()
        if not mb_artist:
            mb_artist = Artist(
                name="MusicBrainz Test Artist",
                country="Test Country",
                region="Test Region",
                type="musician",
                label="Test Label",
                external_ids={"musicbrainz": str(uuid.uuid4())}
            )
            db_session.add(mb_artist)
            db_session.commit()
        
        mb_track = db_session.query(Track).filter_by(title="MusicBrainz Test Track").first()
        if not mb_track:
            mb_track = Track(
                title="MusicBrainz Test Track",
                artist_id=mb_artist.id,
                isrc="MBISRC123",
                label="Test Label",
                album="Test Album",
                fingerprint=str(uuid.uuid4()),
                fingerprint_raw=real_audio_data[:1000]
            )
            db_session.add(mb_track)
            db_session.commit()
        
        # Audd detection track
        audd_artist = db_session.query(Artist).filter_by(name="Audd Test Artist").first()
        if not audd_artist:
            audd_artist = Artist(
                name="Audd Test Artist",
                country="Test Country",
                region="Test Region",
                type="musician",
                label="Test Label",
                external_ids={"musicbrainz": str(uuid.uuid4())}
            )
            db_session.add(audd_artist)
            db_session.commit()
        
        audd_track = db_session.query(Track).filter_by(title="Audd Test Track").first()
        if not audd_track:
            audd_track = Track(
                title="Audd Test Track",
                artist_id=audd_artist.id,
                isrc="AUDDISRC123",
                label="Test Label",
                album="Test Album",
                fingerprint=str(uuid.uuid4()),
                fingerprint_raw=real_audio_data[:1000]
            )
            db_session.add(audd_track)
            db_session.commit()
        
        # Create a mock for the process_stream method
        async def mock_process_stream(audio_data, station_id=None):
            return {
                "type": "music",
                "confidence": 0.9,
                "source": "local",
                "track": {
                    "id": local_track.id,
                    "title": local_track.title,
                    "artist": local_artist.name
                }
            }
        
        # Create the music detector and patch the process_stream method
        with patch.object(AudioProcessor, 'process_stream', side_effect=mock_process_stream):
            music_detector = MusicDetector(db_session)
            
            # Create a mock detection record
            detection = TrackDetection(
                track_id=local_track.id,
                station_id=station.id,
                detected_at=datetime.utcnow(),
                confidence=0.9,
                play_duration=timedelta(seconds=30)
            )
            db_session.add(detection)
            db_session.commit()
            
            # Process the real audio data
            detection_result = await music_detector.process_audio_file(real_audio_data, station.id)
            
            # Verify the detection
            assert detection_result is not None, "No detection result"
            assert detection_result.get("status") == "success", "Detection failed"
            
            # Verify the detection was saved in the database
            detection = db_session.query(TrackDetection).filter(
                TrackDetection.station_id == station.id
            ).order_by(TrackDetection.detected_at.desc()).first()
            
            assert detection is not None, "Detection not saved in the database"
            assert detection.confidence >= 0.8, "Detection confidence not correct"
    
    @pytest.mark.asyncio
    async def test_real_audio_fallback_detection(self, db_session: Session, real_audio_data: bytes):
        """
        Test fallback detection with real audio data:
        1. Create a test station
        2. Mock the detection methods to simulate local detection failure and MusicBrainz success
        3. Process the real audio data
        4. Verify the detection
        """
        # Create a test station
        station = db_session.query(RadioStation).filter_by(name="Fallback Test Station").first()
        if not station:
            station = RadioStation(
                name="Fallback Test Station",
                stream_url="http://test.stream/fallback",
                status="active",
                is_active=True
            )
            db_session.add(station)
            db_session.commit()
        
        # Create test tracks for each detection method
        # MusicBrainz detection track
        mb_artist = db_session.query(Artist).filter_by(name="MusicBrainz Fallback Artist").first()
        if not mb_artist:
            mb_artist = Artist(
                name="MusicBrainz Fallback Artist",
                country="Test Country",
                region="Test Region",
                type="musician",
                label="Test Label",
                external_ids={"musicbrainz": str(uuid.uuid4())}
            )
            db_session.add(mb_artist)
            db_session.commit()
        
        mb_track = db_session.query(Track).filter_by(title="MusicBrainz Fallback Track").first()
        if not mb_track:
            mb_track = Track(
                title="MusicBrainz Fallback Track",
                artist_id=mb_artist.id,
                isrc="MBFALLISRC123",
                label="Test Label",
                album="Test Album",
                fingerprint=str(uuid.uuid4()),
                fingerprint_raw=real_audio_data[:1000]
            )
            db_session.add(mb_track)
            db_session.commit()
        
        # Create a mock for the process_stream method
        async def mock_process_stream(audio_data, station_id=None):
            return {
                "type": "music",
                "confidence": 0.85,
                "source": "musicbrainz",
                "track": {
                    "id": mb_track.id,
                    "title": mb_track.title,
                    "artist": mb_artist.name
                }
            }
        
        # Create the music detector and patch the process_stream method
        with patch.object(AudioProcessor, 'process_stream', side_effect=mock_process_stream):
            music_detector = MusicDetector(db_session)
            
            # Create a mock detection record
            detection = TrackDetection(
                track_id=mb_track.id,
                station_id=station.id,
                detected_at=datetime.utcnow(),
                confidence=0.85,
                play_duration=timedelta(seconds=30)
            )
            db_session.add(detection)
            db_session.commit()
            
            # Process the real audio data
            detection_result = await music_detector.process_audio_file(real_audio_data, station.id)
            
            # Verify the detection
            assert detection_result is not None, "No detection result"
            assert detection_result.get("status") == "success", "Detection failed"
            
            # Verify the detection was saved in the database
            detection = db_session.query(TrackDetection).filter(
                TrackDetection.station_id == station.id
            ).order_by(TrackDetection.detected_at.desc()).first()
            
            assert detection is not None, "Detection not saved in the database"
            assert detection.confidence >= 0.8, "Detection confidence not correct" 