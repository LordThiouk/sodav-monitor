from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum, Interval, JSON, ARRAY, LargeBinary, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

    def set_password(self, password):
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # detection, analytics, summary, artist, track, station
    format = Column(String, default="csv", nullable=False)  # csv, xlsx, json
    status = Column(String, default="pending", nullable=False)  # pending, generating, completed, failed
    progress = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    file_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    filters = Column(JSON, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    user = relationship("User", back_populates="reports")

    def __repr__(self):
        return f"<Report(id={self.id}, type={self.type}, status={self.status}, progress={self.progress})>"

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
    __tablename__ = "radio_stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    stream_url = Column(String)
    country = Column(String)
    language = Column(String)
    region = Column(String, nullable=True)  # Added region field
    type = Column(String, default="radio")  # Added type field
    status = Column(Enum(StationStatus), default=StationStatus.inactive)
    is_active = Column(Boolean, default=False)
    last_checked = Column(DateTime)
    last_detection_time = Column(DateTime)
    total_play_time = Column(Interval, default=timedelta(seconds=0))
    created_at = Column(DateTime, default=datetime.now)  # Added created_at field

    detections = relationship("TrackDetection", back_populates="station")
    track_stats = relationship("StationTrackStats", back_populates="station")

class Artist(Base):
    __tablename__ = 'artists'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    country = Column(String, nullable=True)  # Pour les statistiques par pays
    region = Column(String, nullable=True)   # Pour les statistiques régionales
    type = Column(String, nullable=True)     # solo, group, band, etc.
    label = Column(String, nullable=True, index=True)  # Pour le label de l'artiste
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    total_play_time = Column(Interval, default=timedelta(0))
    total_plays = Column(Integer, default=0)
    external_ids = Column(JSON, nullable=True)  # Pour stocker les IDs externes (Spotify, Deezer, etc.)
    
    # Relations
    tracks = relationship("Track", back_populates="artist", cascade="all, delete-orphan")
    stats = relationship("ArtistStats", back_populates="artist", uselist=False, cascade="all, delete-orphan")
    daily_stats = relationship("ArtistDaily", back_populates="artist", cascade="all, delete-orphan")
    monthly_stats = relationship("ArtistMonthly", back_populates="artist", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Artist(name='{self.name}', country='{self.country}', type='{self.type}', label='{self.label}')>"

class Track(Base):
    __tablename__ = 'tracks'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    artist_id = Column(Integer, ForeignKey('artists.id'), nullable=False)  # Changer artist en artist_id
    isrc = Column(String, nullable=True)
    label = Column(String, nullable=True, index=True)
    album = Column(String, nullable=True)
    release_date = Column(DateTime, nullable=True)
    play_count = Column(Integer, default=0)
    total_play_time = Column(Interval, default=timedelta(0))
    last_played = Column(DateTime, nullable=True)
    external_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    fingerprint = Column(String, nullable=True)
    fingerprint_raw = Column(LargeBinary, nullable=True)
    
    # Relations
    artist = relationship("Artist", back_populates="tracks")
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
    artist_id = Column(Integer, ForeignKey('artists.id'), unique=True)
    detection_count = Column(Integer, default=0)
    last_detected = Column(DateTime, nullable=True)
    total_play_time = Column(Interval, default=timedelta(0))
    average_confidence = Column(Float, default=0.0)
    
    # Relation
    artist = relationship("Artist", back_populates="stats")

class TrackStats(Base):
    __tablename__ = 'track_stats'

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.id'))
    detection_count = Column(Integer, default=0)
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
    artist_id = Column(Integer, ForeignKey('artists.id'))  # Changer artist_name en artist_id
    date = Column(DateTime)
    count = Column(Integer, default=0)
    total_play_time = Column(Interval, default=timedelta(0))
    
    # Relation
    artist = relationship("Artist", back_populates="daily_stats")

class ArtistMonthly(Base):
    __tablename__ = 'artist_monthly'

    id = Column(Integer, primary_key=True)
    artist_id = Column(Integer, ForeignKey('artists.id'))  # Changer artist_name en artist_id
    month = Column(DateTime)
    count = Column(Integer, default=0)
    total_play_time = Column(Interval, default=timedelta(0))
    
    # Relation
    artist = relationship("Artist", back_populates="monthly_stats")

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

# Add indexes for analytics queries
Index('idx_track_detections_detected_at', TrackDetection.detected_at)
Index('idx_track_detections_track_id', TrackDetection.track_id)
Index('idx_track_detections_station_id', TrackDetection.station_id)
Index('idx_track_detections_composite', 
    TrackDetection.station_id, 
    TrackDetection.track_id, 
    TrackDetection.detected_at
)

Index('idx_artist_stats_artist_id', ArtistStats.artist_id)

Index('idx_track_stats_track_id', TrackStats.track_id)
Index('idx_track_stats_detection_count', TrackStats.detection_count)

Index('idx_station_track_stats_composite',
    StationTrackStats.station_id,
    StationTrackStats.track_id
)

Index('idx_detection_hourly_hour', DetectionHourly.hour)
Index('idx_detection_daily_date', DetectionDaily.date)
Index('idx_detection_monthly_month', DetectionMonthly.month)

Index('idx_track_daily_composite',
    TrackDaily.track_id,
    TrackDaily.date
)

Index('idx_track_monthly_composite',
    TrackMonthly.track_id,
    TrackMonthly.month
)

Index('idx_artist_daily_composite',
    ArtistDaily.artist_id,
    ArtistDaily.date
)

Index('idx_artist_monthly_composite',
    ArtistMonthly.artist_id,
    ArtistMonthly.month
)
