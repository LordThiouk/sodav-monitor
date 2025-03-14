"""API endpoint tests for the SODAV Monitor system.

This package contains tests for the API endpoints:

- test_detections_api.py: Tests for detection endpoints
- test_music_detection_api.py: Tests for music detection endpoints
- test_analytics_api.py: Tests for analytics endpoints
- test_reports_api.py: Tests for report generation endpoints
- test_reports_router.py: Tests for the reorganized reports router
- test_websocket.py: Tests for WebSocket communication
- test_api_performance.py: Performance tests for API endpoints

These tests verify that the API endpoints correctly handle requests,
validate input data, and return appropriate responses.
"""

from .test_websocket import *  # noqa: F403
