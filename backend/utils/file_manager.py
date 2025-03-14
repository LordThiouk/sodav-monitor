"""File management utilities for SODAV Monitor."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from backend.config import PATHS, logger


def get_report_path(report_type: str, date: Optional[datetime] = None) -> str:
    """
    Get the path for a report file.

    Args:
        report_type: Type of report (e.g., 'detection', 'station')
        date: Optional date for the report filename

    Returns:
        str: Path where the report should be stored
    """
    if date is None:
        date = datetime.now()

    # Use the REPORT_DIR from config
    reports_dir = Path(PATHS["REPORT_DIR"])

    # Create subdirectory for report type
    type_dir = reports_dir / report_type
    type_dir.mkdir(exist_ok=True)

    # Create year/month subdirectories
    year_dir = type_dir / str(date.year)
    year_dir.mkdir(exist_ok=True)
    month_dir = year_dir / f"{date.month:02d}"
    month_dir.mkdir(exist_ok=True)

    return str(month_dir)


def ensure_directory_exists(path: str) -> None:
    """
    Ensure that a directory exists, creating it if necessary.

    Args:
        path: Path to the directory
    """
    os.makedirs(path, exist_ok=True)
    logger.debug(f"Directory ensured: {path}")


def clean_old_reports(days: int = 30) -> None:
    """
    Clean up reports older than specified number of days.

    Args:
        days: Number of days to keep reports for
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    reports_dir = Path("reports")

    if not reports_dir.exists():
        return

    for report_type in reports_dir.iterdir():
        if not report_type.is_dir():
            continue

        for year_dir in report_type.iterdir():
            if not year_dir.is_dir():
                continue

            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue

                for report_file in month_dir.iterdir():
                    if not report_file.is_file():
                        continue

                    file_date = datetime.fromtimestamp(report_file.stat().st_mtime)
                    if file_date < cutoff_date:
                        report_file.unlink()

                # Clean up empty directories
                try:
                    month_dir.rmdir()
                except OSError:
                    pass

            try:
                year_dir.rmdir()
            except OSError:
                pass

        try:
            report_type.rmdir()
        except OSError:
            pass
