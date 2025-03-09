"""Tests for the report generator module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from backend.reports.generator import ReportGenerator
from backend.schemas.base import ReportCreate
from backend.models.models import TrackDetection, RadioStation, Track

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = Mock()
    session.query = Mock()
    return session

@pytest.fixture
def mock_track():
    """Create a mock track."""
    track = Mock()
    track.id = 1
    track.title = "Test Track"
    track.artist = "Test Artist"
    return track

@pytest.fixture
def mock_station():
    """Create a mock radio station."""
    station = Mock()
    station.id = 1
    station.name = "Test Station"
    station.region = "Test Region"
    station.language = "Test Language"
    station.status = Mock(value="active")
    station.last_checked = datetime.now()
    return station

@pytest.fixture
def mock_detection(mock_track, mock_station):
    """Create a mock track detection."""
    detection = Mock()
    detection.id = 1
    detection.track = mock_track
    detection.station = mock_station
    detection.detected_at = datetime.now()
    detection.confidence = 0.95
    return detection

@pytest.fixture
def report_generator(mock_db_session):
    """Create a ReportGenerator instance with a mock session."""
    return ReportGenerator(mock_db_session)

@pytest.mark.asyncio
async def test_generate_detection_report(report_generator, mock_db_session, mock_detection):
    """Test generating a detection report."""
    # Setup mock query
    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [mock_detection]
    mock_db_session.query.return_value = mock_query
    
    # Setup test data
    start_date = datetime(2024, 3, 1)
    end_date = datetime(2024, 3, 31)
    
    # Mock pandas DataFrame
    with patch('pandas.DataFrame.to_excel') as mock_to_excel:
        filepath = await report_generator._generate_detection_report(start_date, end_date)
        
        # Verify the query was constructed correctly
        mock_db_session.query.assert_called_with(TrackDetection)
        mock_query.filter.assert_called_once()
        
        # Verify the report was generated
        assert filepath == f"reports/detection_report_20240301_20240331.xlsx"
        mock_to_excel.assert_called_once()

@pytest.mark.asyncio
async def test_generate_detection_report_with_filters(report_generator, mock_db_session, mock_detection):
    """Test generating a detection report with filters."""
    # Setup mock query
    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.join.return_value = mock_query
    mock_query.all.return_value = [mock_detection]
    mock_db_session.query.return_value = mock_query
    
    # Setup test data
    start_date = datetime(2024, 3, 1)
    end_date = datetime(2024, 3, 31)
    filters = {
        "station": "Test Station",
        "artist": "Test Artist"
    }
    
    # Mock pandas DataFrame
    with patch('pandas.DataFrame.to_excel') as mock_to_excel:
        filepath = await report_generator._generate_detection_report(start_date, end_date, filters)
        
        # Verify the query was constructed correctly with filters
        mock_db_session.query.assert_called_with(TrackDetection)
        assert mock_query.filter.call_count == 3  # Date range, artist filter, and station filter
        mock_query.join.assert_called_once()  # For station filter
        
        # Verify the report was generated
        assert filepath == f"reports/detection_report_20240301_20240331.xlsx"
        mock_to_excel.assert_called_once()

@pytest.mark.asyncio
async def test_generate_station_report(report_generator, mock_db_session, mock_station, mock_detection):
    """Test generating a station report."""
    # Setup mock queries
    mock_station_query = Mock()
    mock_station_query.all.return_value = [mock_station]
    
    mock_detection_query = Mock()
    mock_detection_query.filter.return_value = mock_detection_query
    mock_detection_query.all.return_value = [mock_detection]
    
    # Configure mock_db_session to return different queries for different calls
    def side_effect(model):
        if model == RadioStation:
            return mock_station_query
        elif model == TrackDetection:
            return mock_detection_query
        return Mock()
    
    mock_db_session.query.side_effect = side_effect
    
    # Setup test data
    start_date = datetime(2024, 3, 1)
    end_date = datetime(2024, 3, 31)
    
    # Mock pandas DataFrame
    with patch('pandas.DataFrame.to_excel') as mock_to_excel:
        filepath = await report_generator._generate_station_report(start_date, end_date)
        
        # Verify the queries were constructed correctly
        assert mock_db_session.query.call_count == 2  # One for stations, one for detections
        mock_detection_query.filter.assert_called_once()  # For date range filter
        
        # Verify the report was generated
        assert filepath == f"reports/station_report_20240301_20240331.xlsx"
        mock_to_excel.assert_called_once()

@pytest.mark.asyncio
async def test_generate_report_invalid_type(report_generator):
    """Test generating a report with an invalid type."""
    report_data = ReportCreate(
        title="Test Report",
        type="invalid",
        format="xlsx",
        period_start=datetime(2024, 3, 1),
        period_end=datetime(2024, 3, 31)
    )
    
    with pytest.raises(ValueError, match="Unsupported report type: invalid"):
        await report_generator.generate_report(report_data)

@pytest.mark.asyncio
async def test_generate_report_with_empty_data(report_generator, mock_db_session):
    """Test generating a report with no data."""
    # Setup mock query that returns no data
    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = []
    mock_db_session.query.return_value = mock_query
    
    # Setup test data
    start_date = datetime(2024, 3, 1)
    end_date = datetime(2024, 3, 31)
    
    # Mock pandas DataFrame
    with patch('pandas.DataFrame.to_excel') as mock_to_excel:
        filepath = await report_generator._generate_detection_report(start_date, end_date)
        
        # Verify empty DataFrame was handled correctly
        mock_to_excel.assert_called_once()
        assert filepath == f"reports/detection_report_20240301_20240331.xlsx"

@pytest.mark.asyncio
async def test_generate_report_date_validation(report_generator):
    """Test report generation with invalid date range."""
    report_data = ReportCreate(
        title="Test Report",
        type="detection",
        format="xlsx",
        period_start=datetime(2024, 3, 31),
        period_end=datetime(2024, 3, 1)  # End date before start date
    )
    
    with pytest.raises(ValueError, match="End date must be after start date"):
        await report_generator.generate_report(report_data)

@pytest.mark.asyncio
async def test_generate_report_with_future_dates(report_generator):
    """Test report generation with future dates."""
    future_date = datetime.now() + timedelta(days=30)
    report_data = ReportCreate(
        title="Test Report",
        type="detection",
        format="xlsx",
        period_start=datetime.now(),
        period_end=future_date
    )
    
    with pytest.raises(ValueError, match="Cannot generate reports for future dates"):
        await report_generator.generate_report(report_data) 