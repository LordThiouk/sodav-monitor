"""
Integration tests for the SODAV Monitor backend.

These tests verify the interaction between different components of the system,
ensuring they work together correctly in real-world scenarios.

This package is organized into the following subpackages:

- api/: Tests for API endpoints integration
  - test_api_endpoints.py: Tests for all API endpoints
  - test_api_integration.py: Tests for API integration with other components

- detection/: Tests for detection system integration
  - test_detection_integration.py: Basic integration tests for detection
  - test_detection_pipeline.py: Tests for the complete detection pipeline

- analytics/: Tests for analytics system integration
  - test_analytics_integration.py: Basic integration tests for analytics
  - test_analytics_pipeline.py: Tests for the complete analytics pipeline

The integration tests use a shared test database and fixtures defined in conftest.py.
They focus on testing the interaction between components rather than individual
unit functionality.
"""

import os
import sys

import pytest

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
