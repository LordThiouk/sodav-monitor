from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum, Interval, JSON, ARRAY, LargeBinary, Index
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timedelta
import enum
from passlib.context import CryptContext
from typing import Optional, List, Dict, Any, Union

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Base = declarative_base()

class ReportType(str, enum.Enum):
    """Types de rapports disponibles."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    COMPREHENSIVE = "comprehensive"

class ReportStatus(str, enum.Enum):
    """Statuts possibles pour les rapports."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ReportFormat(str, enum.Enum):
    """Formats de rapport disponibles."""
    PDF = "pdf"
    XLSX = "xlsx"
    CSV = "csv"

class StationStatus(str, enum.Enum):
    """Statuts possibles pour les stations."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    OFFLINE = "offline"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    last_login = Column(DateTime)
    role = Column(String, default='user')  # 'admin', 'user', etc.
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    
    reports = relationship("Report", back_populates="user", foreign_keys="Report.user_id")
    created_reports = relationship("Report", back_populates="creator", foreign_keys="Report.created_by")
    subscriptions = relationship("ReportSubscription", back_populates="user", foreign_keys="ReportSubscription.user_id")
    created_subscriptions = relationship("ReportSubscription", back_populates="creator", foreign_keys="ReportSubscription.created_by")

    def set_password(self, password):
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)  # Changed to String to accept any type
    report_type = Column(String, nullable=False)  # Added report_type field
    format = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    progress = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    parameters = Column(JSON, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    file_path = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Added created_by field
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="reports", foreign_keys=[user_id])
    creator = relationship("User", back_populates="created_reports", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Report(id={self.id}, title={self.title}, type={self.type}, status={self.status}, progress={self.progress})>"

class ReportSubscription(Base):
    __tablename__ = "report_subscriptions"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    frequency = Column(String, nullable=False)
    report_type = Column(String, nullable=False)
    format = Column(String, nullable=False)
    parameters = Column(JSON, nullable=True)
    filters = Column(JSON, nullable=True)  # Added filters field
    include_graphs = Column(Boolean, default=True)
    language = Column(String, default="fr")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Added created_by field
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions", foreign_keys=[user_id])
    creator = relationship("User", back_populates="created_subscriptions", foreign_keys=[created_by])

    def __repr__(self):
        return f"<ReportSubscription(id={self.id}, name={self.name}, email={self.email}, frequency={self.frequency})>"

class RadioStation(Base):
    __tablename__ = "radio_stations"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    stream_url = Column(String, nullable=False)
    country = Column(String)
    language = Column(String)
    region = Column(String, nullable=True)
    type = Column(String, default="radio")
    status = Column(String, default="inactive")  # Changed to String
    is_active = Column(Boolean, default=False)
    last_check = Column(DateTime, default=datetime.utcnow)  # Renamed from last_checked
    last_detection_time = Column(DateTime)
    total_play_time = Column(Interval, default=timedelta(seconds=0))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    failure_count = Column(Integer, default=0)

    detections = relationship("TrackDetection", back_populates="station")
    track_stats = relationship("StationTrackStats", back_populates="station")
    status_history = relationship("StationStatusHistory", back_populates="station")

class Artist(Base):
    __tablename__ = 'artists'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    country = Column(String, nullable=True)
    region = Column(String, nullable=True)
    type = Column(String, nullable=True)
    label = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    total_play_time = Column(Interval, default=timedelta(0))
    total_plays = Column(Integer, default=0)
    external_ids = Column(JSON, nullable=True)
    
    tracks = relationship("Track", back_populates="artist", cascade="all, delete-orphan")
    stats = relationship("ArtistStats", back_populates="artist", uselist=False, cascade="all, delete-orphan")
    daily_stats = relationship("ArtistDaily", back_populates="artist", cascade="all, delete-orphan")
    monthly_stats = relationship("ArtistMonthly", back_populates="artist", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Artist(name='{self.name}', country='{self.country}', type='{self.type}', label='{self.label}')>"

class Track(Base):
    """Track model."""
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    artist_id = Column(Integer, ForeignKey("artists.id"))
    isrc = Column(String, index=True)
    label = Column(String)
    album = Column(String)
    duration = Column(Interval)
    fingerprint = Column(String, unique=True)
    fingerprint_raw = Column(LargeBinary)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    artist = relationship("Artist", back_populates="tracks")
    detections = relationship("TrackDetection", back_populates="track")
    stats = relationship("TrackStats", back_populates="track", uselist=False)

class TrackDetection(Base):
    __tablename__ = 'track_detections'
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey('radio_stations.id'), index=True)
    track_id = Column(Integer, ForeignKey('tracks.id'), index=True)
    confidence = Column(Float)
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    end_time = Column(DateTime, index=True)
    play_duration = Column(Interval)
    fingerprint = Column(String)
    audio_hash = Column(String, index=True)
    _is_valid = Column("is_valid", Boolean, default=True)  # Added is_valid column
    
    station = relationship("RadioStation", back_populates="detections")
    track = relationship("Track", back_populates="detections")
    
    @property
    def duration_seconds(self) -> float:
        if self.play_duration:
            return self.play_duration.total_seconds()
        elif self.end_time and self.detected_at:
            return (self.end_time - self.detected_at).total_seconds()
        return 0.0
    
    @property
    def is_valid(self) -> bool:
        return self._is_valid
    
    @is_valid.setter
    def is_valid(self, value: bool):
        self._is_valid = value

class DetectionHourly(Base):
    __tablename__ = 'detection_hourly'

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.id'), nullable=True)  # Made nullable
    station_id = Column(Integer, ForeignKey('radio_stations.id'), nullable=True)  # Made nullable
    hour = Column(DateTime, nullable=False, unique=True)  # Added unique constraint
    count = Column(Integer, default=0)

    track = relationship("Track")
    station = relationship("RadioStation")

class ArtistStats(Base):
    __tablename__ = 'artist_stats'

    id = Column(Integer, primary_key=True)
    artist_id = Column(Integer, ForeignKey('artists.id'), unique=True)
    total_plays = Column(Integer, default=0)  # Renamed from detection_count
    last_detected = Column(DateTime, nullable=True)
    total_play_time = Column(Interval, default=timedelta(0))
    average_confidence = Column(Float, default=0.0)
    
    artist = relationship("Artist", back_populates="stats")

class TrackStats(Base):
    __tablename__ = 'track_stats'

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.id'))
    total_plays = Column(Integer, default=0)  # Renamed from detection_count
    average_confidence = Column(Float, default=0.0)
    last_detected = Column(DateTime, nullable=True)
    total_play_time = Column(Interval, default=timedelta(0))
    
    track = relationship("Track", back_populates="stats")

class AnalyticsData(Base):
    __tablename__ = 'analytics_data'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    detection_count = Column(Integer, default=0)
    detection_rate = Column(Float, default=0.0)
    active_stations = Column(Integer, default=0)
    average_confidence = Column(Float, default=0.0)
    total_tracks = Column(Integer, default=0)
    total_artists = Column(Integer, default=0)
    total_stations = Column(Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'detection_count': self.detection_count,
            'detection_rate': self.detection_rate,
            'active_stations': self.active_stations,
            'average_confidence': self.average_confidence,
            'total_tracks': self.total_tracks,
            'total_artists': self.total_artists,
            'total_stations': self.total_stations
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
    artist_id = Column(Integer, ForeignKey('artists.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    count = Column(Integer, default=0)
    total_play_time = Column(Interval, default=timedelta(0))

    artist = relationship("Artist", back_populates="daily_stats")

class ArtistMonthly(Base):
    __tablename__ = 'artist_monthly'

    id = Column(Integer, primary_key=True)
    artist_id = Column(Integer, ForeignKey('artists.id'), nullable=False)
    month = Column(DateTime, nullable=False)
    count = Column(Integer, default=0)
    total_play_time = Column(Interval, default=timedelta(0))

    artist = relationship("Artist", back_populates="monthly_stats")

class StationTrackStats(Base):
    __tablename__ = 'station_track_stats'

    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey('radio_stations.id'))
    track_id = Column(Integer, ForeignKey('tracks.id'))
    play_count = Column(Integer, default=0)
    total_play_time = Column(Interval, default=timedelta(0))
    last_played = Column(DateTime, nullable=True)
    average_confidence = Column(Float, default=0.0)
    
    station = relationship("RadioStation", back_populates="track_stats")
    track = relationship("Track")

class StationHealth(Base):
    __tablename__ = 'station_health'

    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey('radio_stations.id'), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String)  # 'healthy', 'unhealthy', 'error'
    error_message = Column(Text, nullable=True)
    response_time = Column(Float, nullable=True)  # in seconds
    bitrate = Column(Integer, nullable=True)  # in kbps
    content_type = Column(String, nullable=True)
    failure_count = Column(Integer, default=0)
    
    # Relations
    station = relationship("RadioStation")

    def __repr__(self):
        return f"<StationHealth(station_id={self.station_id}, status='{self.status}', timestamp={self.timestamp})>"

class StationStatusHistory(Base):
    """History of station status changes."""
    __tablename__ = "station_status_history"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("radio_stations.id", ondelete="CASCADE"))
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    station = relationship("RadioStation", back_populates="status_history")
    user = relationship("User", backref="station_status_changes")

# Add indexes for analytics queries
Index('idx_track_detections_detected_at', TrackDetection.detected_at)
Index('idx_track_detections_track_id', TrackDetection.track_id)
Index('idx_track_detections_station_id', TrackDetection.station_id)
Index('idx_track_detections_composite', 
    TrackDetection.station_id, 
    TrackDetection.track_id, 
    TrackDetection.detected_at
)

Index('idx_tracks_title', Track.title)
Index('idx_tracks_artist_id', Track.artist_id)
Index('idx_detections_track_id', TrackDetection.track_id)
Index('idx_detections_station_id', TrackDetection.station_id)
Index('idx_detections_detected_at', TrackDetection.detected_at)
Index('idx_artist_stats_artist_id', ArtistStats.artist_id)
Index('idx_track_stats_track_id', TrackStats.track_id)
Index('idx_station_track_stats_station_id', StationTrackStats.station_id)
Index('idx_station_track_stats_track_id', StationTrackStats.track_id)
Index('idx_artist_daily_artist_id', ArtistDaily.artist_id)
Index('idx_artist_monthly_artist_id', ArtistMonthly.artist_id)
Index('idx_tracks_title_artist_id', Track.title, Track.artist_id)  # Combined index for title and artist_id
