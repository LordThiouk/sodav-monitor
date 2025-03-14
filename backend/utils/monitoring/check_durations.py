"""Duration checking utilities for the monitoring system.

This module provides functionality for checking and validating play durations
in the SODAV Monitor system.
"""

from datetime import timedelta
from typing import Dict, List

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.models.models import RadioStation, Track, TrackDetection
from backend.utils.logging_config import setup_logging

logger = setup_logging(__name__)


def check_play_durations(db: Session, station_id: int = None) -> List[Dict]:
    """Check play durations for anomalies.

    Args:
        db: Database session
        station_id: Optional station ID to check (checks all stations if None)

    Returns:
        List[Dict]: List of anomalies found
    """
    anomalies = []

    # Base query for detections
    query = db.query(TrackDetection)

    # Filter by station if specified
    if station_id is not None:
        query = query.filter(TrackDetection.station_id == station_id)

    # Check for missing durations
    missing_durations = (
        query.filter(TrackDetection.play_duration.is_(None))
        .order_by(desc(TrackDetection.detected_at))
        .all()
    )

    if missing_durations:
        anomalies.append(
            {
                "type": "missing_duration",
                "count": len(missing_durations),
                "detections": [
                    {
                        "id": d.id,
                        "station_id": d.station_id,
                        "track_id": d.track_id,
                        "detected_at": d.detected_at.isoformat(),
                    }
                    for d in missing_durations[:10]  # Limit to 10 examples
                ],
            }
        )

    # Check for overlapping detections
    overlapping = (
        query.join(RadioStation)
        .filter(TrackDetection.play_duration.isnot(None))
        .order_by(desc(TrackDetection.detected_at))
        .all()
    )

    # Group by station and check for overlaps
    by_station = {}
    for detection in overlapping:
        if detection.station_id not in by_station:
            by_station[detection.station_id] = []
        by_station[detection.station_id].append(detection)

    for station_detections in by_station.values():
        for i in range(len(station_detections) - 1):
            current = station_detections[i]
            next_det = station_detections[i + 1]

            current_end = current.detected_at + current.play_duration
            if current_end > next_det.detected_at:
                anomalies.append(
                    {
                        "type": "overlap",
                        "station_id": current.station_id,
                        "detection1": {
                            "id": current.id,
                            "track_id": current.track_id,
                            "detected_at": current.detected_at.isoformat(),
                            "duration": str(current.play_duration),
                        },
                        "detection2": {
                            "id": next_det.id,
                            "track_id": next_det.track_id,
                            "detected_at": next_det.detected_at.isoformat(),
                            "duration": str(next_det.play_duration),
                        },
                    }
                )

    return anomalies


def check_detections():
    """Check track detections and their durations.

    This function analyzes detection data to identify issues with play durations,
    including zero or null durations and overlapping detections.
    """
    try:
        # Import here to avoid circular imports
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from backend.core.config import get_settings

        # Get database URL and create engine
        settings = get_settings()
        database_url = settings.DATABASE_URL
        engine = create_engine(database_url)

        # Create session
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            # Get total number of detections
            total_detections = db.query(TrackDetection).count()
            logger.info(f"Total number of detections: {total_detections}")

            # Get number of detections with zero duration
            zero_duration_count = (
                db.query(TrackDetection)
                .filter(
                    (TrackDetection.play_duration == timedelta(0))
                    | (TrackDetection.play_duration.is_(None))
                )
                .count()
            )
            logger.info(f"Number of detections with zero/null duration: {zero_duration_count}")

            # Calculate percentage
            if total_detections > 0:
                zero_duration_percentage = (zero_duration_count / total_detections) * 100
                logger.info(f"Percentage of zero/null durations: {zero_duration_percentage:.2f}%")

            # Get recent detections
            logger.info("\nMost recent detections:")
            recent_detections = (
                db.query(TrackDetection)
                .join(Track)
                .join(RadioStation)
                .order_by(desc(TrackDetection.detected_at))
                .limit(10)
                .all()
            )

            for detection in recent_detections:
                logger.info(
                    f"Detection ID: {detection.id}\n"
                    f"  Track: {detection.track.title} by {detection.track.artist}\n"
                    f"  Station: {detection.station.name}\n"
                    f"  Duration: {detection.play_duration or 'None'}\n"
                    f"  Detected at: {detection.detected_at}\n"
                    f"  Confidence: {detection.confidence}\n"
                )

            # Check tracks with most zero/null duration detections
            logger.info("\nTracks with most zero/null duration detections:")
            problematic_tracks = (
                db.query(Track, func.count(TrackDetection.id).label("zero_duration_count"))
                .join(TrackDetection)
                .filter(
                    (TrackDetection.play_duration == timedelta(0))
                    | (TrackDetection.play_duration.is_(None))
                )
                .group_by(Track.id)
                .order_by(desc("zero_duration_count"))
                .limit(5)
                .all()
            )

            for track, count in problematic_tracks:
                logger.info(
                    f"Track: {track.title} by {track.artist}\n"
                    f"  Zero/null duration detections: {count}\n"
                    f"  Total play time: {track.total_play_time}\n"
                    f"  Play count: {track.play_count}\n"
                )

            # Check stations with most zero/null duration detections
            logger.info("\nStations with most zero/null duration detections:")
            problematic_stations = (
                db.query(RadioStation, func.count(TrackDetection.id).label("zero_duration_count"))
                .join(TrackDetection)
                .filter(
                    (TrackDetection.play_duration == timedelta(0))
                    | (TrackDetection.play_duration.is_(None))
                )
                .group_by(RadioStation.id)
                .order_by(desc("zero_duration_count"))
                .limit(5)
                .all()
            )

            for station, count in problematic_stations:
                logger.info(
                    f"Station: {station.name}\n"
                    f"  Zero/null duration detections: {count}\n"
                    f"  Total play time: {station.total_play_time}\n"
                )

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error checking detections: {str(e)}")
        raise


if __name__ == "__main__":
    check_detections()
