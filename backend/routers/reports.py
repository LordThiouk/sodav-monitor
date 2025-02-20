from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, case, and_
from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
import os
import logging
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db, SessionLocal
from models import Report, ReportSubscription, User, TrackDetection, Track, RadioStation, ReportStatus, Artist
from utils.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Create reports directory if it doesn't exist
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

router = APIRouter(
    tags=["reports"],
    dependencies=[Depends(get_current_user)]  # Require authentication for all endpoints
)

class ReportCreate(BaseModel):
    type: str  # 'detection', 'analytics', 'summary', 'artist', 'track', 'station'
    format: str = "csv"  # 'csv', 'xlsx', 'json'
    start_date: datetime
    end_date: datetime
    filters: Optional[Dict] = None

class SubscriptionCreate(BaseModel):
    name: str
    frequency: str
    type: str
    recipients: List[EmailStr]

class ReportResponse(BaseModel):
    id: str
    title: str
    type: str
    format: str
    generatedAt: str
    status: str
    progress: Optional[float] = None
    downloadUrl: Optional[str] = None
    user: Optional[dict] = None

class SubscriptionResponse(BaseModel):
    id: str
    name: str
    frequency: str
    type: str
    nextDelivery: str
    recipients: List[str]
    user: Optional[dict] = None

@router.get("/", response_model=List[ReportResponse])
async def get_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all reports for the current user"""
    try:
        reports = db.query(Report).filter(
            Report.user_id == current_user.id
        ).order_by(Report.created_at.desc()).all()
        
        return [
            ReportResponse(
                id=str(report.id),
                title=f"{report.type.capitalize()} Report",
                type=report.type,
                format=report.format,
                generatedAt=report.created_at.isoformat(),
                status=report.status,
                progress=report.progress,
                downloadUrl=f"/api/reports/{report.id}/download" if report.status == "completed" else None,
                user={
                    'id': current_user.id,
                    'username': current_user.username,
                    'email': current_user.email
                }
            )
            for report in reports
        ]
    except Exception as e:
        logger.error(f"Error getting reports: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=ReportResponse)
async def create_report(
    report: ReportCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new report"""
    try:
        # Validate report type
        valid_types = ["detection", "analytics", "summary", "artist", "track", "station"]
        if report.type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid report type. Must be one of: {', '.join(valid_types)}"
            )

        # Validate format
        valid_formats = ["csv", "xlsx", "json"]
        if report.format not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}"
            )

        # Create new report
        new_report = Report(
            type=report.type,
            format=report.format,
            start_date=report.start_date,
            end_date=report.end_date,
            status="pending",
            progress=0.0,
            user_id=current_user.id,
            created_at=datetime.now(),
            filters=report.filters
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)

        # Start report generation in background
        background_tasks.add_task(generate_report, new_report.id)

        return ReportResponse(
            id=str(new_report.id),
            title=f"{new_report.type.capitalize()} Report",
            type=new_report.type,
            format=new_report.format,
            generatedAt=new_report.created_at.isoformat(),
            status=new_report.status,
            progress=new_report.progress,
            user={
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating report: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/subscriptions", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all report subscriptions for the current user"""
    try:
        subscriptions = db.query(ReportSubscription).filter(ReportSubscription.user_id == current_user.id).all()
        return [
            SubscriptionResponse(
                id=str(sub.id),
                name=sub.name,
                frequency=sub.frequency,
                type=sub.type,
                nextDelivery=sub.next_delivery.isoformat(),
                recipients=sub.recipients,
                user={
                    'id': current_user.id,
                    'username': current_user.username,
                    'email': current_user.email
                }
            )
            for sub in subscriptions
        ]
    except Exception as e:
        logger.error(f"Error getting subscriptions: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving subscriptions")

@router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    subscription: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new report subscription"""
    try:
        # Validate user exists
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Calculate next delivery based on frequency
        now = datetime.now()
        if subscription.frequency == "daily":
            next_delivery = now + timedelta(days=1)
        elif subscription.frequency == "weekly":
            next_delivery = now + timedelta(weeks=1)
        else:  # monthly
            next_delivery = now + timedelta(days=30)

        new_subscription = ReportSubscription(
            name=subscription.name,
            frequency=subscription.frequency,
            type=subscription.type,
            recipients=subscription.recipients,
            next_delivery=next_delivery,
            user_id=current_user.id,
            created_at=now
        )
        db.add(new_subscription)
        db.commit()
        db.refresh(new_subscription)

        return SubscriptionResponse(
            id=str(new_subscription.id),
            name=new_subscription.name,
            frequency=new_subscription.frequency,
            type=new_subscription.type,
            nextDelivery=new_subscription.next_delivery.isoformat(),
            recipients=new_subscription.recipients,
            user={
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating subscription")

def get_detection_data(start_date: datetime, end_date: datetime, db: Session) -> pd.DataFrame:
    """Get detection data for the specified time range"""
    detections = db.query(
        TrackDetection.detected_at,
        Track.title,
        Track.artist_id,
        Artist.name.label('artist_name'),
        RadioStation.name.label('station_name'),
        TrackDetection.confidence
    ).join(Track, TrackDetection.track_id == Track.id)\
     .join(Artist, Track.artist_id == Artist.id)\
     .join(RadioStation, TrackDetection.station_id == RadioStation.id)\
     .filter(
        TrackDetection.detected_at >= start_date,
        TrackDetection.detected_at <= end_date
     ).all()
    
    if not detections:
        return pd.DataFrame(columns=['detected_at', 'title', 'artist_name', 'station_name', 'confidence'])
    
    return pd.DataFrame([{
        'detected_at': d.detected_at,
        'title': d.title,
        'artist_name': d.artist_name,
        'station_name': d.station_name,
        'confidence': d.confidence
    } for d in detections])

def get_analytics_data(start_date: datetime, end_date: datetime, db: Session) -> pd.DataFrame:
    """Get analytics data for the specified time range"""
    analytics = db.query(
        func.date_trunc('day', TrackDetection.detected_at).label('date'),
        func.count(TrackDetection.id).label('total_detections'),
        func.count(distinct(Track.id)).label('unique_tracks'),
        func.count(distinct(Track.artist_id)).label('unique_artists'),
        func.count(distinct(RadioStation.id)).label('active_stations'),
        func.avg(TrackDetection.confidence).label('avg_confidence')
    ).join(Track, TrackDetection.track_id == Track.id)\
     .join(RadioStation, TrackDetection.station_id == RadioStation.id)\
     .filter(
        TrackDetection.detected_at >= start_date,
        TrackDetection.detected_at <= end_date
     ).group_by(func.date_trunc('day', TrackDetection.detected_at))\
     .order_by(func.date_trunc('day', TrackDetection.detected_at))\
     .all()
    
    if not analytics:
        return pd.DataFrame(columns=['date', 'total_detections', 'unique_tracks', 'unique_artists', 'active_stations', 'avg_confidence'])
    
    return pd.DataFrame([{
        'date': a.date,
        'total_detections': a.total_detections,
        'unique_tracks': a.unique_tracks,
        'unique_artists': a.unique_artists,
        'active_stations': a.active_stations,
        'avg_confidence': round(float(a.avg_confidence), 2) if a.avg_confidence else 0
    } for a in analytics])

def get_summary_data(start_date: datetime, end_date: datetime, db: Session) -> pd.DataFrame:
    """Get summary data for the specified time range"""
    # Get daily stats
    daily_stats = db.query(
        func.date_trunc('day', TrackDetection.detected_at).label('date'),
        func.count(TrackDetection.id).label('total_detections'),
        func.count(distinct(Track.id)).label('unique_tracks'),
        func.count(distinct(Track.artist_id)).label('unique_artists'),
        func.count(distinct(RadioStation.id)).label('active_stations'),
        func.avg(TrackDetection.confidence).label('avg_confidence'),
        func.sum(TrackDetection.play_duration).label('total_play_time')
    ).join(Track, TrackDetection.track_id == Track.id)\
     .join(RadioStation, TrackDetection.station_id == RadioStation.id)\
     .filter(
        TrackDetection.detected_at >= start_date,
        TrackDetection.detected_at <= end_date
     ).group_by(func.date_trunc('day', TrackDetection.detected_at))\
     .order_by(func.date_trunc('day', TrackDetection.detected_at))\
     .all()
    
    if not daily_stats:
        return pd.DataFrame(columns=['date', 'total_detections', 'unique_tracks', 'unique_artists', 'active_stations', 'avg_confidence', 'total_play_time'])
    
    return pd.DataFrame([{
        'date': d.date.strftime('%Y-%m-%d'),
        'total_detections': d.total_detections,
        'unique_tracks': d.unique_tracks,
        'unique_artists': d.unique_artists,
        'active_stations': d.active_stations,
        'avg_confidence': round(float(d.avg_confidence), 2) if d.avg_confidence else 0,
        'total_play_time': str(d.total_play_time) if d.total_play_time else '00:00:00'
    } for d in daily_stats])

async def generate_report(report_id: int):
    """Background task to generate report"""
    logger.info(f"Starting report generation for report_id: {report_id}")
    db = SessionLocal()
    try:
        # Get report details
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            logger.error(f"Report {report_id} not found")
            return

        logger.info(f"Generating {report.type} report in {report.format} format")
        report.status = "generating"
        report.progress = 0.0
        db.commit()

        # Get data based on report type
        data = None
        if report.type == "detection":
            logger.info("Getting detection data...")
            data = get_detection_data(report.start_date, report.end_date, db)
            report.progress = 0.3
        elif report.type == "analytics":
            logger.info("Getting analytics data...")
            data = get_analytics_data(report.start_date, report.end_date, db)
            report.progress = 0.3
        elif report.type == "summary":
            logger.info("Getting summary data...")
            data = get_summary_data(report.start_date, report.end_date, db)
            report.progress = 0.3
        else:
            raise ValueError(f"Unsupported report type: {report.type}")

        db.commit()
        
        if data is None:
            logger.error("No data returned from query")
            report.status = "failed"
            report.error_message = "No data returned from query"
            db.commit()
            return
            
        if data.empty:
            logger.warning("No data found for the specified time range")
            report.status = "failed"
            report.error_message = "No data found for the specified time range"
            db.commit()
            return

        # Create report file
        file_path = REPORTS_DIR / f"report_{report.id}.{report.format}"
        logger.info(f"Creating report file at: {file_path}")
        
        report.progress = 0.6
        db.commit()

        # Export data in the requested format
        try:
            if report.format == "csv":
                logger.info("Exporting to CSV...")
                data.to_csv(file_path, index=False, encoding='utf-8')
            elif report.format == "xlsx":
                logger.info("Exporting to Excel...")
                data.to_excel(file_path, index=False, engine='openpyxl')
            elif report.format == "json":
                logger.info("Exporting to JSON...")
                data.to_json(file_path, orient='records', date_format='iso')
            else:
                raise ValueError(f"Unsupported format: {report.format}")
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            report.status = "failed"
            report.error_message = f"Error exporting data: {str(e)}"
            db.commit()
            return

        report.progress = 0.9
        db.commit()

        # Verify file was created
        if not file_path.exists():
            logger.error("File was not created")
            raise Exception("Failed to create report file")

        # Update report status
        logger.info("Report generated successfully")
        report.file_path = str(file_path)
        report.status = "completed"
        report.progress = 1.0
        report.completed_at = datetime.now()
        db.commit()

    except Exception as e:
        logger.error(f"Error generating report {report_id}: {str(e)}")
        if report:
            report.status = "failed"
            report.error_message = str(e)
            db.commit()
    finally:
        db.close()
        logger.info("Report generation process completed")

@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a generated report"""
    try:
        report = db.query(Report).filter(
            Report.id == report_id,
            Report.user_id == current_user.id
        ).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        if report.status != "completed":
            raise HTTPException(status_code=400, detail="Report not ready for download")
        
        file_path = REPORTS_DIR / f"report_{report.id}.{report.format}"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report file not found")
        
        return FileResponse(
            str(file_path),
            filename=f"report_{report.type}_{report.created_at.date()}.{report.format}",
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 