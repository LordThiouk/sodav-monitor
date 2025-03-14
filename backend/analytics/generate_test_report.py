import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from backend.config import PATHS
from backend.models.database import SessionLocal, get_database_url
from backend.models.models import Report, ReportStatus, User
from backend.routers.reports import get_summary_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_report():
    """Create a test summary report for the last 24 hours"""
    try:
        # Get database session
        db = SessionLocal()

        try:
            # Get test admin user if not exists
            user = db.query(User).filter(User.username == "admin").first()
            if not user:
                user = User(username="admin", email="admin@sodav.sn", is_active=True, role="admin")
                user.set_password("admin123")
                db.add(user)
                db.commit()
                logger.info("Created test admin user")

            # Set time range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)

            # Create report
            report = Report(
                type="summary",
                format="csv",
                start_date=start_date,
                end_date=end_date,
                status=ReportStatus.PENDING,
                progress=0.0,
                user_id=user.id,
                created_at=datetime.now(),
            )
            db.add(report)
            db.commit()
            logger.info(f"Created report with ID: {report.id}")

            # Get summary data
            data = get_summary_data(start_date, end_date, db)

            # Use REPORT_DIR from config
            report_dir = Path(PATHS["REPORT_DIR"]) / "analytics"
            report_dir.mkdir(parents=True, exist_ok=True)

            # Save to CSV
            report_path = report_dir / f"report_{report.id}.csv"
            data.to_csv(report_path, index=False)

            # Update report status
            report.status = ReportStatus.COMPLETED
            report.progress = 1.0
            report.completed_at = datetime.now()
            report.file_path = str(report_path)
            db.commit()

            logger.info(f"Report generated successfully: {report_path}")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error creating test report: {str(e)}")
        raise


if __name__ == "__main__":
    create_test_report()
