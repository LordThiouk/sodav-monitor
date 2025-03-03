"""Tests for the analytics API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, List
import json

from backend.models.models import (
    RadioStation, Track, TrackDetection,
    Artist, StationStatus, TrackStats,
    ArtistStats, StationStats, DetectionHourly,
    AnalyticsData
)
from backend.analytics.stats_manager import StatsManager

@pytest.fixture
def stats_manager(db_session: Session) -> StatsManager:
    """Create a StatsManager instance for testing."""
    return StatsManager(db_session)

@pytest.fixture(autouse=True)
def cleanup_db(db_session: Session):
    """Clean up the database after each test."""
    yield
    db_session.query(ArtistStats).delete()
    db_session.query(TrackStats).delete()
    db_session.query(StationStats).delete()
    db_session.query(DetectionHourly).delete()
    db_session.query(AnalyticsData).delete()
    db_session.commit()

@pytest.fixture
def test_track_stats(db_session: Session, test_track: Track) -> TrackStats:
    """Create test track statistics."""
    # First check if stats already exist
    existing_stats = db_session.query(TrackStats).filter(
        TrackStats.track_id == test_track.id
    ).first()
    
    if existing_stats:
        db_session.delete(existing_stats)
        db_session.commit()
    
    stats = TrackStats(
        track_id=test_track.id,
        total_plays=50,
        total_play_time=timedelta(hours=3),
        average_confidence=0.95,
        last_detected=datetime.utcnow()
    )
    db_session.add(stats)
    db_session.commit()
    return stats

@pytest.fixture
def test_artist_stats(db_session: Session, test_artist: Artist) -> ArtistStats:
    """Create test artist statistics."""
    # First check if stats already exist
    existing_stats = db_session.query(ArtistStats).filter(
        ArtistStats.artist_id == test_artist.id
    ).first()
    
    if existing_stats:
        db_session.delete(existing_stats)
        db_session.commit()
    
    stats = ArtistStats(
        artist_id=test_artist.id,
        total_plays=25,
        total_play_time=timedelta(hours=2, minutes=30),
        average_confidence=0.89,
        last_detected=datetime.utcnow()
    )
    db_session.add(stats)
    db_session.commit()
    return stats

@pytest.fixture
def test_station_stats(db_session: Session, test_station: RadioStation) -> StationStats:
    """Create test station statistics."""
    # First check if stats already exist
    existing_stats = db_session.query(StationStats).filter(
        StationStats.station_id == test_station.id
    ).first()
    
    if existing_stats:
        db_session.delete(existing_stats)
        db_session.commit()
    
    stats = StationStats(
        station_id=test_station.id,
        detection_count=100,
        average_confidence=0.92,
        last_detected=datetime.utcnow()
    )
    db_session.add(stats)
    db_session.commit()
    return stats

@pytest.fixture
def multiple_detections(
    db_session: Session,
    test_track: Track,
    test_station: RadioStation
) -> List[TrackDetection]:
    """Create multiple test detections."""
    detections = []
    base_time = datetime.utcnow() - timedelta(hours=12)  # Create detections from the last 12 hours
    
    for i in range(10):
        detection = TrackDetection(
            track_id=test_track.id,
            station_id=test_station.id,
            detected_at=base_time + timedelta(hours=i),
            play_duration=timedelta(minutes=3),
            confidence=0.9,
            fingerprint="test_fingerprint",
            audio_hash="test_audio_hash"
        )
        detections.append(detection)
    
    db_session.add_all(detections)
    db_session.commit()
    return detections

@pytest.mark.asyncio
class TestAnalyticsAPI:
    """Test cases for the analytics API endpoints."""

    async def test_get_overview(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_track_stats: TrackStats,
        test_artist_stats: ArtistStats,
        test_station_stats: StationStats,
        test_analytics_data: AnalyticsData,
        test_hourly_detections: List[DetectionHourly],
        stats_manager: StatsManager
    ):
        """Test getting analytics overview."""
        response = test_client.get("/api/analytics/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "totalChannels" in data
        assert "activeStations" in data
        assert "totalPlays" in data
        assert "totalPlayTime" in data
        assert "systemHealth" in data
        assert "playsData" in data
        assert "topTracks" in data
        assert "topArtists" in data
        assert "topLabels" in data
        assert "topChannels" in data

    async def test_get_track_stats(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_track: Track,
        test_track_stats: TrackStats,
        stats_manager: StatsManager
    ):
        """Test getting track statistics."""
        response = test_client.get("/api/analytics/tracks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        track_data = next((t for t in data if t["id"] == test_track.id), None)
        assert track_data is not None
        assert track_data["detection_count"] == test_track_stats.total_plays
        assert track_data["average_confidence"] == test_track_stats.average_confidence

    async def test_get_artist_stats(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_artist: Artist,
        test_artist_stats: ArtistStats,
        stats_manager: StatsManager
    ):
        """Test getting artist statistics."""
        response = test_client.get("/api/analytics/artists", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        artist_data = next((a for a in data if a["artist"] == test_artist.name), None)
        assert artist_data is not None
        assert artist_data["detection_count"] == test_artist_stats.total_plays
        assert artist_data["average_confidence"] == test_artist_stats.average_confidence

    async def test_get_station_stats(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        test_station_stats: StationStats,
        stats_manager: StatsManager
    ):
        """Test getting station statistics."""
        response = test_client.get("/api/analytics/stations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        station_data = next((s for s in data if s["id"] == test_station.id), None)
        assert station_data is not None
        assert station_data["detections24h"] == test_station_stats.detection_count
        assert station_data["status"] == test_station.status if test_station.status else "inactive"

    async def test_get_trend_analysis(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        multiple_detections: List[TrackDetection],
        stats_manager: StatsManager
    ):
        """Test getting trend analysis."""
        response = test_client.get(
            "/api/analytics/dashboard",
            params={"period": 24},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "totalDetections" in data
        assert "detectionRate" in data
        assert "activeStations" in data
        assert "averageConfidence" in data
        assert "detectionsByHour" in data
        assert "topArtists" in data
        assert "systemHealth" in data

    async def test_get_stats_by_timeframe(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        multiple_detections: List[TrackDetection],
        stats_manager: StatsManager
    ):
        """Test getting statistics by timeframe."""
        now = datetime.utcnow()
        start_date = now - timedelta(days=7)
        response = test_client.get(
            "/api/analytics/dashboard",
            params={"period": 168},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "totalDetections" in data
        assert "detectionRate" in data
        assert "activeStations" in data
        assert "averageConfidence" in data
        assert "detectionsByHour" in data
        assert "topArtists" in data
        assert "systemHealth" in data

    async def test_invalid_timeframe(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        stats_manager: StatsManager
    ):
        """Test invalid timeframe parameter."""
        response = test_client.get(
            "/api/analytics/dashboard",
            params={"period": -1},
            headers=auth_headers
        )
        assert response.status_code == 400

    async def test_nonexistent_track_stats(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test getting statistics for nonexistent track."""
        response = test_client.get("/api/analytics/tracks/999999/stats", headers=auth_headers)
        assert response.status_code == 404

    async def test_export_analytics(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        multiple_detections: List[TrackDetection]
    ):
        """Test exporting analytics data."""
        response = test_client.get(
            "/api/analytics/export",
            params={"format": "json"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0 