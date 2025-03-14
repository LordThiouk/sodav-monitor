"""Script to seed the database with test data for real data testing."""

import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

# Add the parent directory to the path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.models.database import get_db
from backend.models.models import (
    Artist,
    ArtistStats,
    RadioStation,
    Report,
    StationStats,
    StationTrackStats,
    Track,
    TrackDetection,
    TrackStats,
    User,
)
from backend.utils.auth import get_password_hash


async def seed_test_data():
    """Seed the database with test data."""
    # Get a database session
    db = next(get_db())

    try:
        # Check if test user exists
        test_user = db.query(User).filter(User.username == "testuser").first()
        if not test_user:
            # Create a test user
            test_user = User(
                username="testuser",
                email="test@example.com",
                password_hash=get_password_hash("password"),
                is_active=True,
                role="admin",
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            print(f"Created test user: {test_user.username}")
        else:
            print(f"Using existing user: {test_user.username}")

        # Create test radio stations
        stations = []
        for i in range(1, 4):
            station_name = f"Test Station {i}"
            existing_station = (
                db.query(RadioStation).filter(RadioStation.name == station_name).first()
            )
            if existing_station:
                stations.append(existing_station)
                print(f"Using existing station: {existing_station.name}")
                continue

            station = RadioStation(
                name=station_name,
                stream_url=f"http://test.stream/{i}",
                status="active",
                is_active=True,
                region="Test Region",
                language="en",
            )
            db.add(station)
            db.commit()
            db.refresh(station)
            stations.append(station)
            print(f"Created test station: {station.name}")

        # Create test artists
        artists = []
        for i in range(1, 6):
            artist_name = f"Test Artist {i}"
            existing_artist = db.query(Artist).filter(Artist.name == artist_name).first()
            if existing_artist:
                artists.append(existing_artist)
                print(f"Using existing artist: {existing_artist.name}")
                continue

            mbid = str(uuid.uuid4())
            artist = Artist(
                name=artist_name,
                country="Test Country",
                region="Test Region",
                type="musician",
                label="Test Label",
                external_ids={"musicbrainz": mbid},
            )
            db.add(artist)
            db.commit()
            db.refresh(artist)
            artists.append(artist)
            print(f"Created test artist: {artist.name}")

        # Create test tracks
        tracks = []
        for i in range(1, 11):
            track_title = f"Test Track {i}"
            artist = random.choice(artists)
            existing_track = (
                db.query(Track)
                .filter(Track.title == track_title, Track.artist_id == artist.id)
                .first()
            )
            if existing_track:
                tracks.append(existing_track)
                print(f"Using existing track: {existing_track.title} by {artist.name}")
                continue

            track = Track(
                title=track_title,
                artist_id=artist.id,
                isrc=f"USXXX{i:07d}",
                fingerprint=f"test_fingerprint_{i}",
                label="Test Label",
            )
            try:
                db.add(track)
                db.commit()
                db.refresh(track)
                tracks.append(track)
                print(f"Created test track: {track.title} by {artist.name}")
            except IntegrityError:
                db.rollback()
                # Try with a different fingerprint
                track.fingerprint = f"test_fingerprint_{i}_{uuid.uuid4()}"
                db.add(track)
                db.commit()
                db.refresh(track)
                tracks.append(track)
                print(f"Created test track with unique fingerprint: {track.title} by {artist.name}")

        # Create test detections
        now = datetime.utcnow()
        detection_count = 0
        for i in range(50):
            station = random.choice(stations)
            track = random.choice(tracks)
            detected_at = now - timedelta(hours=random.randint(1, 72))
            play_duration = timedelta(seconds=random.randint(60, 300))
            confidence = random.uniform(0.7, 1.0)

            # Check if a similar detection already exists
            existing_detection = (
                db.query(TrackDetection)
                .filter(
                    TrackDetection.track_id == track.id,
                    TrackDetection.station_id == station.id,
                    TrackDetection.detected_at == detected_at,
                )
                .first()
            )

            if existing_detection:
                continue

            detection = TrackDetection(
                track_id=track.id,
                station_id=station.id,
                detected_at=detected_at,
                end_time=detected_at + play_duration,
                play_duration=play_duration,
                confidence=confidence,
                fingerprint=f"detection_fingerprint_{i}_{uuid.uuid4()}",
                audio_hash=f"audio_hash_{i}_{uuid.uuid4()}",
            )
            db.add(detection)
            db.commit()
            db.refresh(detection)
            detection_count += 1
            print(f"Created test detection: {track.title} on {station.name} at {detected_at}")

            if detection_count >= 50:
                break

        # Create test reports
        for i in range(1, 4):
            report_title = f"Test Report {i}"
            existing_report = db.query(Report).filter(Report.title == report_title).first()
            if existing_report:
                print(f"Using existing report: {existing_report.title}")
                continue

            period_start = now - timedelta(days=i * 7)
            period_end = now - timedelta(days=(i - 1) * 7)

            report = Report(
                title=report_title,
                type="daily_report",
                report_type="daily",
                format="json",
                status="completed",
                parameters={
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "filters": {"station_id": stations[0].id},
                },
                file_path=f"/path/to/test/report_{i}.json",
                user_id=test_user.id,
                created_by=test_user.id,
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            print(f"Created test report: {report.title}")

        # Create test statistics
        for track in tracks:
            # Check if track stats already exist
            existing_track_stats = (
                db.query(TrackStats).filter(TrackStats.track_id == track.id).first()
            )
            if not existing_track_stats:
                # Track stats
                track_stats = TrackStats(
                    track_id=track.id,
                    total_plays=random.randint(1, 20),
                    total_play_time=timedelta(seconds=random.randint(300, 3600)),
                    last_detected=now - timedelta(hours=random.randint(1, 48)),
                    average_confidence=random.uniform(0.7, 1.0),
                )
                db.add(track_stats)
                print(f"Created track stats for: {track.title}")

            # Station track stats for each station
            for station in stations:
                # Check if station track stats already exist
                existing_station_track_stats = (
                    db.query(StationTrackStats)
                    .filter(
                        StationTrackStats.track_id == track.id,
                        StationTrackStats.station_id == station.id,
                    )
                    .first()
                )

                if not existing_station_track_stats:
                    station_track_stats = StationTrackStats(
                        track_id=track.id,
                        station_id=station.id,
                        play_count=random.randint(1, 10),
                        total_play_time=timedelta(seconds=random.randint(60, 1800)),
                        last_played=now - timedelta(hours=random.randint(1, 48)),
                        average_confidence=random.uniform(0.7, 1.0),
                    )
                    db.add(station_track_stats)
                    print(f"Created station track stats for: {track.title} on {station.name}")

        # Artist stats
        for artist in artists:
            # Check if artist stats already exist
            existing_artist_stats = (
                db.query(ArtistStats).filter(ArtistStats.artist_id == artist.id).first()
            )
            if not existing_artist_stats:
                artist_stats = ArtistStats(
                    artist_id=artist.id,
                    total_plays=random.randint(5, 50),
                    total_play_time=timedelta(seconds=random.randint(600, 7200)),
                    last_detected=now - timedelta(hours=random.randint(1, 48)),
                    average_confidence=random.uniform(0.7, 1.0),
                )
                db.add(artist_stats)
                print(f"Created artist stats for: {artist.name}")

        # Station stats
        for station in stations:
            # Check if station stats already exist
            existing_station_stats = (
                db.query(StationStats).filter(StationStats.station_id == station.id).first()
            )
            if not existing_station_stats:
                station_stats = StationStats(
                    station_id=station.id,
                    detection_count=random.randint(10, 100),
                    last_detected=now - timedelta(hours=random.randint(1, 24)),
                    average_confidence=random.uniform(0.7, 1.0),
                )
                db.add(station_stats)
                print(f"Created station stats for: {station.name}")

        db.commit()
        print("Created test statistics")

        print("Database seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_test_data())
