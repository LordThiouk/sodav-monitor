"""Test configuration for analytics tests."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock

import numpy as np
import pytest
from sqlalchemy.orm import Session


class AsyncTransactionContext:
    """Mock SQLAlchemy async transaction context."""

    def __init__(self, session):
        self.session = session
        self.execute = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self):
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        if exc_type is not None:
            await self.session.rollback()
        else:
            await self.session.commit()
        return None


class BeginContextManager:
    """Mock SQLAlchemy begin context manager."""

    def __init__(self, session):
        self.session = session
        self.transaction = AsyncTransactionContext(session)

    async def __aenter__(self):
        """Enter the async context manager."""
        return self.transaction

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        return None


class AsyncMockSession:
    """Mock SQLAlchemy async session with proper transaction support."""

    def __init__(self):
        self.execute = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.close = AsyncMock()

        # Configure execute to return a mock result
        mock_result = AsyncMock()
        mock_result.first = AsyncMock(
            return_value={
                "track_id": 1,
                "artist": "Test Artist",
                "title": "Test Track",
                "detection_count": 10,
                "total_play_time": 3600,
                "artist_count": 5,
                "artist_play_time": 1800,
                "play_count": 3,
                "station_play_time": 900,
            }
        )
        self.execute.return_value = mock_result

    async def __aenter__(self):
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        return None

    def begin(self):
        """Return self as the transaction context manager."""
        return self


@pytest.fixture
def mock_db_session():
    """Create a mock database session with async support."""
    return AsyncMockSession()


@pytest.fixture
def sample_track():
    """Create a sample track for testing."""
    return {
        "id": 1,
        "title": "Test Track",
        "artist": "Test Artist",
        "duration": 180.0,
        "detection_count": 10,
        "total_play_time": 3600,
        "average_confidence": 0.85,
        "last_detected": datetime.now(),
    }


@pytest.fixture
def sample_artist():
    """Create a sample artist for testing."""
    return {
        "id": 1,
        "name": "Test Artist",
        "detection_count": 50,
        "total_play_time": 18000,
        "average_confidence": 0.88,
        "last_detected": datetime.now(),
    }


@pytest.fixture
def sample_station():
    """Create a sample radio station for testing."""
    return {
        "id": 1,
        "name": "Test Radio",
        "stream_url": "http://test.stream/audio",
        "status": "active",
        "is_active": True,
        "detection_count": 100,
        "total_play_time": 36000,
        "last_detection": datetime.now(),
    }


@pytest.fixture
def sample_detections():
    """Create a list of sample detections for testing."""
    base_time = datetime.now()
    return [
        {
            "id": i,
            "station_id": 1,
            "track_id": i % 5 + 1,
            "confidence": 0.9 + (i % 10) / 100,
            "detected_at": base_time - timedelta(minutes=i),
            "play_duration": timedelta(seconds=180),
        }
        for i in range(20)
    ]


@pytest.fixture
def sample_temporal_data():
    """Create sample temporal analytics data."""
    base_time = datetime.now()
    return {
        "hourly": [
            {
                "hour": base_time.replace(minute=0, second=0, microsecond=0) - timedelta(hours=i),
                "count": np.random.randint(10, 100),
            }
            for i in range(24)
        ],
        "daily": [
            {
                "date": base_time.replace(hour=0, minute=0, second=0, microsecond=0)
                - timedelta(days=i),
                "count": np.random.randint(100, 1000),
            }
            for i in range(7)
        ],
        "monthly": [
            {
                "month": base_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                - timedelta(days=i * 30),
                "count": np.random.randint(1000, 10000),
            }
            for i in range(12)
        ],
    }


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = Mock()
    redis.publish = AsyncMock()
    redis.set = AsyncMock()
    redis.get = AsyncMock()
    redis.delete = AsyncMock()
    return redis
