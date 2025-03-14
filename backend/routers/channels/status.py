"""Station status functionality for SODAV Monitor.

This module handles operations related to radio station status.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.models.database import get_db
from backend.models.models import RadioStation, StationStatus, StationStatusHistory
from backend.schemas.base import StationStatusResponse, StationStatusUpdate
from backend.utils.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    tags=["channels"],
    dependencies=[Depends(get_current_user)],  # Require authentication for all endpoints
)


@router.get("/{station_id}/status", response_model=StationStatusResponse)
async def get_station_status(
    station_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """Get the current status of a specific radio station."""
    # Get the station from the database
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    # Get the latest status history entry
    latest_status = (
        db.query(StationStatusHistory)
        .filter(StationStatusHistory.station_id == station_id)
        .order_by(StationStatusHistory.created_at.desc())
        .first()
    )

    return {
        "id": station.id,
        "name": station.name,
        "status": station.status,
        "last_check": station.last_check,
        "last_successful_check": station.last_successful_check,
        "error_count": station.error_count,
        "status_message": latest_status.message if latest_status else None,
        "updated_at": station.updated_at,
    }


@router.put("/{station_id}/status", response_model=StationStatusResponse)
async def update_station_status(
    station_id: int,
    status_update: StationStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update the status of a specific radio station."""
    # Get the station from the database
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    # Update the station status
    old_status = station.status
    station.status = status_update.status
    station.updated_at = datetime.utcnow()
    station.updated_by = current_user.id

    # Create a status history entry
    status_history = StationStatusHistory(
        station_id=station_id,
        old_status=old_status,
        new_status=status_update.status,
        message=status_update.message,
        created_by=current_user.id,
    )

    db.add(status_history)
    db.commit()
    db.refresh(station)

    return {
        "id": station.id,
        "name": station.name,
        "status": station.status,
        "last_check": station.last_check,
        "last_successful_check": station.last_successful_check,
        "error_count": station.error_count,
        "status_message": status_update.message,
        "updated_at": station.updated_at,
    }


@router.get("/status/summary", response_model=Dict[str, int])
async def get_status_summary(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get a summary of station statuses."""
    # Count stations by status
    active_count = (
        db.query(RadioStation).filter(RadioStation.status == StationStatus.ACTIVE).count()
    )
    inactive_count = (
        db.query(RadioStation).filter(RadioStation.status == StationStatus.INACTIVE).count()
    )
    error_count = db.query(RadioStation).filter(RadioStation.status == StationStatus.ERROR).count()
    maintenance_count = (
        db.query(RadioStation).filter(RadioStation.status == StationStatus.MAINTENANCE).count()
    )

    return {
        "active": active_count,
        "inactive": inactive_count,
        "error": error_count,
        "maintenance": maintenance_count,
        "total": active_count + inactive_count + error_count + maintenance_count,
    }


@router.get("/status/history/{station_id}", response_model=List[Dict])
async def get_status_history(
    station_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the status history for a specific radio station."""
    # Get the station from the database
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    # Get the status history
    history = (
        db.query(StationStatusHistory)
        .filter(StationStatusHistory.station_id == station_id)
        .order_by(StationStatusHistory.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": h.id,
            "old_status": h.old_status,
            "new_status": h.new_status,
            "message": h.message,
            "created_at": h.created_at,
            "created_by": h.created_by,
        }
        for h in history
    ]
