"""Base schemas for the SODAV Monitor."""

from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator, model_serializer
from typing import List, Optional, Dict, Union, Any
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

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)
    
    @model_validator(mode='before')
    @classmethod
    def validate_artist(cls, data):
        if isinstance(data, dict) and 'artist' in data and hasattr(data['artist'], 'name'):
            # Si artist est un objet avec un attribut name, utiliser le nom
            data['artist'] = data['artist'].name
        return data

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

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        data = self.model_dump()
        # Handle timedelta serialization
        if self.play_duration and isinstance(self.play_duration, timedelta):
            data["play_duration"] = self.play_duration.total_seconds()
        return data

class DetectionResponse(BaseModel):
    id: int
    track: TrackResponse
    station: StationResponse
    detected_at: datetime
    confidence: float
    play_duration: Optional[timedelta] = None

    model_config = ConfigDict(from_attributes=True)

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
    last_check: Optional[datetime] = None
    last_successful_check: Optional[datetime] = None
    error_count: int = 0
    status_message: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class StationStatusUpdate(BaseModel):
    status: str
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ReportBase(BaseModel):
    title: str
    type: str
    format: str
    period_start: datetime
    period_end: datetime
    filters: Optional[Dict[str, str]] = None

class ReportCreate(ReportBase):
    report_type: str
    parameters: Optional[Dict[str, Any]] = None

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
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)

class DetectionsResponse(BaseModel):
    """Response model for a list of detections with pagination."""
    total: int
    items: List[Dict[str, Any]]
    station: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True) 