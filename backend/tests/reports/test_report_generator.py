"""Tests for the report generation module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
import pandas as pd

from backend.reports.generate_report import ReportGenerator
from backend.models.models import (
    Report, ReportType, ReportFormat, ReportStatus,
    Track, Artist, TrackDetection
)

@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    session = Mock(spec=Session)
    session.query = Mock(return_value=session)
    session.filter = Mock(return_value=session)
    session.first = Mock(return_value=None)
    return session

@pytest.fixture
def report_generator(db_session):
    """Create a ReportGenerator instance for testing."""
    return ReportGenerator(db_session)

@pytest.mark.asyncio
async def test_generate_daily_report(report_generator, db_session):
    """Test generation of daily report."""
    # Mock detection data
    mock_detections = [
        Mock(
            track=Mock(
                title="Test Track 1",
                artist="Test Artist 1",
                duration=180
            ),
            station=Mock(name="Test Station 1"),
            confidence=0.9,
            play_duration=timedelta(seconds=180),
            detected_at=datetime.now()
        ),
        Mock(
            track=Mock(
                title="Test Track 2",
                artist="Test Artist 2",
                duration=200
            ),
            station=Mock(name="Test Station 2"),
            confidence=0.85,
            play_duration=timedelta(seconds=200),
            detected_at=datetime.now()
        )
    ]
    
    db_session.query.return_value.filter.return_value.all.return_value = mock_detections
    
    report = await report_generator.generate_daily_report(
        date=datetime.now().date(),
        format=ReportFormat.CSV
    )
    
    assert report is not None
    assert report.type == ReportType.DAILY
    assert report.status == ReportStatus.COMPLETED
    assert report.format == ReportFormat.CSV
    assert report.file_path is not None

@pytest.mark.asyncio
async def test_generate_monthly_report(report_generator, db_session):
    """Test generation of monthly report."""
    # Mock monthly statistics
    mock_stats = [
        Mock(
            artist=Mock(name="Test Artist 1"),
            count=50,
            total_play_time=timedelta(hours=2)
        ),
        Mock(
            artist=Mock(name="Test Artist 2"),
            count=30,
            total_play_time=timedelta(hours=1)
        )
    ]
    
    db_session.query.return_value.filter.return_value.all.return_value = mock_stats
    
    report = await report_generator.generate_monthly_report(
        year=2024,
        month=3,
        format=ReportFormat.XLSX
    )
    
    assert report is not None
    assert report.type == ReportType.MONTHLY
    assert report.status == ReportStatus.COMPLETED
    assert report.format == ReportFormat.XLSX
    assert report.file_path is not None

@pytest.mark.asyncio
async def test_generate_comprehensive_report(report_generator, db_session):
    """Test generation of comprehensive report."""
    # Mock comprehensive data
    mock_data = {
        'tracks': [
            Mock(
                title="Track 1",
                artist="Artist 1",
                detection_count=100,
                total_play_time=timedelta(hours=5)
            )
        ],
        'artists': [
            Mock(
                name="Artist 1",
                detection_count=150,
                total_play_time=timedelta(hours=8)
            )
        ],
        'stations': [
            Mock(
                name="Station 1",
                detection_count=200,
                total_play_time=timedelta(hours=10)
            )
        ]
    }
    
    with patch.object(report_generator, '_get_comprehensive_data',
                     return_value=mock_data):
        report = await report_generator.generate_comprehensive_report(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            format=ReportFormat.PDF
        )
        
        assert report is not None
        assert report.type == ReportType.COMPREHENSIVE
        assert report.status == ReportStatus.COMPLETED
        assert report.format == ReportFormat.PDF
        assert report.file_path is not None

@pytest.mark.asyncio
async def test_export_to_different_formats(report_generator):
    """Test exporting reports in different formats."""
    test_data = pd.DataFrame({
        'track': ['Track 1', 'Track 2'],
        'artist': ['Artist 1', 'Artist 2'],
        'plays': [10, 20]
    })
    
    # Test CSV export
    csv_path = await report_generator._export_to_csv(test_data, "test_report")
    assert csv_path.endswith('.csv')
    
    # Test XLSX export
    xlsx_path = await report_generator._export_to_xlsx(test_data, "test_report")
    assert xlsx_path.endswith('.xlsx')
    
    # Test PDF export
    pdf_path = await report_generator._export_to_pdf(test_data, "test_report")
    assert pdf_path.endswith('.pdf')

@pytest.mark.asyncio
async def test_error_handling(report_generator, db_session):
    """Test error handling in report generation."""
    # Simulate database error
    db_session.query.side_effect = Exception("Database error")
    
    # Test daily report error handling
    report = await report_generator.generate_daily_report(
        date=datetime.now().date(),
        format=ReportFormat.CSV
    )
    assert report.status == ReportStatus.FAILED
    assert report.error_message is not None
    
    # Test monthly report error handling
    report = await report_generator.generate_monthly_report(
        year=2024,
        month=3,
        format=ReportFormat.XLSX
    )
    assert report.status == ReportStatus.FAILED
    assert report.error_message is not None

@pytest.mark.asyncio
async def test_report_progress_tracking(report_generator):
    """Test report generation progress tracking."""
    with patch.object(report_generator, '_update_progress') as mock_progress:
        await report_generator.generate_comprehensive_report(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            format=ReportFormat.PDF
        )
        
        # Verify progress updates
        mock_progress.assert_called()
        progress_values = [call[0][0] for call in mock_progress.call_args_list]
        assert all(0 <= progress <= 1 for progress in progress_values)

@pytest.mark.asyncio
async def test_report_validation(report_generator):
    """Test report parameter validation."""
    # Test invalid date range
    with pytest.raises(ValueError):
        await report_generator.generate_comprehensive_report(
            start_date=datetime.now(),
            end_date=datetime.now() - timedelta(days=1),
            format=ReportFormat.PDF
        )
    
    # Test invalid format
    with pytest.raises(ValueError):
        await report_generator.generate_daily_report(
            date=datetime.now().date(),
            format="invalid_format"
        ) 