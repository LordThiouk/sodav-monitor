from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Union
from datetime import datetime

class TrackBase(BaseModel):
    title: str
    artist: str
    duration: int
    confidence: float

class TrackResponse(TrackBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class StreamBase(BaseModel):
    name: str
    type: str
    status: str
    region: str
    language: str
    stream_url: str

class DetectionBase(BaseModel):
    station_name: str
    track_title: str
    artist: str
    confidence: float

class DetectionCreate(DetectionBase):
    detected_at: Optional[datetime] = None

class DetectionResponse(DetectionBase):
    id: int
    detected_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

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

class StationBase(BaseModel):
    name: str
    stream_url: str
    country: Optional[str] = None
    region: Optional[str] = None
    language: Optional[str] = None
    type: Optional[str] = "radio"
    status: Optional[str] = "inactive"
    is_active: Optional[bool] = False

class StationCreate(StationBase):
    pass

class StationUpdate(BaseModel):
    name: Optional[str] = None
    stream_url: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    language: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None

class StationResponse(StationBase):
    id: int
    last_check: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StationStatusResponse(BaseModel):
    id: int
    name: str
    status: str
    is_active: bool
    last_checked: Optional[datetime] = None

class ReportBase(BaseModel):
    title: str
    type: str
    format: str
    period_start: datetime
    period_end: datetime
    filters: Optional[Dict[str, str]] = None

class ReportCreate(ReportBase):
    pass

class ReportUpdate(ReportBase):
    status: Optional[str] = None
    file_path: Optional[str] = None
    error_message: Optional[str] = None

class ReportResponse(ReportBase):
    id: int
    status: str
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class ReportStatusResponse(BaseModel):
    id: int
    title: str
    status: str
    created_at: datetime
    updated_at: datetime 