"""Tests for external music recognition services.

This package contains tests for external service integrations:

- test_external_services.py: Tests for general external service functionality
- test_musicbrainz_recognizer.py: Tests for MusicBrainz/AcoustID integration

These tests verify that the SODAV Monitor system correctly interacts with
external music recognition services like MusicBrainz, AcoustID, and Audd.
"""

from .test_external_services import *  # noqa: F403
from .test_musicbrainz_recognizer import *  # noqa: F403
