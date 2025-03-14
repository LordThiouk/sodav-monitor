"""Tests for the reorganized reports router."""

from datetime import datetime, timedelta
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models.database import get_db
from backend.models.models import (
    Report,
    ReportFormat,
    ReportStatus,
    ReportSubscription,
    ReportType,
    User,
)
from backend.utils.auth import get_current_user, oauth2_scheme


@pytest.fixture
def test_client_reports(db_session: Session, test_user: User, auth_headers: Dict[str, str]):
    """Create a test client specifically for the reports router."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_user():
        return test_user

    def override_oauth2_scheme():
        return auth_headers["Authorization"].split(" ")[1]

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[oauth2_scheme] = override_oauth2_scheme

    with TestClient(app) as client:
        client.headers.update(auth_headers)
        yield client

    app.dependency_overrides.clear()


def test_get_reports_new_router(
    test_client_reports: TestClient, test_report: Report, auth_headers: Dict[str, str]
):
    """Test getting all reports with the new router."""
    response = test_client_reports.get("/api/reports/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0


def test_create_report_new_router(test_client_reports: TestClient, auth_headers: Dict[str, str]):
    """Test creating a report with the new router."""
    report_data = {
        "title": "Test Report",
        "report_type": "DAILY",
        "format": "PDF",
        "start_date": datetime.utcnow().isoformat(),
        "end_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "include_graphs": True,
        "language": "fr",
    }

    response = test_client_reports.post("/api/reports/", json=report_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Report"
    assert data["report_type"] == "DAILY"
    assert data["status"] == "pending"


def test_get_report_new_router(
    test_client_reports: TestClient, test_report: Report, auth_headers: Dict[str, str]
):
    """Test getting a specific report with the new router."""
    response = test_client_reports.get(f"/api/reports/{test_report.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_report.id
    assert data["title"] == test_report.title
