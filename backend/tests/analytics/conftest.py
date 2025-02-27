"""Test configuration for analytics tests."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

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
        mock_result.first = AsyncMock(return_value={
            'track_id': 1,
            'artist': 'Test Artist',
            'title': 'Test Track',
            'detection_count': 10,
            'total_play_time': 3600,
            'artist_count': 5,
            'artist_play_time': 1800,
            'play_count': 3,
            'station_play_time': 900
        })
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
    """Create a mock database session."""
    session = MagicMock(spec=AsyncSession)
    
    # Configure execute to return a mock result
    mock_result = AsyncMock()
    mock_result.first.return_value = {
        'track_id': 1,
        'artist_id': 1,
        'artist': 'Test Artist',
        'title': 'Test Track',
        'detection_count': 10,
        'total_play_time': 3600,
        'artist_count': 5,
        'artist_play_time': 1800,
        'play_count': 3,
        'station_play_time': 900
    }
    mock_result.fetchall.return_value = [mock_result.first.return_value]
    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    
    # Create a transaction context that calls commit on exit
    transaction = AsyncMock()
    transaction.__aenter__ = AsyncMock(return_value=transaction)
    async def async_exit(exc_type, exc_val, exc_tb):
        if exc_type is None:
            await session.commit()
        else:
            await session.rollback()
        return None
    transaction.__aexit__ = AsyncMock(side_effect=async_exit)
    
    # Configure begin to return the transaction context
    session.begin = Mock(return_value=transaction)
    
    return session

@pytest.fixture
def mock_hourly_data():
    """Create mock hourly detection data."""
    current_time = datetime.now()
    hour_start = current_time.replace(minute=0, second=0, microsecond=0)
    
    return [
        {
            'hour': hour_start + timedelta(hours=i),
            'detection_count': 10 + i,
            'total_duration': 1800 + i * 300,
            'average_confidence': 0.9 + i * 0.01
        }
        for i in range(24)
    ]

@pytest.fixture
def mock_daily_data():
    """Create mock daily detection data."""
    current_time = datetime.now()
    day_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return [
        {
            'date': day_start - timedelta(days=i),
            'detection_count': 100 + i * 10,
            'total_duration': 18000 + i * 3600,
            'average_confidence': 0.92 + i * 0.005
        }
        for i in range(30)
    ]

@pytest.fixture
def mock_station_report_data():
    """Create mock station report data."""
    return [
        {
            'station_id': 1,
            'track_id': i,
            'title': f'Track {i}',
            'artist': f'Artist {i % 5}',
            'play_count': 10 + i,
            'total_duration': 1800 + i * 300,
            'average_confidence': 0.9 + (i % 10) * 0.01
        }
        for i in range(1, 11)
    ]

@pytest.fixture
def mock_artist_report_data():
    """Create mock artist report data."""
    return [
        {
            'artist_id': i,
            'artist': f'Artist {i}',
            'total_tracks': 5 + i,
            'total_plays': 50 + i * 10,
            'total_duration': 9000 + i * 1800,
            'average_confidence': 0.9 + (i % 10) * 0.01
        }
        for i in range(1, 6)
    ]

@pytest.fixture
def mock_concurrent_data():
    """Create mock data for concurrent processing tests."""
    current_time = datetime.now()
    
    return {
        'detections': [
            {
                'station_id': i % 3 + 1,
                'track_id': i % 5 + 1,
                'confidence': 0.9 + (i % 10) / 100,
                'play_duration': timedelta(seconds=180),
                'detected_at': current_time - timedelta(minutes=i)
            }
            for i in range(20)
        ],
        'reports': {
            'station': [
                {
                    'station_id': i,
                    'track_count': 100 + i * 10,
                    'total_duration': 36000 + i * 3600
                }
                for i in range(1, 4)
            ],
            'artist': [
                {
                    'artist_id': i,
                    'track_count': 50 + i * 5,
                    'total_duration': 18000 + i * 1800
                }
                for i in range(1, 4)
            ]
        }
    }

@pytest.fixture
def mock_error_data():
    """Create mock data for error handling tests."""
    return {
        'invalid_detection': {
            'station_id': 'invalid',  # Should be integer
            'track_id': None,  # Should not be None
            'confidence': 2.0,  # Should be between 0 and 1
            'play_duration': -100  # Should be positive
        },
        'missing_data': {
            'station_id': 1
            # Missing required fields
        },
        'database_error': SQLAlchemyError("Database error")
    }

@pytest.fixture
def sample_track():
    """Create a sample track for testing."""
    return {
        'id': 1,
        'title': 'Test Track',
        'artist': 'Test Artist',
        'duration': 180.0,
        'detection_count': 10,
        'total_play_time': 3600,
        'average_confidence': 0.85,
        'last_detected': datetime.now()
    }

@pytest.fixture
def sample_artist():
    """Create a sample artist for testing."""
    return {
        'id': 1,
        'name': 'Test Artist',
        'detection_count': 50,
        'total_play_time': 18000,
        'average_confidence': 0.88,
        'last_detected': datetime.now()
    }

@pytest.fixture
def sample_station():
    """Create a sample radio station for testing."""
    return {
        'id': 1,
        'name': 'Test Radio',
        'stream_url': 'http://test.stream/audio',
        'status': 'active',
        'is_active': True,
        'detection_count': 100,
        'total_play_time': 36000,
        'last_detection': datetime.now()
    }

@pytest.fixture
def sample_detections():
    """Create a list of sample detections for testing."""
    base_time = datetime.now()
    return [
        {
            'id': i,
            'station_id': 1,
            'track_id': i % 5 + 1,
            'confidence': 0.9 + (i % 10) / 100,
            'detected_at': base_time - timedelta(minutes=i),
            'play_duration': timedelta(seconds=180)
        }
        for i in range(20)
    ]

@pytest.fixture
def sample_temporal_data():
    """Create sample temporal analytics data."""
    base_time = datetime.now()
    return {
        'hourly': [
            {
                'hour': base_time.replace(minute=0, second=0, microsecond=0) - timedelta(hours=i),
                'count': np.random.randint(10, 100)
            }
            for i in range(24)
        ],
        'daily': [
            {
                'date': base_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i),
                'count': np.random.randint(100, 1000)
            }
            for i in range(7)
        ],
        'monthly': [
            {
                'month': base_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i*30),
                'count': np.random.randint(1000, 10000)
            }
            for i in range(12)
        ]
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