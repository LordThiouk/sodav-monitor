"""
Analytics integration tests for the SODAV Monitor backend.

This package contains integration tests for the analytics system:

- test_analytics_integration.py: Basic integration tests for analytics functionality
- test_analytics_pipeline.py: Tests for the complete analytics pipeline

These tests verify that the analytics system works correctly with the database,
detection system, and other components. They test the end-to-end flow of data
from detection to analytics processing and report generation.

Key aspects tested:
- Statistics updates after detections
- Track, artist, and station statistics
- Analytics data generation
- Trend analysis
"""
