"""Tests for the generate_test_report module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from pathlib import Path
import shutil

from backend.analytics.generate_test_report import create_test_report
from backend.models.models import Report, User, ReportStatus

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = Mock()
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.close = Mock()
    return db

@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = Mock(spec=User)
    user.id = 1
    user.username = "admin"
    user.email = "admin@sodav.sn"
    user.is_active = True
    user.role = "admin"
    return user

@pytest.fixture
def mock_report():
    """Create a mock report."""
    report = Mock(spec=Report)
    report.id = 1
    report.type = "summary"
    report.format = "csv"
    report.status = ReportStatus.PENDING
    report.progress = 0.0
    report.user_id = 1
    return report

@pytest.fixture
def mock_summary_data():
    """Create mock summary data."""
    return pd.DataFrame({
        'track_title': ['Test Track'],
        'artist_name': ['Test Artist'],
        'play_count': [10],
        'total_duration': ['00:30:00']
    })

@pytest.fixture(autouse=True)
def cleanup_reports():
    """Clean up reports directory after each test."""
    yield
    reports_dir = Path(__file__).parent.parent.parent / "analytics" / "reports"
    if reports_dir.exists():
        shutil.rmtree(reports_dir)

@patch('backend.analytics.generate_test_report.SessionLocal')
@patch('backend.analytics.generate_test_report.get_summary_data')
def test_create_test_report_success(mock_get_data, mock_session_local, mock_db, mock_user, mock_report, mock_summary_data):
    """Test successful creation of a test report."""
    # Setup mocks
    mock_session_local.return_value = mock_db
    mock_get_data.return_value = mock_summary_data
    
    # Create a spy to track report status changes
    report_spy = None
    
    def spy_add(obj):
        nonlocal report_spy
        if isinstance(obj, Report):
            report_spy = obj
        return None
    
    mock_add = Mock(side_effect=spy_add)
    mock_db.add = mock_add
    
    # Mock user query
    mock_user_query = Mock()
    mock_user_query.filter.return_value.first.return_value = mock_user
    
    # Mock report creation
    mock_db.query.side_effect = lambda x: {
        User: mock_user_query,
    }[x]
    
    # Run the function
    create_test_report()
    
    # Verify the results
    assert mock_add.call_count == 1
    assert mock_db.commit.call_count >= 2
    assert mock_db.close.called
    
    # Verify that we captured the report
    assert report_spy is not None
    assert isinstance(report_spy, Report)
    
    # Verify initial state
    assert report_spy.type == "summary"
    assert report_spy.format == "csv"
    
    # Verify final state
    assert report_spy.status == ReportStatus.COMPLETED
    assert report_spy.progress == 1.0
    assert report_spy.completed_at is not None
    assert report_spy.file_path is not None
    
    # Verify the report file was created
    reports_dir = Path(__file__).parent.parent.parent / "analytics" / "reports"
    assert reports_dir.exists()
    report_files = list(reports_dir.glob("report_*.csv"))
    assert len(report_files) == 1

@patch('backend.analytics.generate_test_report.SessionLocal')
@patch('backend.analytics.generate_test_report.get_summary_data')
def test_create_test_report_new_user(mock_get_data, mock_session_local, mock_db, mock_summary_data):
    """Test report creation when admin user doesn't exist."""
    # Setup mocks
    mock_session_local.return_value = mock_db
    mock_get_data.return_value = mock_summary_data
    
    # Mock empty user query
    mock_user_query = Mock()
    mock_user_query.filter.return_value.first.return_value = None
    mock_db.query.return_value = mock_user_query
    
    # Run the function
    create_test_report()
    
    # Verify user creation
    assert mock_db.add.call_count == 2  # User and report
    assert mock_db.commit.call_count >= 2
    
    # Verify user was created with correct attributes
    user_call = mock_db.add.call_args_list[0][0][0]
    assert isinstance(user_call, User)
    assert user_call.username == "admin"
    assert user_call.email == "admin@sodav.sn"
    assert user_call.is_active is True
    assert user_call.role == "admin"

@patch('backend.analytics.generate_test_report.SessionLocal')
@patch('backend.analytics.generate_test_report.get_summary_data')
def test_create_test_report_data_error(mock_get_data, mock_session_local, mock_db, mock_user):
    """Test handling of data generation errors."""
    # Setup mocks
    mock_session_local.return_value = mock_db
    mock_get_data.side_effect = Exception("Data generation error")
    
    # Mock user query
    mock_user_query = Mock()
    mock_user_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_user_query
    
    # Run the function and check for error
    with pytest.raises(Exception, match="Data generation error"):
        create_test_report()
    
    # Verify cleanup
    assert mock_db.close.called

@patch('backend.analytics.generate_test_report.SessionLocal')
@patch('backend.analytics.generate_test_report.get_summary_data')
def test_create_test_report_file_error(mock_get_data, mock_session_local, mock_db, mock_user, mock_summary_data):
    """Test handling of file writing errors."""
    # Setup mocks
    mock_session_local.return_value = mock_db
    mock_get_data.return_value = mock_summary_data
    
    # Mock user query
    mock_user_query = Mock()
    mock_user_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_user_query
    
    # Mock DataFrame to_csv to raise error
    mock_summary_data.to_csv = Mock(side_effect=IOError("File write error"))
    
    # Run the function and check for error
    with pytest.raises(IOError, match="File write error"):
        create_test_report()
    
    # Verify cleanup
    assert mock_db.close.called

@patch('backend.analytics.generate_test_report.SessionLocal')
def test_create_test_report_db_error(mock_session_local):
    """Test handling of database connection errors."""
    # Mock session to raise error
    mock_session_local.side_effect = Exception("Database connection error")
    
    # Run the function and check for error
    with pytest.raises(Exception, match="Database connection error"):
        create_test_report() 