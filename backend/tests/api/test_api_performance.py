"""Performance tests for API endpoints."""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models.models import (
    Artist,
    RadioStation,
    StationStatus,
    Track,
    TrackDetection,
    TrackStats,
)


@pytest.fixture
def bulk_detections(
    db_session: Session, test_track: Track, test_station: RadioStation
) -> List[TrackDetection]:
    """Create bulk detections for performance testing."""
    detections = []
    base_time = datetime.utcnow() - timedelta(days=30)

    # Create 1000 detections
    for i in range(1000):
        detection = TrackDetection(
            track_id=test_track.id,
            station_id=test_station.id,
            confidence=0.9 + (i % 10) * 0.01,
            detected_at=base_time + timedelta(hours=i),
            play_duration=timedelta(minutes=3),
            is_valid=True,
            fingerprint="test_fingerprint",
            audio_hash=f"test_hash_{i}",
        )
        detections.append(detection)

    db_session.add_all(detections)
    db_session.commit()

    # Verify test data
    for detection in detections:
        if not detection.track or not detection.station:
            raise ValueError("Detection created without track or station")
        if not detection.track.artist:
            raise ValueError("Track created without artist")

    return detections


@pytest.mark.benchmark
class TestAPIPerformance:
    """Performance tests for API endpoints."""

    def test_music_detection_performance(
        self,
        benchmark,
        client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager,
    ):
        """Benchmark music detection endpoint.

        Performance targets:
        - Response time < 100ms
        - Memory usage < 50MB
        - CPU usage < 50% single core
        """

        def run_detection():
            response = client.post(
                f"/api/channels/{test_station.id}/detect-music", headers=auth_headers
            )
            return response

        result = benchmark(run_detection)
        assert result.status_code == 200
        response_data = result.json()
        assert "status" in response_data
        assert response_data["status"] == "success"
        assert result.elapsed.total_seconds() < 0.1  # Response within 100ms

    def test_analytics_overview_performance(
        self,
        benchmark,
        client: TestClient,
        auth_headers: Dict[str, str],
        bulk_detections: List[TrackDetection],
    ):
        """Benchmark analytics overview endpoint.

        Performance targets:
        - Response time < 200ms
        - Memory usage < 100MB
        - Efficient database queries
        """

        def get_overview():
            return client.get("/api/analytics/overview", headers=auth_headers)

        result = benchmark(get_overview)
        assert result.status_code == 200
        assert result.elapsed.total_seconds() < 0.2  # Response within 200ms

    def test_trend_analysis_performance(
        self,
        benchmark,
        client: TestClient,
        auth_headers: Dict[str, str],
        bulk_detections: List[TrackDetection],
    ):
        """Benchmark trend analysis endpoint.

        Performance targets:
        - Response time < 300ms
        - Memory usage < 150MB
        - Efficient data aggregation
        """

        def get_trends():
            return client.get("/api/analytics/trends", params={"days": 30}, headers=auth_headers)

        result = benchmark(get_trends)
        assert result.status_code == 200
        assert result.elapsed.total_seconds() < 0.3  # Response within 300ms

    def test_report_generation_performance(
        self,
        benchmark,
        client: TestClient,
        auth_headers: Dict[str, str],
        bulk_detections: List[TrackDetection],
    ):
        """Benchmark report generation endpoint.

        Performance targets:
        - Response time < 500ms
        - Memory usage < 200MB
        - Efficient data processing
        """

        def generate_report():
            return client.post(
                "/api/reports/generate",
                json={
                    "type": "daily",
                    "format": "pdf",
                    "date": datetime.utcnow().date().isoformat(),
                    "include_graphs": True,
                    "language": "fr",
                },
                headers=auth_headers,
            )

        result = benchmark(generate_report)
        assert result.status_code == 200
        data = result.json()
        assert "report_type" in data
        assert "metrics" in data
        assert "top_tracks" in data
        assert "top_artists" in data
        assert result.elapsed.total_seconds() < 0.5  # Response within 500ms

    def test_bulk_stats_query_performance(
        self,
        benchmark,
        client: TestClient,
        auth_headers: Dict[str, str],
        bulk_detections: List[TrackDetection],
    ):
        """Benchmark bulk statistics query performance.

        Performance targets:
        - Response time < 300ms
        - Memory usage < 150MB
        - Efficient database queries
        """

        def get_bulk_stats():
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            return client.get(
                "/api/analytics/stats",
                params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                headers=auth_headers,
            )

        result = benchmark(get_bulk_stats)
        assert result.status_code == 200
        assert result.elapsed.total_seconds() < 0.3  # Response within 300ms

    @pytest.mark.parametrize("n_requests", [10, 50, 100])
    def test_concurrent_detection_performance(
        self,
        benchmark,
        client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        mock_radio_manager,
        n_requests: int,
    ):
        """Benchmark concurrent music detection requests.

        Performance targets:
        - Average response time < 500ms
        - No request failures
        - Linear scaling up to 100 concurrent requests
        """

        def run_concurrent_detections():
            responses = []
            for _ in range(n_requests):
                response = client.post(
                    f"/api/channels/{test_station.id}/detect-music", headers=auth_headers
                )
                responses.append(response)
            return responses

        results = benchmark(run_concurrent_detections)
        assert all(r.status_code == 200 for r in results)
        avg_time = sum(r.elapsed.total_seconds() for r in results) / len(results)
        assert avg_time < 0.5  # Average response time under 500ms

    def test_analytics_export_performance(
        self,
        benchmark,
        client: TestClient,
        auth_headers: Dict[str, str],
        bulk_detections: List[TrackDetection],
    ):
        """Benchmark analytics export endpoint.

        Performance targets:
        - Response time < 500ms
        - Memory usage < 200MB
        - Efficient data serialization
        """

        def export_analytics():
            return client.get(
                "/api/analytics/export", params={"format": "json"}, headers=auth_headers
            )

        result = benchmark(export_analytics)
        assert result.status_code == 200
        assert result.elapsed.total_seconds() < 0.5  # Export within 500ms

    def test_station_stats_performance(
        self,
        benchmark,
        client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        bulk_detections: List[TrackDetection],
    ):
        """Benchmark station statistics endpoint.

        Performance targets:
        - Response time < 200ms
        - Memory usage < 100MB
        - Efficient data aggregation
        """

        def get_station_stats():
            return client.get(
                f"/api/channels/{test_station.id}/stats",
                params={"period": 24, "include_hourly": True},  # Last 24 hours
                headers=auth_headers,
            )

        result = benchmark(get_station_stats)
        assert result.status_code == 200
        data = result.json()

        # Verify response structure
        assert "station_id" in data
        assert "name" in data
        assert "status" in data
        assert "total_detections" in data
        assert "detections_24h" in data
        assert "total_play_time" in data
        assert "hourly_detections" in data
        assert isinstance(data["hourly_detections"], list)

        assert result.elapsed.total_seconds() < 0.2  # Response within 200ms

    def test_detection_history_performance(
        self,
        benchmark,
        client: TestClient,
        auth_headers: Dict[str, str],
        test_station: RadioStation,
        bulk_detections: List[TrackDetection],
    ):
        """Benchmark detection history endpoint.

        Performance targets:
        - Response time < 200ms
        - Memory usage < 100MB
        - Efficient pagination
        """

        def get_detection_history():
            return client.get(
                f"/api/channels/{test_station.id}/detections",
                params={"page": 1, "limit": 100, "search": None, "label": None},
                headers=auth_headers,
            )

        result = benchmark(get_detection_history)
        assert result.status_code == 200
        data = result.json()

        # Verify response structure
        assert "detections" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
        assert "has_next" in data
        assert "has_prev" in data
        assert "labels" in data
        assert "station" in data

        # Verify data types
        assert isinstance(data["detections"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["pages"], int)
        assert isinstance(data["has_next"], bool)
        assert isinstance(data["has_prev"], bool)
        assert isinstance(data["labels"], list)
        assert isinstance(data["station"], dict)

        assert result.elapsed.total_seconds() < 0.2  # Response within 200ms

    def test_search_basic(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        bulk_detections: List[TrackDetection],
        db_session: Session,
    ):
        """Basic test for search endpoint functionality."""
        # Verify test data
        assert len(bulk_detections) > 0, "No test detections available"

        # Get a sample track title to search for
        sample_track = bulk_detections[0].track
        assert sample_track is not None, "Sample track not found"
        search_term = sample_track.title

        # Make the search request
        response = client.get(
            "/api/detections/search/",
            params={"query": search_term, "limit": 10, "skip": 0},
            headers=auth_headers,
        )

        # Print response for debugging
        print(f"\nSearch response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response content: {response.content}")

        # Basic assertions
        assert response.status_code == 200, f"Search failed with status {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "No results found"

        # Verify first result structure
        first_result = data[0]
        assert "id" in first_result, "Missing id in result"
        assert "track" in first_result, "Missing track in result"
        assert "station" in first_result, "Missing station in result"
        assert "detected_at" in first_result, "Missing detected_at in result"
        assert "confidence" in first_result, "Missing confidence in result"

        # Verify track data
        track_data = first_result["track"]
        assert "title" in track_data, "Missing track title"
        assert "artist" in track_data, "Missing artist name"

        # Verify station data
        station_data = first_result["station"]
        assert "name" in station_data, "Missing station name"
        assert "stream_url" in station_data, "Missing stream_url"
        assert station_data["stream_url"], "Stream URL should not be empty"

    def test_search_performance(
        self,
        benchmark,
        client: TestClient,
        auth_headers: Dict[str, str],
        bulk_detections: List[TrackDetection],
    ):
        """Benchmark search endpoint.

        Performance targets:
        - Response time < 200ms
        - Memory usage < 100MB
        - Efficient search indexing
        """

        def search_detections():
            return client.get(
                "/api/detections/search/",
                params={"query": "test", "limit": 50, "skip": 0},
                headers=auth_headers,
            )

        # Ensure test data is properly set up
        if not bulk_detections:
            raise ValueError("No test detections available")

        # Verify test data has all required fields
        for detection in bulk_detections:
            if not detection.track or not detection.station:
                raise ValueError("Detection missing track or station")
            if not detection.track.artist:
                raise ValueError("Track missing artist")
            if not detection.station.stream_url:
                raise ValueError("Station missing stream_url")

        result = benchmark(search_detections)
        assert result.status_code == 200
        data = result.json()

        # Verify response structure
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify each detection has required fields
        for detection in data:
            assert "id" in detection
            assert "track" in detection
            assert "station" in detection
            assert "detected_at" in detection
            assert "confidence" in detection
            assert "play_duration" in detection

            # Verify track data
            assert "title" in detection["track"]
            assert "artist" in detection["track"]

            # Verify station data
            assert "name" in detection["station"]
            assert "stream_url" in detection["station"]
            assert detection["station"]["stream_url"], "Stream URL should not be empty"
