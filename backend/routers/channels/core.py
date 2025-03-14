"""Core channels functionality for SODAV Monitor.

This module handles basic CRUD operations for radio stations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.models.database import get_db
from backend.models.models import RadioStation, StationStatus
from backend.schemas.base import StationCreate, StationResponse, StationUpdate
from backend.utils.auth import get_current_user
from backend.utils.radio import fetch_and_save_senegal_stations

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    tags=["channels"],
    dependencies=[Depends(get_current_user)],  # Require authentication for all endpoints
)


@router.get("/", response_model=List[StationResponse])
async def get_stations(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    country: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a list of radio stations with optional filtering."""
    query = db.query(RadioStation)

    # Apply filters if provided
    if status:
        query = query.filter(RadioStation.status == status)

    if country:
        query = query.filter(RadioStation.country == country)

    # Apply pagination
    stations = query.order_by(RadioStation.name).offset(skip).limit(limit).all()

    return stations


@router.post("/", response_model=StationResponse)
async def create_station(
    station: StationCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """Create a new radio station."""
    # Check if a station with the same name already exists
    existing_station = db.query(RadioStation).filter(RadioStation.name == station.name).first()
    if existing_station:
        raise HTTPException(status_code=400, detail="Station with this name already exists")

    # Create a new station record
    db_station = RadioStation(
        name=station.name,
        stream_url=station.stream_url,
        location=station.location,
        description=station.description,
        logo_url=station.logo_url,
        website=station.website,
        status=StationStatus.INACTIVE,
        created_by=current_user.id,
    )

    db.add(db_station)
    db.commit()
    db.refresh(db_station)

    return db_station


@router.get("/{station_id}", response_model=StationResponse)
async def get_station(
    station_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """Get a specific radio station by ID."""
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


@router.put("/{station_id}", response_model=StationResponse)
async def update_station(
    station_id: int,
    station_update: StationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update a specific radio station."""
    # Get the station from the database
    db_station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not db_station:
        raise HTTPException(status_code=404, detail="Station not found")

    # Check if the name is being changed and if it conflicts with an existing station
    if station_update.name and station_update.name != db_station.name:
        existing_station = (
            db.query(RadioStation).filter(RadioStation.name == station_update.name).first()
        )
        if existing_station:
            raise HTTPException(status_code=400, detail="Station with this name already exists")

    # Update the station fields
    update_data = station_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_station, key, value)

    db_station.updated_at = datetime.utcnow()
    db_station.updated_by = current_user.id

    db.commit()
    db.refresh(db_station)

    return db_station


@router.delete("/{station_id}")
async def delete_station(
    station_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """Delete a specific radio station."""
    # Get the station from the database
    db_station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not db_station:
        raise HTTPException(status_code=404, detail="Station not found")

    # Delete the station
    db.delete(db_station)
    db.commit()

    return {"message": "Station deleted successfully"}


@router.post("/fetch-senegal-stations")
async def fetch_senegal_stations(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """Manually fetch Senegalese radio stations from Radio Browser API."""
    try:
        logger.info("Manually fetching Senegalese radio stations...")
        stations_count = await fetch_and_save_senegal_stations(db)

        return {
            "status": "success",
            "message": f"Successfully processed {stations_count} Senegalese radio stations",
            "count": stations_count,
        }
    except Exception as e:
        logger.error(f"Error fetching Senegalese radio stations: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch Senegalese radio stations: {str(e)}"
        )


@router.get("/senegal-stations/health")
async def senegal_stations_health(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """Get health information about Senegalese radio stations."""
    try:
        # Check if radio_stations table exists
        inspector = inspect(db.bind)
        if not inspector.has_table("radio_stations"):
            return {
                "status": "initializing",
                "message": "Radio stations table is not yet created",
                "total_stations": 0,
                "active_stations": 0,
                "last_updated": None,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Count total Senegalese stations
        total_count = db.query(RadioStation).filter(RadioStation.country == "Senegal").count()

        # Count active Senegalese stations
        active_count = (
            db.query(RadioStation)
            .filter(RadioStation.country == "Senegal", RadioStation.is_active == True)
            .count()
        )

        # Get last updated station
        last_updated = (
            db.query(RadioStation)
            .filter(RadioStation.country == "Senegal")
            .order_by(RadioStation.updated_at.desc())
            .first()
        )

        return {
            "status": "success",
            "total_stations": total_count,
            "active_stations": active_count,
            "last_updated": last_updated.updated_at.isoformat() if last_updated else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting Senegalese stations health: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "total_stations": 0,
            "active_stations": 0,
            "last_updated": None,
            "timestamp": datetime.utcnow().isoformat(),
        }
