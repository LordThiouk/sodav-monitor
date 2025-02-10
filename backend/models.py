from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum, Interval, JSON, ARRAY, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum

Base = declarative_base()

class ReportType(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

class ReportStatus(enum.Enum):
    pending = "pending"
    generating = "generating"
    completed = "completed"
    failed = "failed"

class StationStatus(enum.Enum):
    active = "active"
    inactive = "inactive"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime)
    role = Column(String, default='user')  # 'admin', 'user', etc.
    
    reports = relationship("Report", back_populates="user")

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)
    format = Column(String, default="csv", nullable=False)
    status = Column(String, default="pending", nullable=False)  # Use string instead of enum
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    file_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    filters = Column(JSON, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    user = relationship("User", back_populates="reports")

class ReportSubscription(Base):
    __tablename__ = 'report_subscriptions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    frequency = Column(String, nullable=False)  # daily, weekly, monthly
    type = Column(String, nullable=False)  # detection, analytics, summary
    recipients = Column(JSON, nullable=False)  # Store email list as JSON array
    next_delivery = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_sent = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    user = relationship("User")

class RadioStation(Base):
    __tablename__ = 'radio_stations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    stream_url = Column(String, nullable=False)
    country = Column(String)
    language = Column(String)
    is_active = Column(Boolean, default=True, index=True)
    last_checked = Column(DateTime, default=datetime.utcnow, index=True)
    last_detection_time = Column(DateTime, nullable=True)
    status = Column(String, default='active')
    
    detections = relationship("TrackDetection", back_populates="station")
    track_stats = relationship("StationTrackStats", back_populates="station")

class Track(Base):
    __tablename__ = 'tracks'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False, index=True)
    isrc = Column(String, nullable=True)  # International Standard Recording Code
    label = Column(String, nullable=True, index=True)
    album = Column(String, nullable=True)
    release_date = Column(DateTime, nullable=True)
    play_count = Column(Integer, default=0)
    total_play_time = Column(Interval, default=timedelta(0))
    last_played = Column(DateTime, nullable=True)
    external_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    fingerprint = Column(String, nullable=True)  # Acoustic fingerprint
    fingerprint_raw = Column(LargeBinary, nullable=True)  # Raw fingerprint data as BLOB
    
    detections = relationship("TrackDetection", back_populates="track")
    stats = relationship("TrackStats", back_populates="track", uselist=False)

class TrackDetection(Base):
    __tablename__ = 'track_detections'
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey('radio_stations.id'), index=True)
    track_id = Column(Integer, ForeignKey('tracks.id'), index=True)
    confidence = Column(Float)
    detected_at = Column(DateTime, default=datetime.now, index=True)
    play_duration = Column(Interval)  # Duration of this specific play
    
    station = relationship("RadioStation", back_populates="detections")
    track = relationship("Track", back_populates="detections")

class DetectionHourly(Base):
    __tablename__ = 'detection_hourly'

    id = Column(Integer, primary_key=True)
    hour = Column(DateTime)
    count = Column(Integer, default=0)

class ArtistStats(Base):
    __tablename__ = 'artist_stats'

    id = Column(Integer, primary_key=True)
    artist_name = Column(String)
    detection_count = Column(Integer, default=0)
    last_detected = Column(DateTime, nullable=True)

class TrackStats(Base):
    __tablename__ = 'track_stats'

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.id'))
    detection_count = Column(Integer, default=0)
    average_confidence = Column(Float, default=0.0)
    last_detected = Column(DateTime, nullable=True)
    
    track = relationship("Track", back_populates="stats")

class AnalyticsData(Base):
    __tablename__ = 'analytics_data'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    detection_count = Column(Integer, default=0)
    detection_rate = Column(Float, default=0.0)
    active_stations = Column(Integer, default=0)
    average_confidence = Column(Float, default=0.0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'detection_count': self.detection_count,
            'detection_rate': self.detection_rate,
            'active_stations': self.active_stations,
            'average_confidence': self.average_confidence
        }

class DetectionDaily(Base):
    __tablename__ = 'detection_daily'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    count = Column(Integer, default=0)

class DetectionMonthly(Base):
    __tablename__ = 'detection_monthly'

    id = Column(Integer, primary_key=True)
    month = Column(DateTime)
    count = Column(Integer, default=0)

class StationStats(Base):
    __tablename__ = 'station_stats'

    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey('radio_stations.id'))
    detection_count = Column(Integer, default=0)
    last_detected = Column(DateTime)
    average_confidence = Column(Float, default=0.0)

class TrackDaily(Base):
    __tablename__ = 'track_daily'

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.id'))
    date = Column(DateTime)
    count = Column(Integer, default=0)

class TrackMonthly(Base):
    __tablename__ = 'track_monthly'

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.id'))
    month = Column(DateTime)
    count = Column(Integer, default=0)

class ArtistDaily(Base):
    __tablename__ = 'artist_daily'

    id = Column(Integer, primary_key=True)
    artist_name = Column(String)
    date = Column(DateTime)
    count = Column(Integer, default=0)

class ArtistMonthly(Base):
    __tablename__ = 'artist_monthly'

    id = Column(Integer, primary_key=True)
    artist_name = Column(String)
    month = Column(DateTime)
    count = Column(Integer, default=0)

class StationTrackStats(Base):
    __tablename__ = 'station_track_stats'

    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey('radio_stations.id'))
    track_id = Column(Integer, ForeignKey('tracks.id'))
    play_count = Column(Integer, default=0)
    total_play_time = Column(Interval, default=timedelta(0))
    last_played = Column(DateTime)
    average_confidence = Column(Float, default=0.0)
    
    station = relationship("RadioStation", back_populates="track_stats")
    track = relationship("Track")
