from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Interval, Boolean, Text, Enum
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
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

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
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    type = Column(Enum(ReportType), nullable=False)
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING)
    format = Column(String, default='csv')  # csv, xlsx, pdf
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    filters = Column(JSON)  # Store any additional filters
    file_path = Column(String)  # Path to generated report file
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    user = relationship("User", back_populates="reports")

class RadioStation(Base):
    __tablename__ = 'radio_stations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    stream_url = Column(String, nullable=False)
    country = Column(String)
    language = Column(String)
    is_active = Column(Integer, default=1)
    last_checked = Column(DateTime, default=datetime.now)
    
    detections = relationship("TrackDetection", back_populates="station")

class Track(Base):
    __tablename__ = 'tracks'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    isrc = Column(String)  # International Standard Recording Code
    label = Column(String)  # Record label
    album = Column(String)  # Album name
    release_date = Column(String)  # Release date
    play_count = Column(Integer, default=0)  # Number of times played
    total_play_time = Column(Interval, default=timedelta(0))  # Total time played
    last_played = Column(DateTime)  # Last time the track was played
    external_ids = Column(JSON)  # Store IDs from various services (Spotify, Deezer, etc.)
    created_at = Column(DateTime, default=datetime.now)
    
    detections = relationship("TrackDetection", back_populates="track")

class TrackDetection(Base):
    __tablename__ = 'track_detections'
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey('radio_stations.id'))
    track_id = Column(Integer, ForeignKey('tracks.id'))
    confidence = Column(Float)
    detected_at = Column(DateTime, default=datetime.now)
    play_duration = Column(Interval)  # Duration of this specific play
    
    station = relationship("RadioStation", back_populates="detections")
    track = relationship("Track", back_populates="detections")
