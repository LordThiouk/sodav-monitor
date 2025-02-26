"""Tests pour le module de génération de rapports."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, List
from ..models import Report, ReportSubscription, ReportType, ReportStatus
from ..reports.report_generator import ReportGenerator
from ..core.security import get_current_user

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
        format="pdf",
        include_stats=True
    )
    assert report_path.endswith(".pdf")
    assert report_path.startswith("reports/")

@pytest.mark.asyncio
async def test_generate_excel_report(report_generator, sample_report_data, db_session):
    """Test de génération de rapport Excel."""
    report_path = await report_generator.generate_report(
        start_date=sample_report_data["start_date"],
        end_date=sample_report_data["end_date"],
        format="xlsx",
        include_stats=True
    )
    assert report_path.endswith(".xlsx")
    assert report_path.startswith("reports/")

@pytest.mark.asyncio
async def test_generate_csv_report(report_generator, sample_report_data, db_session):
    """Test de génération de rapport CSV."""
    report_path = await report_generator.generate_report(
        start_date=sample_report_data["start_date"],
        end_date=sample_report_data["end_date"],
        format="csv",
        include_stats=True
    )
    assert report_path.endswith(".csv")
    assert report_path.startswith("reports/")

@pytest.mark.asyncio
async def test_report_subscription(report_generator, db_session):
    """Test de gestion des abonnements aux rapports."""
    # Création d'un abonnement
    subscription_data = {
        "name": "Test User",
        "email": "test@example.com",
        "frequency": "daily",
        "report_type": "comprehensive",
        "format": "pdf",
        "include_graphs": True,
        "language": "fr"
    }
    
    subscription = ReportSubscription(**subscription_data)
    db_session.add(subscription)
    db_session.commit()
    
    # Vérification de l'abonnement
    saved_subscription = db_session.query(ReportSubscription).first()
    assert saved_subscription.email == subscription_data["email"]
    assert saved_subscription.frequency == subscription_data["frequency"]

@pytest.mark.asyncio
async def test_report_status_updates(report_generator, sample_report_data, db_session):
    """Test des mises à jour de statut des rapports."""
    # Création d'un rapport
    report = Report(
        type=ReportType.comprehensive,
        format="pdf",
        status=ReportStatus.pending,
        created_at=datetime.utcnow()
    )
    db_session.add(report)
    db_session.commit()
    
    # Génération du rapport
    report_path = await report_generator.generate_report(
        start_date=sample_report_data["start_date"],
        end_date=sample_report_data["end_date"],
        format="pdf",
        include_stats=True
    )
    
    # Vérification du statut
    report = db_session.query(Report).first()
    assert report.status == ReportStatus.completed
    assert report.completed_at is not None 