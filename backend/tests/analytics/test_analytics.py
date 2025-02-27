"""Tests pour le module d'analytics."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, List
from ..models import (
    TrackDetection,
    ArtistStats,
    TrackStats,
    StationStats,
    DetectionHourly,
    DetectionDaily
)
from ..analytics.stats_manager import StatsManager

@pytest.fixture
def stats_manager(db_session: Session):
    """Fixture pour le gestionnaire de statistiques."""
    return StatsManager(db_session)

@pytest.fixture
def sample_detection_data(db_session: Session) -> TrackDetection:
    """Fixture pour créer des données de détection de test."""
    detection = TrackDetection(
        station_id=1,
        track_id=1,
        confidence=0.95,
        detected_at=datetime.utcnow(),
        play_duration=timedelta(minutes=3)
    )
    db_session.add(detection)
    db_session.commit()
    return detection

@pytest.mark.asyncio
async def test_update_detection_stats(stats_manager, sample_detection_data, db_session):
    """Test de mise à jour des statistiques de détection."""
    await stats_manager.update_detection_stats(sample_detection_data)
    
    # Vérification des stats horaires
    hourly_stats = db_session.query(DetectionHourly).first()
    assert hourly_stats is not None
    assert hourly_stats.detection_count > 0
    
    # Vérification des stats journalières
    daily_stats = db_session.query(DetectionDaily).first()
    assert daily_stats is not None
    assert daily_stats.detection_count > 0

@pytest.mark.asyncio
async def test_generate_daily_report(stats_manager, sample_detection_data, db_session):
    """Test de génération de rapport journalier."""
    report = await stats_manager.generate_daily_report()
    
    assert isinstance(report, dict)
    assert "total_detections" in report
    assert "average_confidence" in report
    assert "top_tracks" in report
    assert "top_artists" in report

@pytest.mark.asyncio
async def test_trend_analysis(stats_manager, db_session):
    """Test d'analyse des tendances."""
    trends = await stats_manager.get_trend_analysis(days=7)
    
    assert isinstance(trends, dict)
    assert "detection_trend" in trends
    assert "confidence_trend" in trends
    assert "top_trending_artists" in trends
    assert "top_trending_tracks" in trends

@pytest.mark.asyncio
async def test_artist_stats_update(stats_manager, sample_detection_data, db_session):
    """Test de mise à jour des statistiques d'artiste."""
    await stats_manager.update_detection_stats(sample_detection_data)
    
    artist_stats = db_session.query(ArtistStats).first()
    assert artist_stats is not None
    assert artist_stats.total_plays > 0
    assert artist_stats.total_play_time > timedelta()

@pytest.mark.asyncio
async def test_track_stats_update(stats_manager, sample_detection_data, db_session):
    """Test de mise à jour des statistiques de piste."""
    await stats_manager.update_detection_stats(sample_detection_data)
    
    track_stats = db_session.query(TrackStats).first()
    assert track_stats is not None
    assert track_stats.detection_count > 0
    assert track_stats.total_play_time > timedelta()
    assert track_stats.average_confidence > 0

@pytest.mark.asyncio
async def test_station_stats_update(stats_manager, sample_detection_data, db_session):
    """Test de mise à jour des statistiques de station."""
    await stats_manager.update_detection_stats(sample_detection_data)
    
    station_stats = db_session.query(StationStats).first()
    assert station_stats is not None
    assert station_stats.total_detections > 0
    assert station_stats.total_play_time > timedelta()
    assert station_stats.average_confidence > 0 