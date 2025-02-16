from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks, UploadFile, File, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import uvicorn
import json
import os
from logging.handlers import RotatingFileHandler
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, distinct, case, and_, text
import librosa
from models import Base, RadioStation, Track, TrackDetection, User, Report, ReportStatus
from database import SessionLocal, engine
from audio_processor import AudioProcessor
from music_recognition import MusicRecognizer
from fingerprint import AudioProcessor as FingerprintProcessor
from radio_manager import RadioManager
from fingerprint_generator import generate_fingerprint
from routers.analytics import router as analytics_router
from routers.channels import router as channels_router
from routers.reports import router as reports_router
from routers import channels, detections
from utils.logging_config import setup_logging
from health_check import get_system_health

# Load environment variables
load_dotenv()

# Configure logging
logger = setup_logging(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SODAV Media Monitor", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes must be mounted before the frontend static files
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(channels_router)
app.include_router(reports_router, prefix="/api/reports", tags=["reports"])
app.include_router(channels.router)
app.include_router(detections.router)

# Fallback route for API 404s
@app.exception_handler(404)
async def not_found_handler(request, exc):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=404,
            content={"detail": "API route not found"}
        )
    raise exc  # Let nginx handle non-API routes

# Security configurations
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic models for API
class TrackBase(BaseModel):
    title: str
    artist: str
    duration: int
    confidence: float

class StreamBase(BaseModel):
    name: str
    type: str
    status: str
    region: str
    language: str
    stream_url: str

class DetectionResponse(BaseModel):
    station_name: str
    track_title: str
    artist: str
    detected_at: datetime
    confidence: float

class StreamRequest(BaseModel):
    stream_url: str

class ChartData(BaseModel):
    hour: int
    count: int

class SystemHealth(BaseModel):
    status: str
    uptime: int
    lastError: Optional[str] = None

class AnalyticsResponse(BaseModel):
    totalDetections: int
    detectionRate: float
    activeStations: int
    totalStations: int
    averageConfidence: float
    detectionsByHour: List[ChartData]
    topArtists: List[Dict[str, Union[str, int]]]
    systemHealth: SystemHealth

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize MusicRecognizer and AudioProcessor
db_session = SessionLocal()
music_recognizer = MusicRecognizer(db_session=db_session)
processor = AudioProcessor(db_session=db_session, music_recognizer=music_recognizer)

# Store active connections
active_connections: List[WebSocket] = []

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    if SessionLocal():
        SessionLocal().close()

@app.get("/api/streams")
async def get_streams(db: Session = Depends(get_db)):
    """Return list of streams from the database"""
    stations = db.query(RadioStation).all()
    return {
        "streams": [
            {
                "id": station.id,
                "name": station.name,
                "url": station.stream_url,
                "status": "active" if station.is_active else "inactive",
                "type": "radio",
                "location": station.country,
                "language": station.language
            }
            for station in stations
        ]
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint avec vérifications détaillées"""
    return get_system_health()

@app.post("/api/detect/{stream_id}")
async def detect_audio(stream_id: int):
    """Detect music from a specific stream"""
    station = SessionLocal().query(RadioStation).filter(RadioStation.id == stream_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    try:
        result = await processor.analyze_stream(station.stream_url, station.id)
        return result
    except Exception as e:
        logger.error(f"Error detecting audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tracks/add")
async def add_track(
    title: str,
    artist: str,
    audio_file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Add a new track to the database with its audio fingerprint."""
    try:
        # Save audio file temporarily
        file_location = f"/tmp/{audio_file.filename}"
        with open(file_location, "wb+") as file_object:
            file_object.write(await audio_file.read())

        # Generate fingerprint
        y, sr = librosa.load(file_location)
        fingerprint = generate_fingerprint(y, sr)

        # Create track in database
        db = SessionLocal()
        track = Track(
            title=title,
            artist=artist,
            fingerprint=fingerprint,
            fingerprint_hash=AudioProcessor._hash_fingerprint(fingerprint)
        )
        db.add(track)
        db.commit()
        db.refresh(track)
        db.close()

        return {"message": "Track added successfully", "track_id": track.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stations")
async def get_stations(db: Session = Depends(get_db)):
    """Get all radio stations with their current status."""
    try:
        stations = db.query(RadioStation).all()
        station_list = []
        
        for station in stations:
            try:
                # Validate last_checked
                last_checked = None
                if station.last_checked and str(station.last_checked) not in ['0', '', 'None', 'null', '0:00:00']:
                    try:
                        if isinstance(station.last_checked, datetime):
                            last_checked = station.last_checked.isoformat()
                        elif isinstance(station.last_checked, str):
                            last_checked = datetime.fromisoformat(station.last_checked).isoformat()
                    except (ValueError, AttributeError):
                        last_checked = None
                
                # Validate last_detection_time
                last_detection_time = None
                if station.last_detection_time and str(station.last_detection_time) not in ['0', '', 'None', 'null', '0:00:00']:
                    try:
                        if isinstance(station.last_detection_time, datetime):
                            last_detection_time = station.last_detection_time.isoformat()
                        elif isinstance(station.last_detection_time, str):
                            last_detection_time = datetime.fromisoformat(station.last_detection_time).isoformat()
                    except (ValueError, AttributeError):
                        last_detection_time = None
                
                station_data = {
                    "id": station.id,
                    "name": station.name,
                    "stream_url": station.stream_url,
                    "country": station.country,
                    "language": station.language,
                    "is_active": bool(station.is_active),
                    "last_checked": last_checked,
                    "last_detection_time": last_detection_time,
                    "total_play_time": station.total_play_time,
                    "status": station.status.value if station.status else "inactive"
                }
                station_list.append(station_data)
                
            except Exception as e:
                logger.error(f"Error processing station {station.id}: {str(e)}")
                continue
                
        return station_list
        
    except Exception as e:
        logger.error(f"Error getting stations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stations/search")
async def search_stations(name: str, db: Session = Depends(get_db)):
    """Search for a radio station by name."""
    station = db.query(RadioStation).filter(RadioStation.name.ilike(f"%{name}%")).first()
    if not station:
        # If station not found, create it with default values
        station = RadioStation(
            name=name,
            stream_url="",  # Will be updated later
            country="Senegal",
            language="French/Wolof",
            is_active=False,
            last_checked=datetime.now()
        )
        db.add(station)
        db.commit()
        db.refresh(station)
    
    return {
        "id": station.id,
        "name": station.name,
        "stream_url": station.stream_url,
        "country": station.country,
        "language": station.language,
        "is_active": station.is_active,
        "last_checked": station.last_checked.isoformat()
    }

@app.post("/api/stations/{station_id}/check")
async def check_station(station_id: int, db: Session = Depends(get_db)):
    """Check station status and analyze stream."""
    try:
        # Get station from database
        station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        
        # Check stream status
        status = await processor.check_stream_status(station.stream_url)
        
        # Update station status in database
        station.is_active = status["ok"]
        station.last_checked = datetime.now()
        db.commit()
        
        # If stream is active, try to detect music
        detection_result = None
        if status["ok"]:
            detection_result = await processor.analyze_stream(station.stream_url, station_id)
        
        return {
            "status": status,
            "detection": detection_result,
            "station": {
                "id": station.id,
                "name": station.name,
                "stream_url": station.stream_url,
                "is_active": station.is_active,
                "last_checked": station.last_checked.isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error checking station {station_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stations/{station_id}/stats")
async def get_station_stats(
    station_id: int,
    time_range: str = "24h"  # Options: 24h, 7d, 30d
):
    """Get detailed statistics for a specific radio station."""
    db = SessionLocal()
    try:
        station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        
        # Calculate time range
        now = datetime.now()
        if time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            raise HTTPException(status_code=400, detail="Invalid time range")
        
        # Get detections for the period
        detections = db.query(TrackDetection).filter(
            TrackDetection.station_id == station_id,
            TrackDetection.detected_at >= start_time
        ).all()
        
        # Calculate statistics
        total_play_time = sum((d.play_duration.total_seconds() for d in detections), 0)
        unique_tracks = len(set(d.track_id for d in detections))
        
        # Get top tracks
        track_plays = {}
        for detection in detections:
            track_plays[detection.track_id] = track_plays.get(detection.track_id, 0) + detection.play_duration.total_seconds()
        
        top_tracks = []
        for track_id, play_time in sorted(track_plays.items(), key=lambda x: x[1], reverse=True)[:10]:
            track = db.query(Track).filter(Track.id == track_id).first()
            if track:
                top_tracks.append({
                    "title": track.title,
                    "artist": track.artist,
                    "play_time": str(timedelta(seconds=int(play_time))),
                    "play_count": sum(1 for d in detections if d.track_id == track_id)
                })
        
        return {
            "station_id": station_id,
            "station_name": station.name,
            "time_range": time_range,
            "metrics": {
                "total_play_time": str(timedelta(seconds=int(total_play_time))),
                "detection_count": len(detections),
                "unique_tracks": unique_tracks,
                "average_track_duration": str(timedelta(seconds=int(total_play_time / len(detections)))) if detections else "0:00:00",
                "uptime_percentage": total_play_time / (now - start_time).total_seconds() * 100
            },
            "top_tracks": top_tracks
        }
    finally:
        db.close()

@app.get("/api/stations/status/summary")
async def get_stations_status_summary():
    """Get a summary of all stations status."""
    db = SessionLocal()
    try:
        stations = db.query(RadioStation).all()
        total_stations = len(stations)
        active_stations = sum(1 for s in stations if s.is_active)
        
        # Get recent detections
        recent_detections = db.query(TrackDetection).filter(
            TrackDetection.detected_at >= datetime.now() - timedelta(hours=24)
        ).all()
        
        total_play_time = sum((d.play_duration.total_seconds() for d in recent_detections), 0)
        unique_tracks = len(set(d.track_id for d in recent_detections))
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_stations": total_stations,
            "active_stations": active_stations,
            "inactive_stations": total_stations - active_stations,
            "metrics_24h": {
                "total_detections": len(recent_detections),
                "unique_tracks": unique_tracks,
                "total_play_time": str(timedelta(seconds=int(total_play_time))),
                "average_uptime": f"{(active_stations / total_stations * 100):.1f}%"
            }
        }
    finally:
        db.close()

@app.get("/api/detections")
async def get_detections(
    station_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get track detections, optionally filtered by station and date range"""
    try:
        # Start with base query
        query = db.query(TrackDetection).options(
            joinedload(TrackDetection.station),
            joinedload(TrackDetection.track)
        )
        
        # Apply filters
        if station_id:
            query = query.filter(TrackDetection.station_id == station_id)
        if start_date:
            query = query.filter(TrackDetection.detected_at >= start_date)
        if end_date:
            query = query.filter(TrackDetection.detected_at <= end_date)
        
        # Get detections ordered by most recent first
        detections = query.order_by(TrackDetection.detected_at.desc()).all()
        
        # Format response
        return {
            "detections": [
                {
                    "id": d.id,
                    "station_id": d.station_id,
                    "track_id": d.track_id,
                    "station_name": d.station.name if d.station else None,
                    "track_title": d.track.title if d.track else None,
                    "artist": d.track.artist if d.track else None,
                    "detected_at": d.detected_at.isoformat(),
                    "confidence": d.confidence,
                    "play_duration": str(d.play_duration) if d.play_duration else "0",
                    "track": {
                        "id": d.track.id if d.track else None,
                        "title": d.track.title if d.track else None,
                        "artist": d.track.artist if d.track else None,
                        "isrc": d.track.isrc if d.track else None,
                        "label": d.track.label if d.track else None,
                        "album": d.track.album if d.track else None,
                        "release_date": d.track.release_date.isoformat() if d.track and d.track.release_date else None,
                        "play_count": d.track.play_count if d.track else 0,
                        "total_play_time": str(d.track.total_play_time) if d.track and d.track.total_play_time else "0",
                        "last_played": d.track.last_played.isoformat() if d.track and d.track.last_played else None,
                        "external_ids": d.track.external_ids if d.track else {},
                        "created_at": d.track.created_at.isoformat() if d.track and d.track.created_at else None
                    }
                }
                for d in detections
            ]
        }
    except Exception as e:
        logger.error(f"Error getting detections: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports")
async def get_reports(db: Session = Depends(get_db)):
    """Return list of reports based on actual detection data"""
    try:
        # Get detection data from the last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        detections = db.query(TrackDetection).filter(
            TrackDetection.detected_at >= yesterday
        ).all()
        
        # Get station status changes
        stations = db.query(RadioStation).all()
        inactive_stations = [s for s in stations if not s.is_active]
        
        reports = []
        
        # Daily summary report
        reports.append({
            "id": 1,
            "date": datetime.now().isoformat(),
            "type": "Daily Summary",
            "status": "success",
            "content": f"Monitored 24 hours of content across all stations. Detected {len(detections)} tracks."
        })
        
        # Station status report
        if inactive_stations:
            reports.append({
                "id": 2,
                "date": datetime.now().isoformat(),
                "type": "System Status",
                "status": "warning",
                "content": f"{len(inactive_stations)} station(s) currently offline."
            })
        
        return {"reports": reports}
    except Exception as e:
        logger.error(f"Error generating reports: {e}")
        raise HTTPException(status_code=500, detail="Error generating reports")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    from utils.websocket import active_connections
    
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial data
        from models import TrackDetection, RadioStation
        from sqlalchemy import desc
        
        # Get database session
        db = SessionLocal()
        try:
            # Get all stations
            stations = db.query(RadioStation).all()
            active_station_count = len([s for s in stations if s.is_active])
            
            # Get recent detections
            recent_detections = (
                db.query(TrackDetection)
                .order_by(desc(TrackDetection.detected_at))
                .limit(50)
                .all()
            )
            
            # Convert to dict
            detections = []
            for detection in recent_detections:
                track = {
                    "id": detection.track.id if detection.track else None,
                    "title": detection.track.title if detection.track else None,
                    "artist": detection.track.artist if detection.track else None,
                    "isrc": detection.track.isrc if detection.track else None,
                    "label": detection.track.label if detection.track else None,
                    "album": detection.track.album if detection.track else None,
                    "release_date": detection.track.release_date.isoformat() if detection.track and detection.track.release_date else None,
                    "play_count": detection.track.play_count if detection.track else 0,
                    "total_play_time": str(detection.track.total_play_time) if detection.track and detection.track.total_play_time else "0:00:00",
                    "last_played": detection.track.last_played.isoformat() if detection.track and detection.track.last_played else None,
                    "external_ids": detection.track.external_ids if detection.track else {},
                    "created_at": detection.track.created_at.isoformat() if detection.track and detection.track.created_at else None
                }
                
                detections.append({
                    "id": detection.id,
                    "station_id": detection.station_id,
                    "track_id": detection.track_id,
                    "station_name": detection.station.name if detection.station else None,
                    "track_title": detection.track.title if detection.track else None,
                    "artist": detection.track.artist if detection.track else None,
                    "detected_at": detection.detected_at.isoformat(),
                    "confidence": detection.confidence,
                    "play_duration": str(detection.play_duration) if detection.play_duration else "0:00:15",  # Default to 15 seconds if not set
                    "track": track
                })
            
            # Send initial data
            await websocket.send_json({
                "type": "initial_data",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "active_stations": active_station_count,
                    "recent_detections": detections
                }
            })
        finally:
            db.close()
            
        # Keep connection alive and handle pings
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
                
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

async def broadcast_track_detection(track_data: Dict):
    """Broadcast track detection to all connected clients"""
    from utils.websocket import active_connections
    
    # Format the track data for frontend
    track = {
        "id": track_data.get("track_id"),
        "title": track_data.get("title"),
        "artist": track_data.get("artist"),
        "isrc": track_data.get("isrc"),
        "label": track_data.get("label"),
        "album": track_data.get("album"),
        "release_date": track_data.get("release_date"),
        "play_count": track_data.get("play_count", 0),
        "total_play_time": str(track_data.get("total_play_time", timedelta(seconds=15))),
        "last_played": track_data.get("last_played"),
        "external_ids": track_data.get("external_ids", {}),
        "created_at": track_data.get("created_at")
    }
    
    # Ensure play_duration is never 0
    play_duration = track_data.get("play_duration")
    if not play_duration or str(play_duration) == "0":
        play_duration = timedelta(seconds=15)  # Default to 15 seconds
    
    detection_data = {
        "type": "track_detection",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "id": track_data.get("id"),
            "station_id": track_data.get("station_id"),
            "track_id": track_data.get("track_id"),
            "station_name": track_data.get("station_name"),
            "track_title": track_data.get("title"),
            "artist": track_data.get("artist"),
            "detected_at": track_data.get("detected_at", datetime.now().isoformat()),
            "confidence": track_data.get("confidence"),
            "play_duration": str(play_duration),
            "track": track
        }
    }
    
    # Send to all connected clients
    for connection in active_connections:
        try:
            await connection.send_json(detection_data)
        except Exception as e:
            logger.error(f"Error sending detection to client: {e}")
            active_connections.remove(connection)

@app.post("/api/detect")
async def detect_music(request: StreamRequest):
    """Detect music from a stream URL"""
    try:
        # Analyze stream
        result = await processor.analyze_stream(request.stream_url)
        return result
    except Exception as e:
        logger.error(f"Error in detect_music: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Pydantic models for user and report
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: int
    is_active: bool
    role: str
    created_at: datetime

class ReportRequest(BaseModel):
    type: str
    format: str = "csv"
    start_date: datetime
    end_date: datetime
    filters: Optional[Dict] = None

class ReportResponse(BaseModel):
    id: int
    type: str
    status: str
    format: str
    created_at: datetime
    completed_at: Optional[datetime] = None

# Security functions
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# User management endpoints
@app.post("/api/users", response_model=UserInDB)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/api/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token"""
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user or not verify_password(form_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update user's last login time and ensure they are active
        user.last_login = datetime.utcnow()
        user.is_active = True
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create access token with user information
        access_token = create_access_token(
            data={
                "sub": user.username,
                "id": user.id,
                "email": user.email,
                "role": user.role
            }
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during login process"
        )

# Report management endpoints
@app.post("/api/reports", response_model=ReportResponse)
async def create_report(
    report_request: ReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new report"""
    report = Report(
        type=report_request.type,
        format=report_request.format,
        start_date=report_request.start_date,
        end_date=report_request.end_date,
        filters=report_request.filters,
        status='pending'
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    # Start report generation in background
    background_tasks.add_task(generate_report, report.id, db)
    
    return report

@app.get("/api/reports", response_model=List[ReportResponse])
async def list_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all reports for the current user"""
    reports = db.query(Report).filter(Report.user_id == current_user.id).all()
    return reports

@app.get("/api/reports/{report_id}/download")
async def download_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a generated report"""
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == current_user.id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status != 'completed':
        raise HTTPException(status_code=400, detail="Report not ready for download")
    
    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        report.file_path,
        filename=f"report_{report.id}_{report.type}_{report.created_at.date()}.{report.format}"
    )

async def generate_report(report_id: int, db: Session):
    """Background task to generate report"""
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return

        report.status = "completed"
        report.completed_at = datetime.now()
        
    except Exception as e:
        report.status = "failed"
        report.error_message = str(e)
        logger.error(f"Error generating report {report_id}: {e}")
    
    finally:
        db.commit()

from datetime import timedelta
from typing import Optional, List
from fastapi import Query

@app.get("/api/analytics/tracks")
async def get_tracks_analytics(
    time_range: str = Query("24h", description="Time range for analytics (e.g., '7d' for 7 days)"),
    db: Session = Depends(get_db)
):
    """Get detailed track analytics for a specific time range"""
    try:
        # Parse time range
        unit = time_range[-1].lower()
        value = int(time_range[:-1])
        
        if unit == 'd':
            delta = timedelta(days=value)
        elif unit == 'h':
            delta = timedelta(hours=value)
        else:
            raise ValueError(f"Invalid time range format: {time_range}. Use format like '7d' or '24h'")
        
        start_time = datetime.now() - delta
        
        # Get track analytics with all required information
        tracks = (
            db.query(
                Track.id,
                Track.title,
                Track.artist,
                Track.album,
                Track.isrc,
                Track.label,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(func.strftime('%s', TrackDetection.play_duration)).label('total_play_time'),
                func.count(distinct(TrackDetection.station_id)).label('unique_stations'),
                func.group_concat(distinct(RadioStation.name)).label('stations')
            )
            .join(TrackDetection, Track.id == TrackDetection.track_id)
            .join(RadioStation, TrackDetection.station_id == RadioStation.id)
            .filter(TrackDetection.detected_at >= start_time)
            .group_by(Track.id)
            .order_by(func.count(TrackDetection.id).desc())
            .all()
        )
        
        # Format response
        return [
            {
                "id": id,
                "title": title,
                "artist": artist,
                "album": album,
                "isrc": isrc,
                "label": label,
                "detection_count": detection_count or 0,
                "total_play_time": str(timedelta(seconds=int(total_play_time))) if total_play_time else "0:00:00",
                "unique_stations": unique_stations or 0,
                "stations": stations.split(',') if stations else []
            }
            for id, title, artist, album, isrc, label, detection_count, total_play_time, unique_stations, stations in tracks
        ]
        
    except Exception as e:
        logger.error(f"Error getting tracks analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting tracks analytics: {str(e)}"
        )

@app.get("/api/analytics/artists")
async def get_artist_analytics(
    time_range: str = Query(..., description="Time range for analytics (e.g., '7d' for 7 days)"),
    db: Session = Depends(get_db)
):
    """Get artist analytics for a specific time range"""
    try:
        # Parse time range
        unit = time_range[-1].lower()
        value = int(time_range[:-1])
        
        if unit == 'd':
            delta = timedelta(days=value)
        elif unit == 'h':
            delta = timedelta(hours=value)
        else:
            raise ValueError(f"Invalid time range format: {time_range}. Use format like '7d' or '24h'")
        
        start_time = datetime.now() - delta
        
        # Get artist detections in the time range
        detections = (
            db.query(
                Track.artist,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(func.strftime('%s', TrackDetection.play_duration)).label('total_play_time'),
                func.count(distinct(Track.id)).label('unique_tracks'),
                func.group_concat(distinct(Track.title)).label('tracks'),
                func.group_concat(distinct(Track.album)).label('albums'),
                func.group_concat(distinct(Track.label)).label('labels'),
                func.group_concat(distinct(RadioStation.name)).label('stations')
            )
            .join(TrackDetection, Track.id == TrackDetection.track_id)
            .join(RadioStation, TrackDetection.station_id == RadioStation.id)
            .filter(TrackDetection.detected_at >= start_time)
            .group_by(Track.artist)
            .order_by(func.count(TrackDetection.id).desc())
            .all()
        )
        
        # Format response
        results = []
        for (artist, detection_count, total_play_time, unique_tracks, tracks, albums, labels, stations) in detections:
            # Split concatenated strings into lists
            track_list = tracks.split(',') if tracks else []
            album_list = list(set(albums.split(',') if albums else []))
            label_list = list(set(labels.split(',') if labels else []))
            station_list = list(set(stations.split(',') if stations else []))
            
            results.append({
                "artist": artist,
                "detection_count": detection_count,
                "total_play_time": str(timedelta(seconds=int(total_play_time))) if total_play_time else "0:00:00",
                "unique_tracks": unique_tracks,
                "tracks": track_list,
                "unique_albums": len(album_list),
                "albums": album_list,
                "unique_labels": len(label_list),
                "labels": label_list,
                "unique_stations": len(station_list),
                "stations": station_list
            })
        
        return {
            "time_range": time_range,
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "end_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "total_artists": len(results),
            "artists": results
        }
        
    except Exception as e:
        logger.error(f"Error getting artist analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting artist analytics: {str(e)}"
        )

@app.get("/api/analytics/labels")
async def get_label_analytics(
    time_range: str = Query(..., description="Time range for analytics (e.g., '7d' for 7 days)"),
    db: Session = Depends(get_db)
):
    """Get label analytics for a specific time range"""
    try:
        # Parse time range
        unit = time_range[-1].lower()
        value = int(time_range[:-1])
        
        if unit == 'd':
            delta = timedelta(days=value)
        elif unit == 'h':
            delta = timedelta(hours=value)
        else:
            raise ValueError(f"Invalid time range format: {time_range}. Use format like '7d' or '24h'")
        
        start_time = datetime.now() - delta
        
        # Get label detections in the time range
        detections = (
            db.query(
                Track.label,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(func.strftime('%s', TrackDetection.play_duration)).label('total_play_time'),
                func.count(distinct(Track.id)).label('unique_tracks'),
                func.group_concat(distinct(Track.title)).label('tracks'),
                func.group_concat(distinct(Track.artist)).label('artists'),
                func.group_concat(distinct(Track.album)).label('albums'),
                func.group_concat(distinct(RadioStation.name)).label('stations')
            )
            .join(TrackDetection, Track.id == TrackDetection.track_id)
            .join(RadioStation, TrackDetection.station_id == RadioStation.id)
            .filter(TrackDetection.detected_at >= start_time)
            .filter(Track.label.isnot(None))  # Exclude tracks without labels
            .group_by(Track.label)
            .order_by(func.count(TrackDetection.id).desc())
            .all()
        )
        
        # Format response
        results = []
        for (label, detection_count, total_play_time, unique_tracks, tracks, artists, albums, stations) in detections:
            # Split concatenated strings into lists
            track_list = tracks.split(',') if tracks else []
            artist_list = list(set(artists.split(',') if artists else []))
            album_list = list(set(albums.split(',') if albums else []))
            station_list = list(set(stations.split(',') if stations else []))
            
            results.append({
                "label": label,
                "detection_count": detection_count,
                "total_play_time": str(timedelta(seconds=int(total_play_time))) if total_play_time else "0:00:00",
                "unique_tracks": unique_tracks,
                "tracks": track_list,
                "unique_artists": len(artist_list),
                "artists": artist_list,
                "unique_albums": len(album_list),
                "albums": album_list,
                "unique_stations": len(station_list),
                "stations": station_list
            })
        
        return {
            "time_range": time_range,
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "end_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "total_labels": len(results),
            "labels": results
        }
        
    except Exception as e:
        logger.error(f"Error getting label analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting label analytics: {str(e)}"
        )

@app.get("/api/analytics/channels")
async def get_channel_analytics(
    time_range: str = Query(..., description="Time range for analytics (e.g., '7d' for 7 days)"),
    db: Session = Depends(get_db)
):
    """Get channel analytics for a specific time range"""
    try:
        # Parse time range
        unit = time_range[-1].lower()
        value = int(time_range[:-1])
        
        if unit == 'd':
            delta = timedelta(days=value)
        elif unit == 'h':
            delta = timedelta(hours=value)
        else:
            raise ValueError(f"Invalid time range format: {time_range}. Use format like '7d' or '24h'")
        
        start_time = datetime.now() - delta
        
        # Get channel detections in the time range
        detections = (
            db.query(
                RadioStation.id,
                RadioStation.name,
                RadioStation.stream_url,
                RadioStation.country,
                RadioStation.language,
                RadioStation.status,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(func.strftime('%s', TrackDetection.play_duration)).label('total_play_time'),
                func.count(distinct(Track.id)).label('unique_tracks'),
                func.group_concat(distinct(Track.title)).label('tracks'),
                func.group_concat(distinct(Track.artist)).label('artists'),
                func.group_concat(distinct(Track.label)).label('labels'),
                func.count(distinct(Track.artist)).label('unique_artists'),
                func.count(distinct(Track.label)).label('unique_labels')
            )
            .outerjoin(TrackDetection, and_(
                RadioStation.id == TrackDetection.station_id,
                TrackDetection.detected_at >= start_time
            ))
            .outerjoin(Track, TrackDetection.track_id == Track.id)
            .group_by(RadioStation.id)
            .order_by(func.count(TrackDetection.id).desc())
            .all()
        )
        
        # Format response
        results = []
        for (
            station_id, name, stream_url, country, language, status, 
            detection_count, total_play_time, unique_tracks, tracks, 
            artists, labels, unique_artists, unique_labels
        ) in detections:
            # Split concatenated strings into lists
            track_list = tracks.split(',') if tracks else []
            artist_list = list(set(artists.split(',') if artists else []))
            label_list = list(set(labels.split(',') if labels else []))
            
            # Calculate detection rate (detections per hour)
            hours = delta.total_seconds() / 3600
            detection_rate = round(detection_count / hours, 2) if detection_count else 0
            
            results.append({
                "id": station_id,
                "name": name,
                "url": stream_url,
                "status": status.value if status else "inactive",
                "region": f"{country or 'Unknown'} ({language or 'Unknown'})",
                "detection_count": detection_count or 0,
                "detection_rate": detection_rate,
                "total_play_time": str(timedelta(seconds=int(total_play_time))) if total_play_time else "0:00:00",
                "unique_tracks": unique_tracks or 0,
                "tracks": track_list,
                "unique_artists": unique_artists or 0,
                "artists": artist_list,
                "unique_labels": unique_labels or 0,
                "labels": label_list
            })
        
        return {
            "time_range": time_range,
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "end_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "total_channels": len(results),
            "active_channels": len([r for r in results if r["detection_count"] > 0]),
            "channels": results
        }
        
    except Exception as e:
        logger.error(f"Error getting channel analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting channel analytics: {str(e)}"
        )

@app.get("/api/analytics/overview")
async def get_analytics_overview(
    time_range: str = Query("24h", description="Time range for analytics (e.g., '7d' for 7 days)"),
    db: Session = Depends(get_db)
):
    """Get analytics overview for a specific time range"""
    try:
        # Parse time range
        unit = time_range[-1].lower()
        value = int(time_range[:-1])
        
        if unit == 'd':
            delta = timedelta(days=value)
        elif unit == 'h':
            delta = timedelta(hours=value)
        else:
            raise ValueError(f"Invalid time range format: {time_range}. Use format like '7d' or '24h'")
        
        start_time = datetime.now() - delta
        
        # Get total number of stations and active stations
        total_stations = db.query(func.count(RadioStation.id)).scalar() or 0
        active_stations = db.query(func.count(RadioStation.id))\
            .filter(RadioStation.last_checked >= start_time)\
            .filter(RadioStation.is_active == True)\
            .scalar() or 0
        
        # Get overall detection statistics using a subquery
        detection_subq = (
            db.query(
                func.count(TrackDetection.id).label('total_detections'),
                func.sum(func.strftime('%s', TrackDetection.play_duration)).label('total_play_time'),
                func.count(distinct(Track.id)).label('unique_tracks'),
                func.count(distinct(Track.artist)).label('unique_artists'),
                func.avg(TrackDetection.confidence).label('average_confidence')
            )
            .outerjoin(Track, TrackDetection.track_id == Track.id)
            .filter(TrackDetection.detected_at >= start_time)
            .subquery()
        )
        
        detection_stats = db.query(detection_subq).first()
        
        # Get hourly detection counts using a subquery
        hourly_subq = (
            db.query(
                func.strftime('%Y-%m-%d %H:00:00', TrackDetection.detected_at).label('hour'),
                func.count(TrackDetection.id).label('count')
            )
            .filter(TrackDetection.detected_at >= start_time)
            .group_by(text('hour'))
            .order_by(text('hour'))
            .subquery()
        )
        
        hourly_detections = db.query(hourly_subq).all()
        
        # Get top tracks using a subquery
        tracks_subq = (
            db.query(
                Track.id,
                Track.title,
                Track.artist,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(func.strftime('%s', TrackDetection.play_duration)).label('total_play_time')
            )
            .join(TrackDetection, Track.id == TrackDetection.track_id)
            .filter(TrackDetection.detected_at >= start_time)
            .group_by(Track.id)
            .order_by(func.count(TrackDetection.id).desc())
            .limit(10)
            .subquery()
        )
        
        top_tracks = db.query(tracks_subq).all()
        
        # Get top artists using a subquery
        artists_subq = (
            db.query(
                Track.artist,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(func.strftime('%s', TrackDetection.play_duration)).label('total_play_time')
            )
            .join(TrackDetection, Track.id == TrackDetection.track_id)
            .filter(TrackDetection.detected_at >= start_time)
            .group_by(Track.artist)
            .order_by(func.count(TrackDetection.id).desc())
            .limit(10)
            .subquery()
        )
        
        top_artists = db.query(artists_subq).all()

        # Get top labels using a subquery
        labels_subq = (
            db.query(
                Track.label,
                func.count(TrackDetection.id).label('detection_count')
            )
            .join(TrackDetection, Track.id == TrackDetection.track_id)
            .filter(
                Track.label.isnot(None),
                TrackDetection.detected_at >= start_time
            )
            .group_by(Track.label)
            .order_by(func.count(TrackDetection.id).desc())
            .limit(10)
            .subquery()
        )
        
        top_labels = db.query(labels_subq).all()

        # Get top channels using a subquery
        channels_subq = (
            db.query(
                RadioStation.id,
                RadioStation.name,
                RadioStation.country,
                RadioStation.language,
                func.count(TrackDetection.id).label('detection_count')
            )
            .join(TrackDetection, RadioStation.id == TrackDetection.station_id)
            .filter(TrackDetection.detected_at >= start_time)
            .group_by(RadioStation.id)
            .order_by(func.count(TrackDetection.id).desc())
            .limit(10)
            .subquery()
        )
        
        top_channels = db.query(channels_subq).all()
        
        # Format response
        return {
            "totalChannels": total_stations,
            "activeStations": active_stations,
            "totalPlays": detection_stats.total_detections or 0,
            "totalPlayTime": str(timedelta(seconds=int(detection_stats.total_play_time))) if detection_stats.total_play_time else "00:00:00",
            "playsData": [
                {
                    "hour": hour,
                    "count": count
                }
                for hour, count in hourly_detections
            ],
            "topTracks": [
                {
                    "rank": i + 1,
                    "title": title,
                    "artist": artist,
                    "plays": detection_count or 0,
                    "duration": str(timedelta(seconds=int(total_play_time))) if total_play_time else "00:00:00"
                }
                for i, (id, title, artist, detection_count, total_play_time) in enumerate(top_tracks)
            ],
            "topArtists": [
                {
                    "rank": i + 1,
                    "name": artist,
                    "plays": detection_count or 0
                }
                for i, (artist, detection_count, total_play_time) in enumerate(top_artists)
                if artist is not None
            ],
            "topLabels": [
                {
                    "rank": i + 1,
                    "name": label or "Unknown",
                    "plays": count
                }
                for i, (label, count) in enumerate(top_labels)
            ],
            "topChannels": [
                {
                    "rank": i + 1,
                    "name": name,
                    "country": country or "Unknown",
                    "language": language or "Unknown",
                    "plays": count
                }
                for i, (id, name, country, language, count) in enumerate(top_channels)
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics overview: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting analytics overview: {str(e)}"
        )

@app.post("/api/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password reset email"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "If the email exists, you will receive reset instructions"}
    
    # Generate reset token
    reset_token = create_access_token(
        data={"sub": user.username, "type": "reset"},
        expires_delta=timedelta(minutes=15)
    )
    
    # In a real app, send email here
    # For now, just return the token
    return {
        "message": "Password reset instructions sent",
        "token": reset_token  # In production, this should be sent via email
    }

@app.post("/api/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using token"""
    try:
        # Verify token
        payload = jwt.decode(request.token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username or payload.get("type") != "reset":
            raise HTTPException(status_code=400, detail="Invalid token")
        
        # Get user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update password
        user.password_hash = get_password_hash(request.new_password)
        db.commit()
        
        return {"message": "Password reset successful"}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

@app.post("/api/channels/detect-music")
async def detect_music_all_stations(db: Session = Depends(get_db)):
    """Detect music from all active stations"""
    try:
        # Get all active stations
        stations = db.query(RadioStation).filter(RadioStation.is_active == True).all()
        
        if not stations:
            raise HTTPException(status_code=404, detail="No active stations found")
        
        results = []
        for station in stations:
            try:
                # Analyze stream
                result = await processor.analyze_stream(station.stream_url, station.id)
                if result:
                    results.append({
                        "station_id": station.id,
                        "station_name": station.name,
                        "detection": result
                    })
            except Exception as e:
                logger.error(f"Error detecting music for station {station.name}: {str(e)}")
                continue
        
        return {
            "status": "success",
            "message": f"Analyzed {len(stations)} stations",
            "detections": results
        }
        
    except Exception as e:
        logger.error(f"Error in detect_music_all_stations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8000'))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Configure uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Run the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_config=log_config,
        log_level="debug" if debug else "info"
    )
