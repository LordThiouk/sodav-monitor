#!/usr/bin/env python
"""
Script to check music detection results from the database.
"""
import json
import logging
import os
import sys
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from backend
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from models.database import get_db, init_db
from models.models import Detection, RadioStation, Track
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_detection_results(hours=1):
    """
    Check music detection results from the last specified hours.

    Args:
        hours: Number of hours to look back for detections (default: 1)
    """
    try:
        # Initialize the database
        init_db()

        # Get a database session
        db_session = next(get_db())

        # Calculate the time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours)

        # Query recent detections
        detections = (
            db_session.query(Detection)
            .filter(Detection.created_at >= time_threshold)
            .order_by(Detection.created_at.desc())
            .all()
        )

        logger.info(f"Found {len(detections)} detections in the last {hours} hour(s)")

        # Group detections by station
        detections_by_station = {}
        for detection in detections:
            station = (
                db_session.query(RadioStation)
                .filter(RadioStation.id == detection.station_id)
                .first()
            )
            if not station:
                continue

            station_name = station.name

            if station_name not in detections_by_station:
                detections_by_station[station_name] = []

            # Get track information if available
            track_info = None
            if detection.track_id:
                track = db_session.query(Track).filter(Track.id == detection.track_id).first()
                if track:
                    track_info = {
                        "title": track.title,
                        "artist": track.artist,
                        "album": track.album,
                        "isrc": track.isrc,
                    }

            # Add detection to the list
            detections_by_station[station_name].append(
                {
                    "id": detection.id,
                    "timestamp": detection.created_at.isoformat(),
                    "confidence": detection.confidence,
                    "track": track_info,
                    "type": detection.type,
                }
            )

        # Save results to a file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"detection_results_check_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(detections_by_station, f, indent=4)

        logger.info(f"Results saved to {filename}")

        # Print summary
        print("\nDetection Results Summary:")
        print("=" * 50)
        for station, detections in detections_by_station.items():
            music_count = sum(1 for d in detections if d["type"] == "music")
            speech_count = sum(1 for d in detections if d["type"] == "speech")
            unknown_count = sum(1 for d in detections if d["type"] == "unknown")

            print(f"\nStation: {station}")
            print(f"  Total Detections: {len(detections)}")
            print(f"  Music: {music_count}")
            print(f"  Speech: {speech_count}")
            print(f"  Unknown: {unknown_count}")

            # Print the most recent detections
            if detections:
                print("\n  Most Recent Detections:")
                for detection in detections[:3]:  # Show the 3 most recent
                    detection_type = detection["type"]
                    timestamp = detection["timestamp"]

                    if detection_type == "music" and detection["track"]:
                        track_info = detection["track"]
                        print(
                            f"    [{timestamp}] MUSIC: {track_info['title']} by {track_info['artist']}"
                        )
                    else:
                        print(f"    [{timestamp}] {detection_type.upper()}")

        return detections_by_station

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # Check detections from the last 24 hours by default
    import argparse

    parser = argparse.ArgumentParser(description="Check music detection results")
    parser.add_argument(
        "--hours", type=int, default=24, help="Number of hours to look back for detections"
    )

    args = parser.parse_args()
    check_detection_results(hours=args.hours)
