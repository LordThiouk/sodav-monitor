from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks, UploadFile, File, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import uvicorn
import json
import asyncio
import logging
import requests
import librosa
import os
import pandas as pd
from pathlib import Path
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from models import Base, RadioStation, Track, TrackDetection, User, Report
from database import SessionLocal, engine, Base
from audio_processor import AudioProcessor
from fingerprint import AudioProcessor as FingerprintProcessor
from radio_manager import RadioManager
from fingerprint_generator import generate_fingerprint
from music_recognition import MusicRecognizer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('DEBUG', 'False').lower() == 'true' else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('music_recognition.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SODAV Media Monitor", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize MusicRecognizer and AudioProcessor
music_recognizer = MusicRecognizer()
processor = AudioProcessor(db_session=SessionLocal(), music_recognizer=music_recognizer)

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
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "connections": len(active_connections)
    }

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
    stations = db.query(RadioStation).all()
    return [
        {
            "id": station.id,
            "name": station.name,
            "stream_url": station.stream_url,
            "country": station.country,
            "language": station.language,
            "is_active": station.is_active,
            "last_checked": station.last_checked.isoformat()
        }
        for station in stations
    ]

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
    end_date: Optional[datetime] = None
):
    """Get track detections with optional filters."""
    db = SessionLocal()
    query = db.query(TrackDetection)
    
    if station_id:
        query = query.filter(TrackDetection.station_id == station_id)
    if start_date:
        query = query.filter(TrackDetection.detected_at >= start_date)
    if end_date:
        query = query.filter(TrackDetection.detected_at <= end_date)
    
    detections = query.order_by(TrackDetection.detected_at.desc()).all()
    db.close()
    
    return {
        "detections": [
            DetectionResponse(
                station_name=d.station.name,
                track_title=d.track.title,
                artist=d.track.artist,
                detected_at=d.detected_at,
                confidence=d.confidence
            ) for d in detections
        ]
    }

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
    try:
        await websocket.accept()
        active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(active_connections)}")

        try:
            # Send initial data
            await websocket.send_json({
                "type": "stats_update",
                "timestamp": datetime.now().isoformat(),
                "active_streams": 1,
                "total_streams": 1,
                "total_tracks": 0
            })

            # Keep connection alive
            while True:
                try:
                    # Wait for client messages
                    data = await websocket.receive_text()
                    # Send pong response
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                except WebSocketDisconnect:
                    break

        except Exception as e:
            logger.error(f"Error in WebSocket loop: {e}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total: {len(active_connections)}")

def test_music_detection():
    stream_url = "http://listen.senemultimedia.net:8090/stream"
    try:
        response = requests.get(stream_url, stream=True)
        audio_data = response.content  # Get the audio data from the stream
        detection_result = processor.detect_track(audio_data)  # Use the processor to detect music
        print(detection_result)
    except Exception as e:
        print(f"Error detecting music: {e}")

# test_music_detection()  # Call the function to test music detection

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
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user.last_login = datetime.now()
    db.commit()
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# Report management endpoints
@app.post("/api/reports", response_model=ReportResponse)
async def create_report(
    report_request: ReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new report"""
    report = Report(
        user_id=current_user.id,
        type=report_request.type,
        format=report_request.format,
        start_date=report_request.start_date,
        end_date=report_request.end_date,
        filters=report_request.filters,
        status=ReportStatus.PENDING
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
    
    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Report not ready for download")
    
    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        report.file_path,
        filename=f"report_{report.id}_{report.type}_{report.created_at.date()}.{report.format}"
    )

async def generate_report(report_id: int, db: Session):
    """Background task to generate report"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        return
    
    try:
        report.status = ReportStatus.GENERATING
        db.commit()
        
        # Get detection data for the report period
        detections = db.query(TrackDetection).filter(
            TrackDetection.detected_at >= report.start_date,
            TrackDetection.detected_at <= report.end_date
        ).all()
        
        # Create report directory if it doesn't exist
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Generate report based on format
        if report.format == "csv":
            file_path = reports_dir / f"report_{report.id}.csv"
            df = pd.DataFrame([{
                'station': d.station.name,
                'track': d.track.title,
                'artist': d.track.artist,
                'detected_at': d.detected_at,
                'duration': d.play_duration,
                'confidence': d.confidence
            } for d in detections])
            df.to_csv(file_path, index=False)
        elif report.format == "xlsx":
            file_path = reports_dir / f"report_{report.id}.xlsx"
            df = pd.DataFrame([{
                'station': d.station.name,
                'track': d.track.title,
                'artist': d.track.artist,
                'detected_at': d.detected_at,
                'duration': d.play_duration,
                'confidence': d.confidence
            } for d in detections])
            df.to_excel(file_path, index=False)
        
        report.file_path = str(file_path)
        report.status = ReportStatus.COMPLETED
        report.completed_at = datetime.now()
        
    except Exception as e:
        report.status = ReportStatus.FAILED
        report.error_message = str(e)
        logger.error(f"Error generating report {report_id}: {e}")
    
    finally:
        db.commit()

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
