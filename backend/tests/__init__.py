"""Test suite for the SODAV Monitor backend.

Structure:
- analytics/: Tests for analytics and statistics
- api/: API endpoint tests
- core/: Core functionality tests
- detection/: Music detection tests
  - audio_processor/: Audio processing tests
  - external/: External service tests
- reports/: Report generation tests
- utils/: Utility function tests
"""

# Import only what's needed for basic test setup
import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
