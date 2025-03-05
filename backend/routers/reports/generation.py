"""Report generation functionality for SODAV Monitor.

This module handles the generation of various types of reports.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from backend.models.database import get_db
from backend.models.models import (
    Report, ReportSubscription, User, TrackDetection, Track, 
    RadioStation, ReportStatus, Artist, ReportType, ReportFormat
)
from backend.utils.auth import get_current_user
from backend.utils.file_manager import get_report_path
from backend.core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Create reports directory if it doesn't exist
REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Create router
router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_user)]  # Require authentication for all endpoints
)

@router.post("/generate/daily")
async def generate_daily_report(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    date: Optional[datetime] = None
):
    """Generate a daily report for a specific date."""
    if not date:
        date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Set the date range for the report
    start_date = date
    end_date = date + timedelta(days=1)
    
    # Create a new report record
    db_report = Report(
        report_type=ReportType.DAILY,
        format=ReportFormat.PDF,
        start_date=start_date,
        end_date=end_date,
        status=ReportStatus.PENDING,
        created_by=current_user.id,
        include_graphs=True,
        language="fr"
    )
    
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    # Generate the report in the background
    background_tasks.add_task(generate_report, db_report.id)
    
    return {
        "message": "Daily report generation started",
        "report_id": db_report.id,
        "date": date.strftime("%Y-%m-%d")
    }

@router.post("/generate/monthly")
async def generate_monthly_report(
    background_tasks: BackgroundTasks,
    year: int = Query(..., ge=2000, le=datetime.utcnow().year),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Generate a monthly report for a specific year and month."""
    # Set the date range for the report
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # Create a new report record
    db_report = Report(
        report_type=ReportType.MONTHLY,
        format=ReportFormat.PDF,
        start_date=start_date,
        end_date=end_date,
        status=ReportStatus.PENDING,
        created_by=current_user.id,
        include_graphs=True,
        language="fr"
    )
    
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    # Generate the report in the background
    background_tasks.add_task(generate_report, db_report.id)
    
    return {
        "message": "Monthly report generation started",
        "report_id": db_report.id,
        "year": year,
        "month": month
    }

@router.post("/generate", response_model=Dict)
async def generate_custom_report(
    report_type: str = Query("daily", enum=["daily", "weekly", "monthly", "comprehensive"]),
    report_format: str = Query("pdf", enum=["pdf", "csv", "json", "xlsx"]),
    date: Optional[str] = None,
    include_graphs: bool = True,
    language: str = "fr",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Generate a custom report with specified parameters."""
    # Parse the date if provided
    start_date = None
    end_date = None
    
    if date:
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            if report_type == "daily":
                start_date = parsed_date
                end_date = parsed_date + timedelta(days=1)
            elif report_type == "weekly":
                # Start from Monday of the week
                start_date = parsed_date - timedelta(days=parsed_date.weekday())
                end_date = start_date + timedelta(days=7)
            elif report_type == "monthly":
                # Start from the first day of the month
                start_date = datetime(parsed_date.year, parsed_date.month, 1)
                if parsed_date.month == 12:
                    end_date = datetime(parsed_date.year + 1, 1, 1)
                else:
                    end_date = datetime(parsed_date.year, parsed_date.month + 1, 1)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        # Use current date
        now = datetime.utcnow()
        if report_type == "daily":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif report_type == "weekly":
            # Start from Monday of the current week
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=7)
        elif report_type == "monthly":
            # Start from the first day of the current month
            start_date = datetime(now.year, now.month, 1)
            if now.month == 12:
                end_date = datetime(now.year + 1, 1, 1)
            else:
                end_date = datetime(now.year, now.month + 1, 1)
        elif report_type == "comprehensive":
            # Last 30 days
            end_date = now
            start_date = end_date - timedelta(days=30)
    
    # Map the report type to the enum
    report_type_enum = None
    if report_type == "daily":
        report_type_enum = ReportType.DAILY
    elif report_type == "weekly":
        report_type_enum = ReportType.WEEKLY
    elif report_type == "monthly":
        report_type_enum = ReportType.MONTHLY
    elif report_type == "comprehensive":
        report_type_enum = ReportType.COMPREHENSIVE
    
    # Map the report format to the enum
    report_format_enum = None
    if report_format == "pdf":
        report_format_enum = ReportFormat.PDF
    elif report_format == "csv":
        report_format_enum = ReportFormat.CSV
    elif report_format == "json":
        report_format_enum = ReportFormat.JSON
    elif report_format == "xlsx":
        report_format_enum = ReportFormat.XLSX
    
    # Create a new report record
    db_report = Report(
        report_type=report_type_enum,
        format=report_format_enum,
        start_date=start_date,
        end_date=end_date,
        status=ReportStatus.PENDING,
        created_by=current_user.id,
        include_graphs=include_graphs,
        language=language
    )
    
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    # Generate the report in the background
    background_tasks = BackgroundTasks()
    background_tasks.add_task(generate_report, db_report.id)
    
    return {
        "message": f"{report_type.capitalize()} report generation started",
        "report_id": db_report.id,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "format": report_format
    }

@router.post("/send/{report_id}")
async def send_report_by_email(
    report_id: int,
    email: EmailStr,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Send a specific report by email."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Report is not ready for sending")
    
    if not report.file_path:
        raise HTTPException(status_code=400, detail="Report file not found")
    
    file_path = get_report_path(report.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    try:
        # Send the email with the report
        send_email_with_report(email, file_path, report.report_type, report.language)
        
        return {"message": f"Report sent to {email}"}
    except Exception as e:
        logger.error(f"Error sending report by email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")

# Helper functions

async def generate_report(report_id: int):
    """Generate a report based on its ID."""
    # This function is called in the background
    settings = get_settings()
    
    # Create a new database session
    from backend.models.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Get the report from the database
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            logger.error(f"Report {report_id} not found")
            return
        
        # Update the report status
        report.status = ReportStatus.PROCESSING
        report.progress = 0
        report.status_message = "Starting report generation"
        db.commit()
        
        # Generate the report based on its type
        try:
            # Get the data for the report
            report.progress = 10
            report.status_message = "Fetching data"
            db.commit()
            
            # Process the data based on report type
            if report.report_type == ReportType.DAILY:
                data = get_detection_data(report.start_date, report.end_date, db)
                summary = get_summary_stats(db, "daily", report.start_date, report.end_date)
            elif report.report_type == ReportType.WEEKLY:
                data = get_detection_data(report.start_date, report.end_date, db)
                summary = get_summary_stats(db, "weekly", report.start_date, report.end_date)
            elif report.report_type == ReportType.MONTHLY:
                data = get_detection_data(report.start_date, report.end_date, db)
                summary = get_summary_stats(db, "monthly", report.start_date, report.end_date)
            elif report.report_type == ReportType.COMPREHENSIVE:
                data = get_detection_data(report.start_date, report.end_date, db)
                summary = get_summary_stats(db, "comprehensive", report.start_date, report.end_date)
            else:
                logger.error(f"Unsupported report type: {report.report_type}")
                report.status = ReportStatus.FAILED
                report.status_message = f"Unsupported report type: {report.report_type}"
                db.commit()
                return
            
            report.progress = 50
            report.status_message = "Processing data"
            db.commit()
            
            # Generate the report file
            from backend.reports.generator import ReportGenerator
            generator = ReportGenerator(db)
            
            # Generate the report based on format
            if report.format == ReportFormat.PDF:
                file_path = generator.generate_pdf_report(data, summary, report.report_type, report.start_date, report.end_date, report.include_graphs, report.language)
            elif report.format == ReportFormat.XLSX:
                file_path = generator.generate_excel_report(data, summary, report.report_type, report.start_date, report.end_date)
            elif report.format == ReportFormat.CSV:
                file_path = generator.generate_csv_report(data, report.report_type, report.start_date, report.end_date)
            elif report.format == ReportFormat.JSON:
                file_path = generator.generate_json_report(data, summary, report.report_type, report.start_date, report.end_date)
            else:
                logger.error(f"Unsupported report format: {report.format}")
                report.status = ReportStatus.FAILED
                report.status_message = f"Unsupported report format: {report.format}"
                db.commit()
                return
            
            report.progress = 90
            report.status_message = "Finalizing report"
            db.commit()
            
            # Update the report with the file path
            report.file_path = file_path
            report.status = ReportStatus.COMPLETED
            report.progress = 100
            report.status_message = "Report generated successfully"
            report.completed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Report {report_id} generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating report {report_id}: {str(e)}")
            report.status = ReportStatus.FAILED
            report.status_message = f"Error generating report: {str(e)}"
            db.commit()
            
    except Exception as e:
        logger.error(f"Error in generate_report: {str(e)}")
    finally:
        db.close()

def send_email_with_report(email: str, report_path: str, report_type: str, language: str = "fr"):
    """Send an email with the report attached."""
    settings = get_settings()
    
    # Get email settings from configuration
    smtp_server = settings.SMTP_SERVER
    smtp_port = settings.SMTP_PORT
    smtp_username = settings.SMTP_USERNAME
    smtp_password = settings.SMTP_PASSWORD
    sender_email = settings.SENDER_EMAIL
    
    if not all([smtp_server, smtp_port, smtp_username, smtp_password, sender_email]):
        logger.error("Email settings not configured")
        raise ValueError("Email settings not configured")
    
    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    
    # Set the subject and body based on language and report type
    if language == "fr":
        if report_type == ReportType.DAILY:
            msg['Subject'] = "Rapport quotidien SODAV Monitor"
            body = "Veuillez trouver ci-joint le rapport quotidien de SODAV Monitor."
        elif report_type == ReportType.WEEKLY:
            msg['Subject'] = "Rapport hebdomadaire SODAV Monitor"
            body = "Veuillez trouver ci-joint le rapport hebdomadaire de SODAV Monitor."
        elif report_type == ReportType.MONTHLY:
            msg['Subject'] = "Rapport mensuel SODAV Monitor"
            body = "Veuillez trouver ci-joint le rapport mensuel de SODAV Monitor."
        else:
            msg['Subject'] = "Rapport SODAV Monitor"
            body = "Veuillez trouver ci-joint le rapport de SODAV Monitor."
    else:
        if report_type == ReportType.DAILY:
            msg['Subject'] = "SODAV Monitor Daily Report"
            body = "Please find attached the daily report from SODAV Monitor."
        elif report_type == ReportType.WEEKLY:
            msg['Subject'] = "SODAV Monitor Weekly Report"
            body = "Please find attached the weekly report from SODAV Monitor."
        elif report_type == ReportType.MONTHLY:
            msg['Subject'] = "SODAV Monitor Monthly Report"
            body = "Please find attached the monthly report from SODAV Monitor."
        else:
            msg['Subject'] = "SODAV Monitor Report"
            body = "Please find attached the report from SODAV Monitor."
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach the report
    with open(report_path, 'rb') as f:
        attachment = MIMEApplication(f.read(), _subtype=os.path.splitext(report_path)[1][1:])
        attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(report_path))
        msg.attach(attachment)
    
    # Send the email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"Email sent to {email}")
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise

def get_detection_data(start_date: datetime, end_date: datetime, db: Session) -> pd.DataFrame:
    """Get detection data for a specific date range."""
    # Query the database for detections in the date range
    detections = db.query(
        TrackDetection.id,
        TrackDetection.detected_at,
        TrackDetection.play_duration,
        TrackDetection.confidence,
        Track.title.label("track_title"),
        Track.isrc.label("track_isrc"),
        Artist.name.label("artist_name"),
        RadioStation.name.label("station_name")
    ).join(
        Track, TrackDetection.track_id == Track.id
    ).join(
        Artist, Track.artist_id == Artist.id
    ).join(
        RadioStation, TrackDetection.station_id == RadioStation.id
    ).filter(
        TrackDetection.detected_at.between(start_date, end_date)
    ).all()
    
    # Convert to DataFrame
    df = pd.DataFrame([
        {
            "id": d.id,
            "detected_at": d.detected_at,
            "play_duration": d.play_duration.total_seconds() if d.play_duration else 0,
            "confidence": d.confidence,
            "track_title": d.track_title,
            "track_isrc": d.track_isrc,
            "artist_name": d.artist_name,
            "station_name": d.station_name
        }
        for d in detections
    ])
    
    return df

def get_summary_stats(db: Session, report_type: str, start_date: datetime, end_date: datetime) -> Dict:
    """Get summary statistics for a specific date range."""
    # Get total detections
    total_detections = db.query(func.count(TrackDetection.id)).filter(
        TrackDetection.detected_at.between(start_date, end_date)
    ).scalar()
    
    # Get total play time
    total_play_time = db.query(func.sum(TrackDetection.play_duration)).filter(
        TrackDetection.detected_at.between(start_date, end_date)
    ).scalar()
    
    # Get unique tracks
    unique_tracks = db.query(func.count(distinct(TrackDetection.track_id))).filter(
        TrackDetection.detected_at.between(start_date, end_date)
    ).scalar()
    
    # Get unique artists
    unique_artists = db.query(func.count(distinct(Artist.id))).join(
        Track, Track.artist_id == Artist.id
    ).join(
        TrackDetection, TrackDetection.track_id == Track.id
    ).filter(
        TrackDetection.detected_at.between(start_date, end_date)
    ).scalar()
    
    # Get unique stations
    unique_stations = db.query(func.count(distinct(TrackDetection.station_id))).filter(
        TrackDetection.detected_at.between(start_date, end_date)
    ).scalar()
    
    return {
        "total_detections": total_detections or 0,
        "total_play_time": total_play_time.total_seconds() if total_play_time else 0,
        "unique_tracks": unique_tracks or 0,
        "unique_artists": unique_artists or 0,
        "unique_stations": unique_stations or 0,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "report_type": report_type
    } 