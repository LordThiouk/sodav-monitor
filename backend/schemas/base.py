"""Base schemas for the SODAV Monitor."""

from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Union
from datetime import datetime, timedelta

class StationBase(BaseModel):
    name: str
    stream_url: str
    region: Optional[str] = None
    language: Optional[str] = None
    type: Optional[str] = "radio"

class StationCreate(StationBase):
    pass

class StationUpdate(StationBase):
    status: Optional[str] = None
    is_active: Optional[bool] = None

class StationResponse(StationBase):
    id: int
    status: str
    is_active: bool
    last_checked: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TrackBase(BaseModel):
    title: str
    artist: str
    isrc: Optional[str] = None
    label: Optional[str] = None
    fingerprint: Optional[str] = None

class TrackResponse(TrackBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StreamBase(BaseModel):
    name: str
    type: str
    status: str
    region: str
    language: str
    stream_url: str

class DetectionCreate(BaseModel):
    track_id: int
    station_id: int
    detected_at: Optional[datetime] = None
    confidence: float
    play_duration: Optional[Union[int, timedelta]] = None
    fingerprint: Optional[str] = None
    audio_hash: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            timedelta: lambda v: int(v.total_seconds())
        }

class DetectionResponse(BaseModel):
    id: int
    track: TrackResponse
    station: StationResponse
    detected_at: datetime
    confidence: float
    play_duration: Optional[timedelta] = None

    class Config:
        from_attributes = True

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
        from_attributes = True

class ReportStatusResponse(BaseModel):
    id: int
    title: str
    status: str
    created_at: datetime
    updated_at: datetime

class SubscriptionBase(BaseModel):
    name: str
    email: EmailStr
    frequency: str
    report_type: str
    format: str
    filters: Optional[Dict] = None
    include_graphs: Optional[bool] = True
    language: Optional[str] = "fr"

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    frequency: Optional[str] = None
    filters: Optional[Dict] = None
    include_graphs: Optional[bool] = None
    language: Optional[str] = None

class SubscriptionResponse(SubscriptionBase):
    id: int
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_id: int

    class Config:
        from_attributes = True 