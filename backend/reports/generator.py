"""Report generation module for SODAV Monitor."""

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from backend.models.models import RadioStation, TrackDetection
from backend.schemas.base import ReportCreate


class ReportGenerator:
    """Class for generating various types of reports."""

    def __init__(self, db_session):
        """Initialize the report generator with a database session."""
        self.db_session = db_session

    async def generate_report(self, report_data: ReportCreate) -> str:
        """
        Generate a report based on the provided parameters.

        Args:
            report_data: Report configuration and filters

        Returns:
            str: Path to the generated report file

        Raises:
            ValueError: If report type is invalid or date range is invalid
        """
        # Validate dates
        if report_data.period_end < report_data.period_start:
            raise ValueError("End date must be after start date")

        if report_data.period_end > datetime.now():
            raise ValueError("Cannot generate reports for future dates")

        if report_data.type == "detection":
            return await self._generate_detection_report(
                report_data.period_start, report_data.period_end, report_data.filters
            )
        elif report_data.type == "station":
            return await self._generate_station_report(
                report_data.period_start, report_data.period_end, report_data.filters
            )
        else:
            raise ValueError(f"Unsupported report type: {report_data.type}")

    async def _generate_detection_report(
        self, start_date: datetime, end_date: datetime, filters: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate a report of music detections.

        Args:
            start_date: Start date for the report period
            end_date: End date for the report period
            filters: Optional filters to apply to the report

        Returns:
            str: Path to the generated report file
        """
        query = self.db_session.query(TrackDetection).filter(
            TrackDetection.detected_at.between(start_date, end_date)
        )

        if filters:
            if "station" in filters:
                query = query.join(RadioStation).filter(RadioStation.name == filters["station"])
            if "artist" in filters:
                query = query.filter(TrackDetection.track.has(artist=filters["artist"]))

        detections = query.all()

        # Convert to DataFrame for easy analysis
        df = pd.DataFrame(
            [
                {
                    "Date": d.detected_at,
                    "Station": d.station.name,
                    "Track": d.track.title,
                    "Artist": d.track.artist,
                    "Confidence": d.confidence,
                }
                for d in detections
            ]
        )

        # Generate report file
        filename = (
            f"detection_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
        )
        filepath = f"reports/{filename}"
        df.to_excel(filepath, index=False)

        return filepath

    async def _generate_station_report(
        self, start_date: datetime, end_date: datetime, filters: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate a report of station statistics.

        Args:
            start_date: Start date for the report period
            end_date: End date for the report period
            filters: Optional filters to apply to the report

        Returns:
            str: Path to the generated report file
        """
        stations = self.db_session.query(RadioStation).all()

        station_stats = []
        for station in stations:
            detections = (
                self.db_session.query(TrackDetection)
                .filter(
                    TrackDetection.station_id == station.id,
                    TrackDetection.detected_at.between(start_date, end_date),
                )
                .all()
            )

            total_detections = len(detections)
            avg_confidence = (
                sum(d.confidence for d in detections) / total_detections
                if total_detections > 0
                else 0
            )

            station_stats.append(
                {
                    "Station": station.name,
                    "Region": station.region,
                    "Language": station.language,
                    "Status": station.status.value,
                    "Total Detections": total_detections,
                    "Average Confidence": avg_confidence,
                    "Last Checked": station.last_checked,
                }
            )

        # Convert to DataFrame
        df = pd.DataFrame(station_stats)

        # Generate report file
        filename = (
            f"station_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
        )
        filepath = f"reports/{filename}"
        df.to_excel(filepath, index=False)

        return filepath
