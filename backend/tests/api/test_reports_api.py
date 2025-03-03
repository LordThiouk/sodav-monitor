"""Tests for the reports API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, List
import json
from unittest.mock import patch
from pathlib import Path
import os

from backend.main import app
from backend.models.models import (
    RadioStation, Track, TrackDetection,
    Artist, Report, ReportSubscription,
    ReportType, ReportFormat, ReportStatus,
    User
)
from backend.reports.generator import ReportGenerator
from backend.core.config import get_settings

@pytest.fixture
def test_report(db_session: Session, test_user: User) -> Report:
    """Create a test report."""
    report = Report(
        title="Test Report",
        type="daily",
        report_type=ReportType.DAILY,
        format=ReportFormat.XLSX,
        parameters={
            "date": datetime.utcnow().date().isoformat(),
            "include_graphs": True,
            "language": "fr"
        },
        status=ReportStatus.COMPLETED,
        created_by=test_user.id,
        user_id=test_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    return report

@pytest.fixture
def test_subscription(db_session: Session, test_user: User) -> ReportSubscription:
    """Create a test report subscription."""
    subscription = ReportSubscription(
        name="Test Subscription",
        email="test@example.com",
        frequency="daily",
        report_type=ReportType.DAILY,
        format=ReportFormat.XLSX,
        filters={},
        include_graphs=True,
        language="fr",
        user_id=test_user.id,
        created_by=test_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    return subscription

@pytest.fixture
def settings_override():
    """Override settings for testing."""
    settings = get_settings()
    return {
        'SECRET_KEY': settings.SECRET_KEY,
        'ALGORITHM': settings.ALGORITHM,
        'ACCESS_TOKEN_EXPIRE_MINUTES': settings.ACCESS_TOKEN_EXPIRE_MINUTES
    }

class TestReportsAPI:
    """Test reports API endpoints."""

    def test_generate_daily_report(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test generating a daily report."""
        response = test_client.post("/api/reports/generate/daily", headers=auth_headers)
        assert response.status_code == 200
        assert "id" in response.json()

    def test_generate_monthly_report(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test generating a monthly report."""
        today = datetime.utcnow()
        response = test_client.post(
            f"/api/reports/generate/monthly?year={today.year}&month={today.month}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "id" in response.json()

    def test_get_report_list(
        self,
        test_client: TestClient,
        test_report: Report,
        auth_headers: Dict[str, str]
    ):
        """Test getting report list."""
        response = test_client.get("/api/reports/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0

    def test_get_report_by_id(
        self,
        test_client: TestClient,
        test_report: Report,
        auth_headers: Dict[str, str]
    ):
        """Test getting report by ID."""
        response = test_client.get(f"/api/reports/{test_report.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == test_report.id

    def test_create_subscription(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test creating a subscription."""
        subscription_data = {
            "name": "Test Subscription",
            "email": "test@example.com",
            "frequency": "daily",
            "report_type": ReportType.DAILY.value,
            "format": ReportFormat.XLSX.value,
            "filters": {},
            "include_graphs": True,
            "language": "fr"
        }
        response = test_client.post(
            "/api/reports/subscriptions",
            json=subscription_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "id" in response.json()

    def test_get_subscriptions(
        self,
        test_client: TestClient,
        test_subscription: ReportSubscription,
        auth_headers: Dict[str, str]
    ):
        """Test getting subscriptions."""
        response = test_client.get("/api/reports/subscriptions", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0

    def test_update_subscription(
        self,
        test_client: TestClient,
        test_subscription: ReportSubscription,
        auth_headers: Dict[str, str]
    ):
        """Test updating a subscription."""
        update_data = {
            "name": "Updated Subscription",
            "email": "updated@example.com",
            "frequency": "weekly"
        }
        response = test_client.put(
            f"/api/reports/subscriptions/{test_subscription.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Subscription"
        assert data["email"] == "updated@example.com"
        assert data["frequency"] == "weekly"

    def test_delete_subscription(
        self,
        test_client: TestClient,
        test_subscription: ReportSubscription,
        auth_headers: Dict[str, str]
    ):
        """Test deleting a subscription."""
        response = test_client.delete(
            f"/api/reports/subscriptions/{test_subscription.id}",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_send_report_email(
        self,
        test_client: TestClient,
        test_report: Report,
        auth_headers: Dict[str, str]
    ):
        """Test sending report email."""
        email_data = {
            "email": "test@example.com",
            "subject": "Test Report",
            "body": "Please find the report attached."
        }
        response = test_client.post(
            f"/api/reports/{test_report.id}/send",
            json=email_data,
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_invalid_report_parameters(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test invalid report parameters."""
        invalid_data = {
            "title": "Invalid Report",
            "report_type": "invalid_type",
            "format": "invalid_format"
        }
        response = test_client.post("/api/reports/", json=invalid_data, headers=auth_headers)
        assert response.status_code == 422

    def test_nonexistent_report(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test getting nonexistent report."""
        response = test_client.get("/api/reports/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_invalid_subscription_email(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test invalid subscription email."""
        invalid_data = {
            "name": "Test Subscription",
            "email": "invalid_email",
            "frequency": "daily",
            "report_type": ReportType.DAILY.value,
            "format": ReportFormat.XLSX.value
        }
        response = test_client.post(
            "/api/reports/subscriptions",
            json=invalid_data,
            headers=auth_headers
        )
        assert response.status_code == 422

def test_get_reports(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test getting all reports."""
    response = test_client.get("/api/reports/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["title"] == test_report.title
    assert data[0]["report_type"] == test_report.report_type.value
    assert data[0]["status"] == test_report.status.value

def test_get_reports_with_filters(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test getting reports with filters."""
    response = test_client.get(
        f"/api/reports/?report_type={test_report.type}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(r["type"] == test_report.type for r in data)

def test_create_report(test_client: TestClient, auth_headers: Dict[str, str]):
    """Test creating a new report."""
    report_data = {
        "title": "New Test Report",
        "report_type": ReportType.DAILY.value,
        "format": ReportFormat.XLSX.value,
        "parameters": {
            "date": datetime.utcnow().date().isoformat(),
            "include_graphs": True,
            "language": "fr"
        }
    }
    response = test_client.post("/api/reports/", json=report_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == report_data["title"]
    assert data["report_type"] == report_data["report_type"]
    assert data["status"] == ReportStatus.PENDING.value

def test_get_report(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test getting a specific report."""
    response = test_client.get(f"/api/reports/{test_report.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_report.id
    assert data["title"] == test_report.title
    assert data["report_type"] == test_report.report_type.value

def test_get_nonexistent_report(test_client: TestClient, auth_headers: Dict[str, str]):
    """Test getting a nonexistent report."""
    response = test_client.get("/api/reports/99999", headers=auth_headers)
    assert response.status_code == 404

def test_get_report_status(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test getting report status."""
    response = test_client.get(f"/api/reports/{test_report.id}/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_report.id
    assert data["status"] == test_report.status.value

def test_update_report_status(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test updating report status."""
    update_data = {
        "status": ReportStatus.PROCESSING.value,
        "progress": 50.0
    }
    response = test_client.put(
        f"/api/reports/{test_report.id}/status",
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ReportStatus.PROCESSING.value
    assert data["progress"] == 50.0

def test_filter_reports_by_type(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test filtering reports by type."""
    response = test_client.get(f"/api/reports/?type={test_report.type}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(r["type"] == test_report.type for r in data)

def test_filter_reports_by_status(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test filtering reports by status."""
    response = test_client.get(f"/api/reports/?status={test_report.status}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(r["status"] == test_report.status for r in data)

def test_filter_reports_by_date_range(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test filtering reports by date range."""
    start_date = (test_report.created_at - timedelta(days=1)).isoformat()
    end_date = (test_report.created_at + timedelta(days=1)).isoformat()
    response = test_client.get(
        f"/api/reports/?start_date={start_date}&end_date={end_date}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

def test_report_pagination(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test report pagination."""
    # Create multiple reports
    reports = []
    for i in range(5):
        report = Report(
            title=f"Test Report {i}",
            type="daily",
            report_type=ReportType.DAILY,
            format=ReportFormat.XLSX,
            status=ReportStatus.COMPLETED,
            created_by=test_report.created_by,
            user_id=test_report.user_id,
            created_at=datetime.utcnow()
        )
        reports.append(report)
    
    # Test pagination
    response = test_client.get("/api/reports/?skip=0&limit=3", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 3

def test_report_sorting(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test report sorting."""
    # Test sorting by created_at descending
    response = test_client.get("/api/reports/?sort=created_at&order=desc", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    if len(data) > 1:
        assert datetime.fromisoformat(data[0]["created_at"]) >= datetime.fromisoformat(data[1]["created_at"])

def test_report_search(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test searching reports."""
    response = test_client.get(f"/api/reports/search?query={test_report.title}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(test_report.title.lower() in r["title"].lower() for r in data)

def test_report_export_formats(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test report export in different formats."""
    formats = ["pdf", "xlsx", "csv"]
    for format in formats:
        response = test_client.get(
            f"/api/reports/{test_report.id}/export?format={format}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == f"application/{format}"

def test_report_email_validation(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test report email validation."""
    invalid_email_data = {
        "email": "invalid_email",
        "subject": "Test Report",
        "body": "Please find the report attached."
    }
    response = test_client.post(
        f"/api/reports/{test_report.id}/send",
        json=invalid_email_data,
        headers=auth_headers
    )
    assert response.status_code == 422

def test_subscription_frequency_validation(test_client: TestClient, auth_headers: Dict[str, str]):
    """Test subscription frequency validation."""
    invalid_subscription = {
        "name": "Test Subscription",
        "email": "test@example.com",
        "frequency": "invalid_frequency",
        "report_type": ReportType.DAILY.value,
        "format": ReportFormat.XLSX.value
    }
    response = test_client.post(
        "/api/reports/subscriptions",
        json=invalid_subscription,
        headers=auth_headers
    )
    assert response.status_code == 422

def test_subscription_filters(test_client: TestClient, test_subscription: ReportSubscription, auth_headers: Dict[str, str]):
    """Test subscription filters."""
    update_data = {
        "filters": {
            "stations": ["station1", "station2"],
            "artists": ["artist1", "artist2"],
            "date_range": {
                "start": datetime.utcnow().isoformat(),
                "end": (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
        }
    }
    response = test_client.put(
        f"/api/reports/subscriptions/{test_subscription.id}",
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "filters" in data
    assert data["filters"] == update_data["filters"]

def test_subscription_language_validation(test_client: TestClient, auth_headers: Dict[str, str]):
    """Test subscription language validation."""
    invalid_subscription = {
        "name": "Test Subscription",
        "email": "test@example.com",
        "frequency": "daily",
        "report_type": ReportType.DAILY.value,
        "format": ReportFormat.XLSX.value,
        "language": "invalid_language"
    }
    response = test_client.post(
        "/api/reports/subscriptions",
        json=invalid_subscription,
        headers=auth_headers
    )
    assert response.status_code == 422

def test_delete_report(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test deleting a report."""
    response = test_client.delete(f"/api/reports/{test_report.id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Verify deletion
    response = test_client.get(f"/api/reports/{test_report.id}", headers=auth_headers)
    assert response.status_code == 404

def test_generate_daily_report(test_client: TestClient, auth_headers: Dict[str, str]):
    """Test generating a daily report."""
    response = test_client.post("/api/reports/generate/daily", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["report_type"] == ReportType.DAILY.value
    assert data["status"] == ReportStatus.PENDING.value

def test_generate_monthly_report(test_client: TestClient, auth_headers: Dict[str, str]):
    """Test generating a monthly report."""
    today = datetime.utcnow()
    response = test_client.post(
        f"/api/reports/generate/monthly?year={today.year}&month={today.month}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["report_type"] == ReportType.MONTHLY.value
    assert data["status"] == ReportStatus.PENDING.value

def test_create_subscription(test_client: TestClient, auth_headers: Dict[str, str]):
    """Test creating a report subscription."""
    subscription_data = {
        "name": "Test Subscription",
        "email": "test@example.com",
        "frequency": "daily",
        "report_type": ReportType.DAILY.value,
        "format": ReportFormat.XLSX.value,
        "filters": {},
        "include_graphs": True,
        "language": "fr"
    }
    response = test_client.post("/api/reports/subscriptions", json=subscription_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == subscription_data["name"]
    assert data["email"] == subscription_data["email"]
    assert data["frequency"] == subscription_data["frequency"]

def test_get_subscriptions(test_client: TestClient, test_subscription: ReportSubscription, auth_headers: Dict[str, str]):
    """Test getting report subscriptions."""
    response = test_client.get("/api/reports/subscriptions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["name"] == test_subscription.name
    assert data[0]["email"] == test_subscription.email

def test_delete_subscription(test_client: TestClient, test_subscription: ReportSubscription, auth_headers: Dict[str, str]):
    """Test deleting a report subscription."""
    response = test_client.delete(f"/api/reports/subscriptions/{test_subscription.id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Verify deletion
    response = test_client.get("/api/reports/subscriptions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert not any(s["id"] == test_subscription.id for s in data)

def test_download_report(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str]):
    """Test downloading a report."""
    # Create a dummy report file
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / f"report_{test_report.id}.xlsx"
    report_path.touch()

    try:
        response = test_client.get(f"/api/reports/{test_report.id}/download", headers=auth_headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xlsx"
        assert "report" in response.headers["content-disposition"]
    finally:
        # Clean up
        if report_path.exists():
            report_path.unlink()

def test_download_nonexistent_report(test_client: TestClient, auth_headers: Dict[str, str]):
    """Test downloading a nonexistent report."""
    response = test_client.get("/api/reports/99999/download", headers=auth_headers)
    assert response.status_code == 404

def test_download_pending_report(test_client: TestClient, test_report: Report, auth_headers: Dict[str, str], db_session: Session):
    """Test downloading a report that is not ready."""
    # Update report status to pending
    test_report.status = ReportStatus.PENDING
    db_session.commit()

    response = test_client.get(f"/api/reports/{test_report.id}/download", headers=auth_headers)
    assert response.status_code == 400
    assert "not ready for download" in response.json()["detail"] 