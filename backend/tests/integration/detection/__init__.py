"""
Detection integration tests for the SODAV Monitor backend.

This package contains integration tests for the detection system:

- test_detection_integration.py: Basic integration tests for detection functionality
- test_detection_pipeline.py: Tests for the complete detection pipeline

These tests verify that the detection system works correctly with the database,
external services, and other components. They test the end-to-end flow of audio
processing, fingerprint generation, and music recognition.

Key aspects tested:
- Local detection with database fingerprints
- Hierarchical detection process (local → MusicBrainz → Audd)
- Speech vs. music content identification
- Detection data persistence
- Integration with analytics system
""" 