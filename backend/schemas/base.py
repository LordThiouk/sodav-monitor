from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Union
from datetime import datetime

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