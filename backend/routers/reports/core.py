"""Core reports functionality for SODAV Monitor.

This module handles basic CRUD operations for reports.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, distinct, case, and_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
import os
import logging
import json

from backend.models.database import get_db
from backend.models.models import Report, ReportSubscription, User, TrackDetection, Track, RadioStation, ReportStatus, Artist, ReportType, ReportFormat
from backend.utils.auth import get_current_user
from backend.schemas.base import ReportCreate, ReportResponse, ReportStatusResponse
from backend.utils.file_manager import get_report_path

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_user)]  # Require authentication for all endpoints
)

@router.get("/", response_model=List[ReportResponse])
async def get_reports(
    skip: int = 0,
    limit: int = 100,
    report_type: Optional[ReportType] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a list of reports with optional filtering."""
    query = db.query(Report)
    
    # Apply filters if provided
    if report_type:
        query = query.filter(Report.report_type == report_type)
    if start_date:
        query = query.filter(Report.created_at >= start_date)
    if end_date:
        query = query.filter(Report.created_at <= end_date)
    
    # Apply pagination
    reports = query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
    
    return reports

@router.post("/", response_model=ReportResponse)
async def create_report(
    report: ReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new report and generate it in the background."""
    # Create a new report record
    db_report = Report(
        report_type=report.report_type,
        format=report.format,
        start_date=report.start_date,
        end_date=report.end_date,
        status=ReportStatus.PENDING,
        created_by=current_user.id,
        filters=report.filters,
        include_graphs=report.include_graphs,
        language=report.language
    )
    
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    # Generate the report in the background
    from .generation import generate_report
    background_tasks.add_task(generate_report, db_report.id)
    
    return db_report

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific report by ID."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.get("/{report_id}/status", response_model=ReportStatusResponse)
async def get_report_status(
    report_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get the status of a specific report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "id": report.id,
        "status": report.status,
        "progress": report.progress,
        "message": report.status_message,
        "updated_at": report.updated_at
    }

@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Download a specific report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Report is not ready for download")
    
    if not report.file_path:
        raise HTTPException(status_code=400, detail="Report file not found")
    
    file_path = get_report_path(report.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    # Determine content type based on format
    content_type = "application/octet-stream"
    if report.format == ReportFormat.PDF:
        content_type = "application/pdf"
    elif report.format == ReportFormat.XLSX:
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif report.format == ReportFormat.CSV:
        content_type = "text/csv"
    
    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type=content_type
    )

@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a specific report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Delete the file if it exists
    if report.file_path:
        file_path = get_report_path(report.file_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error deleting report file: {str(e)}")
    
    # Delete the report from the database
    db.delete(report)
    db.commit()
    
    return {"message": "Report deleted successfully"}

@router.put("/{report_id}/status", response_model=ReportResponse)
async def update_report_status(
    report_id: int,
    update_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update the status of a specific report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Update the report status
    if "status" in update_data:
        report.status = update_data["status"]
    if "progress" in update_data:
        report.progress = update_data["progress"]
    if "status_message" in update_data:
        report.status_message = update_data["status_message"]
    if "file_path" in update_data:
        report.file_path = update_data["file_path"]
    
    report.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(report)
    
    return report