"""Tests pour le module de génération de rapports."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, List
from ..models.models import Report, ReportSubscription, ReportType, ReportStatus, ReportFormat
from ..reports.report_generator import ReportGenerator
from ..core.security import get_current_user
from ..models.database import SessionLocal

@pytest.fixture(scope="function")
def db_session() -> Session:
    """Fixture pour la session de base de données de test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def report_generator(db_session: Session):
    """Fixture pour le générateur de rapports."""
    return ReportGenerator(db_session)

@pytest.fixture
def sample_report_data() -> Dict:
    """Fixture pour les données de test des rapports."""
    return {
        "report_type": "comprehensive",
        "format": "pdf",
        "start_date": datetime.utcnow() - timedelta(days=7),
        "end_date": datetime.utcnow(),
        "include_graphs": True,
        "language": "fr"
    }

@pytest.mark.asyncio
async def test_generate_pdf_report(report_generator, sample_report_data, db_session):
    """Test de génération de rapport PDF."""
    report_path = await report_generator.generate_report(
        start_date=sample_report_data["start_date"],
        end_date=sample_report_data["end_date"],
        format=ReportFormat.PDF,
        include_stats=True
    )

    assert report_path is not None
    assert report_path.endswith(".pdf")

@pytest.mark.asyncio
async def test_generate_excel_report(report_generator, sample_report_data, db_session):
    """Test de génération de rapport Excel."""
    report_path = await report_generator.generate_report(
        start_date=sample_report_data["start_date"],
        end_date=sample_report_data["end_date"],
        format=ReportFormat.XLSX,
        include_stats=True
    )

    assert report_path is not None
    assert report_path.endswith(".xlsx")

@pytest.mark.asyncio
async def test_generate_csv_report(report_generator, sample_report_data, db_session):
    """Test de génération de rapport CSV."""
    report_path = await report_generator.generate_report(
        start_date=sample_report_data["start_date"],
        end_date=sample_report_data["end_date"],
        format=ReportFormat.CSV,
        include_stats=True
    )

    assert report_path is not None
    assert report_path.endswith(".csv")

@pytest.mark.asyncio
async def test_report_subscription(report_generator, db_session):
    """Test de gestion des abonnements aux rapports."""
    # Création d'un abonnement
    subscription = ReportSubscription(
        name="Test User",
        email="test@example.com",
        frequency=ReportType.DAILY,
        format=ReportFormat.PDF
    )
    db_session.add(subscription)
    db_session.commit()

    assert subscription.id is not None
    assert subscription.name == "Test User"
    assert subscription.email == "test@example.com"
    assert subscription.frequency == ReportType.DAILY
    assert subscription.format == ReportFormat.PDF
    assert subscription.active is True

@pytest.mark.asyncio
async def test_report_status_updates(report_generator, sample_report_data, db_session):
    """Test des mises à jour de statut des rapports."""
    # Création d'un rapport
    report = Report(
        type=ReportType.COMPREHENSIVE,
        format=ReportFormat.PDF,
        status=ReportStatus.PENDING,
        created_at=datetime.utcnow()
    )
    db_session.add(report)
    db_session.commit()

    # Mise à jour du statut
    report.status = ReportStatus.PROCESSING
    db_session.commit()
    assert report.status == ReportStatus.PROCESSING

    report.status = ReportStatus.COMPLETED
    db_session.commit()
    assert report.status == ReportStatus.COMPLETED 