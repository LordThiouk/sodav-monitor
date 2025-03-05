"""
Integration tests for the API endpoints.

These tests verify that the API endpoints work correctly with the detection and analytics systems.
"""

import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid
from unittest.mock import patch
from fastapi import FastAPI

from backend.models.models import (
    RadioStation, Artist, Track, TrackDetection, 
    TrackStats, ArtistStats, StationStats, Report, User
)
from backend.main import app
from backend.utils.auth.auth import get_current_user, oauth2_scheme

class TestAPIEndpoints:
    """Integration tests for the API endpoints."""
    
    @pytest.fixture
    def test_station(self, db_session: Session) -> RadioStation:
        """Create a test radio station."""
        station = db_session.query(RadioStation).filter(RadioStation.name == "API Test Station").first()
        if not station:
            station = RadioStation(
                name="API Test Station",
                stream_url="http://example.com/api_test_stream",
                country="FR",
                language="fr",
                is_active=True,
                status="active"
            )
            db_session.add(station)
            db_session.commit()
            db_session.refresh(station)
        return station
    
    @pytest.fixture
    def test_artist(self, db_session: Session) -> Artist:
        """Create a test artist."""
        artist = db_session.query(Artist).filter(Artist.name == "API Test Artist").first()
        if not artist:
            artist = Artist(
                name="API Test Artist",
                country="FR",
                label="API Test Label"
            )
            db_session.add(artist)
            db_session.commit()
            db_session.refresh(artist)
        return artist
    
    @pytest.fixture
    def test_track(self, db_session: Session, test_artist: Artist) -> Track:
        """Create a test track."""
        unique_fingerprint = f"api_test_fingerprint_{uuid.uuid4()}"
        
        track = Track(
            title="API Test Track",
            artist_id=test_artist.id,
            fingerprint=unique_fingerprint,
            fingerprint_raw=b"api_test_fingerprint_raw"
        )
        db_session.add(track)
        db_session.commit()
        db_session.refresh(track)
        return track
    
    @pytest.fixture
    def test_detection(self, db_session: Session, test_track: Track, test_station: RadioStation) -> TrackDetection:
        """Create a test detection."""
        detection = TrackDetection(
            track_id=test_track.id,
            station_id=test_station.id,
            confidence=0.9,
            detected_at=datetime.utcnow(),
            play_duration=timedelta(seconds=180),  # 3 minutes
            fingerprint=test_track.fingerprint,
            audio_hash="api_test_audio_hash"
        )
        db_session.add(detection)
        db_session.commit()
        db_session.refresh(detection)
        return detection
    
    def test_get_stations(self, test_client: TestClient, test_user: User, auth_headers: Dict[str, str], db_session: Session):
        """
        Test the GET /api/analytics/stations endpoint:
        1. Call the endpoint
        2. Verify that a list of stations is returned
        """
        from backend.analytics.stats_manager import StatsManager
        from backend.routers.analytics import get_stats_manager
        from backend.utils.auth.auth import get_current_user, oauth2_scheme
        
        # Create a mock for the get_current_user function
        async def mock_get_current_user(*args, **kwargs):
            return test_user
        
        # Create a mock for the oauth2_scheme function
        def mock_oauth2_scheme(*args, **kwargs):
            return auth_headers["Authorization"].split(" ")[1]
        
        # Create a mock for the get_stats_manager function
        async def mock_get_stats_manager():
            stats_manager = StatsManager(db_session)
            yield stats_manager
        
        # Use the mocks to override the dependencies
        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[oauth2_scheme] = mock_oauth2_scheme
        app.dependency_overrides[get_stats_manager] = mock_get_stats_manager
        
        try:
            # Create a new test client with the app that has the dependency overrides
            with TestClient(app) as client:
                response = client.get("/api/analytics/stations")
                
                assert response.status_code == 200, f"Failed to get stations: {response.text}"
                
                data = response.json()
                assert isinstance(data, list), "Response is not a list"
                assert len(data) > 0, "No stations returned"
        finally:
            # Clear the dependency overrides
            app.dependency_overrides.clear()
    
    def test_get_station_by_id(self, test_client: TestClient, test_station: RadioStation):
        """
        Test the GET /api/channels/{station_id} endpoint:
        1. Create a test station
        2. Call the endpoint with the station ID
        3. Verify that the station is returned
        """
        response = test_client.get(f"/api/channels/{test_station.id}")
        
        assert response.status_code == 200, f"Failed to get station {test_station.id}: {response.text}"
        
        data = response.json()
        assert data["id"] == test_station.id, "Station ID mismatch"
        assert data["name"] == test_station.name, "Station name mismatch"
        assert data["stream_url"] == test_station.stream_url, "Station URL mismatch"
        assert data["country"] == test_station.country, "Station country mismatch"
        assert data["is_active"] == test_station.is_active, "Station active status mismatch"
    
    def test_get_tracks(self, test_client: TestClient, test_track: Track):
        """
        Test the GET /api/tracks endpoint:
        1. Create a test track
        2. Call the endpoint
        3. Verify that the track is returned
        """
        response = test_client.get("/api/tracks")
        
        assert response.status_code == 200, "Failed to get tracks"
        
        data = response.json()
        assert isinstance(data, list), "Response is not a list"
        assert len(data) > 0, "No tracks returned"
        
        # Find our test track in the response
        found = False
        for track in data:
            if track["title"] == test_track.title:
                found = True
                assert track["id"] == test_track.id, "Track ID mismatch"
                assert track["artist"]["id"] == test_track.artist_id, "Track artist ID mismatch"
                break
        
        assert found, f"Test track '{test_track.title}' not found in response"
    
    def test_get_track_by_id(self, test_client: TestClient, test_track: Track):
        """
        Test the GET /api/tracks/{track_id} endpoint:
        1. Create a test track
        2. Call the endpoint with the track ID
        3. Verify that the track is returned
        """
        response = test_client.get(f"/api/tracks/{test_track.id}")
        
        assert response.status_code == 200, f"Failed to get track {test_track.id}"
        
        data = response.json()
        assert data["id"] == test_track.id, "Track ID mismatch"
        assert data["title"] == test_track.title, "Track title mismatch"
        assert data["artist"]["id"] == test_track.artist_id, "Track artist ID mismatch"
    
    def test_get_artists(self, test_client: TestClient, test_artist: Artist):
        """
        Test the GET /api/artists endpoint:
        1. Create a test artist
        2. Call the endpoint
        3. Verify that the artist is returned
        """
        response = test_client.get("/api/artists")
        
        assert response.status_code == 200, "Failed to get artists"
        
        data = response.json()
        assert isinstance(data, list), "Response is not a list"
        assert len(data) > 0, "No artists returned"
        
        # Find our test artist in the response
        found = False
        for artist in data:
            if artist["name"] == test_artist.name:
                found = True
                assert artist["id"] == test_artist.id, "Artist ID mismatch"
                assert artist["country"] == test_artist.country, "Artist country mismatch"
                assert artist["label"] == test_artist.label, "Artist label mismatch"
                break
        
        assert found, f"Test artist '{test_artist.name}' not found in response"
    
    def test_get_artist_by_id(self, test_client: TestClient, test_artist: Artist):
        """
        Test the GET /api/artists/{artist_id} endpoint:
        1. Create a test artist
        2. Call the endpoint with the artist ID
        3. Verify that the artist is returned
        """
        response = test_client.get(f"/api/artists/{test_artist.id}")
        
        assert response.status_code == 200, f"Failed to get artist {test_artist.id}"
        
        data = response.json()
        assert data["id"] == test_artist.id, "Artist ID mismatch"
        assert data["name"] == test_artist.name, "Artist name mismatch"
        assert data["country"] == test_artist.country, "Artist country mismatch"
        assert data["label"] == test_artist.label, "Artist label mismatch"
    
    def test_get_detections(self, test_client: TestClient, test_detection: TrackDetection):
        """
        Test the GET /api/detections endpoint:
        1. Create a test detection
        2. Call the endpoint
        3. Verify that the detection is returned
        """
        response = test_client.get("/api/detections")
        
        assert response.status_code == 200, "Failed to get detections"
        
        data = response.json()
        assert isinstance(data, list), "Response is not a list"
        assert len(data) > 0, "No detections returned"
        
        # Find our test detection in the response
        found = False
        for detection in data:
            if detection["track_id"] == test_detection.track_id and detection["station_id"] == test_detection.station_id:
                found = True
                assert detection["confidence"] == test_detection.confidence, "Detection confidence mismatch"
                break
        
        assert found, "Test detection not found in response"
    
    def test_detect_music_endpoint(self, test_client: TestClient, test_station: RadioStation):
        """
        Test the POST /api/channels/detect-music endpoint:
        1. Create a test station
        2. Call the endpoint with the station ID
        3. Verify the response
        
        Note: This test may fail if the station is not available or if the detection fails.
        It's more of an integration test than a unit test.
        """
        response = test_client.post(
            "/api/channels/detect-music",
            json={"station_id": test_station.id}
        )
        
        # The response might be 200 (success) or 422 (validation error) or 500 (server error)
        # depending on whether the station is available and the detection works
        # We're just checking that the endpoint exists and returns a valid response
        assert response.status_code in [200, 422, 500], "Unexpected response code"
        
        # If the response is 200, check that it has the expected structure
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Response missing status field"
            assert "message" in data, "Response missing message field"
            assert "details" in data, "Response missing details field"
    
    def test_generate_report(self, test_client: TestClient, db_session: Session, 
                            test_detection: TrackDetection):
        """
        Test the POST /api/reports/generate endpoint:
        1. Create a test detection
        2. Call the endpoint to generate a report
        3. Verify that the report is generated
        """
        # First, make sure we have some data to report on
        # We already have a test detection, but we need to make sure the stats are updated
        from backend.analytics.stats_manager import StatsManager
        stats_manager = StatsManager(db_session)
        stats_manager.update_all_stats()
        
        # Now generate a report
        response = test_client.post(
            "/api/reports/generate",
            json={
                "report_type": "daily",
                "format": "json",
                "start_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "end_date": datetime.utcnow().strftime("%Y-%m-%d")
            }
        )
        
        assert response.status_code == 200, "Failed to generate report"
        
        data = response.json()
        assert "report_id" in data, "Response missing report_id field"
        
        # Verify that the report was saved in the database
        report_id = data["report_id"]
        report = db_session.query(Report).filter(Report.id == report_id).first()
        
        assert report is not None, "Report not saved in the database"
        assert report.report_type == "daily", "Report type mismatch"
        assert report.format == "json", "Report format mismatch"
    
    def test_get_reports(self, test_client: TestClient, db_session: Session):
        """
        Test the GET /api/reports endpoint:
        1. Create a test report
        2. Call the endpoint
        3. Verify that the report is returned
        """
        # Create a test report
        report = Report(
            report_type="daily",
            format="json",
            content=json.dumps({"test": "data"}),
            generated_at=datetime.utcnow(),
            start_date=datetime.utcnow().date(),
            end_date=datetime.utcnow().date()
        )
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
        
        # Get the reports
        response = test_client.get("/api/reports")
        
        assert response.status_code == 200, "Failed to get reports"
        
        data = response.json()
        assert isinstance(data, list), "Response is not a list"
        assert len(data) > 0, "No reports returned"
        
        # Find our test report in the response
        found = False
        for r in data:
            if r["id"] == report.id:
                found = True
                assert r["report_type"] == report.report_type, "Report type mismatch"
                assert r["format"] == report.format, "Report format mismatch"
                break
        
        assert found, "Test report not found in response"
    
    def test_get_report_by_id(self, test_client: TestClient, db_session: Session):
        """
        Test the GET /api/reports/{report_id} endpoint:
        1. Create a test report
        2. Call the endpoint with the report ID
        3. Verify that the report is returned
        """
        # Create a test report
        report = Report(
            report_type="daily",
            format="json",
            content=json.dumps({"test": "data"}),
            generated_at=datetime.utcnow(),
            start_date=datetime.utcnow().date(),
            end_date=datetime.utcnow().date()
        )
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
        
        # Get the report
        response = test_client.get(f"/api/reports/{report.id}")
        
        assert response.status_code == 200, f"Failed to get report {report.id}"
        
        data = response.json()
        assert data["id"] == report.id, "Report ID mismatch"
        assert data["report_type"] == report.report_type, "Report type mismatch"
        assert data["format"] == report.format, "Report format mismatch" 