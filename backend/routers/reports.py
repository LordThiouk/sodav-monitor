from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
from database import get_db, SessionLocal
from models import Report, ReportSubscription, User, TrackDetection, Track, RadioStation, ReportStatus
import logging
import os
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
    type: str
    format: str = "csv"
    start_date: datetime
    end_date: datetime

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
        reports = db.query(Report).filter(Report.user_id == current_user.id).order_by(Report.created_at.desc()).all()
        return [
            ReportResponse(
                id=str(report.id),
                title=f"{report.type.capitalize()} Report",
                type=report.type,
                format=report.format,
                generatedAt=report.created_at.isoformat(),
                status=report.status,
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
        raise HTTPException(status_code=500, detail="Error retrieving reports")

@router.post("/", response_model=ReportResponse)
async def create_report(
    report: ReportCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new report"""
    try:
        # Validate user exists
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_report = Report(
            type=report.type,
            format=report.format,
            start_date=report.start_date,
            end_date=report.end_date,
            status="pending",
            user_id=current_user.id,
            created_at=datetime.now()
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
        raise HTTPException(status_code=500, detail="Error creating report")

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

async def generate_report(report_id: int):
    """Background task to generate report"""
    # Create a new database session for the background task
    task_db = SessionLocal()
    try:
        # First check if report exists
        report = task_db.query(Report).filter(Report.id == report_id).first()
        if not report:
            # Create new report if it doesn't exist
            report = Report(
                id=report_id,
                type="detection",  # Default type
                format="csv",      # Default format
                status="generating",
                created_at=datetime.now()
            )
            task_db.add(report)
            task_db.commit()
            task_db.refresh(report)
        else:
            # Update existing report
            report.status = "generating"
            task_db.commit()
            task_db.refresh(report)

        # Get data based on report type
        if report.type == "detection":
            data = get_detection_data(report.start_date, report.end_date, task_db)
        elif report.type == "analytics":
            data = get_analytics_data(report.start_date, report.end_date, task_db)
        else:
            data = get_summary_data(report.start_date, report.end_date, task_db)

        if data.empty:
            logger.warning(f"No data found for report {report_id}")
            report.status = "failed"
            report.error_message = "No data found for the specified time range"
            task_db.commit()
            task_db.refresh(report)
            return

        # Generate report file
        file_path = REPORTS_DIR / f"report_{report.id}.{report.format}"
        if report.format == "csv":
            data.to_csv(str(file_path), index=False)
        else:  # xlsx
            data.to_excel(str(file_path), index=False)

        # Verify file was created
        if not file_path.exists():
            raise Exception("Failed to create report file")

        report.file_path = str(file_path)
        report.status = "completed"
        report.completed_at = datetime.now()
        task_db.commit()
        task_db.refresh(report)

    except Exception as e:
        logger.error(f"Error generating report {report_id}: {str(e)}")
        if report:
            report.status = "failed"
            report.error_message = str(e)
            task_db.commit()
            task_db.refresh(report)
    finally:
        task_db.close()

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
            filename=f"report_{report.type}_{report.created_at.date()}.{report.format}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        raise HTTPException(status_code=500, detail="Error downloading report")

def get_detection_data(start_date: datetime, end_date: datetime, db: Session) -> pd.DataFrame:
    """Get detection data for report"""
    try:
        logger.info(f"Fetching detection data from {start_date} to {end_date}")
        detections = db.query(
            TrackDetection,
            Track,
            RadioStation
        ).join(
            Track,
            TrackDetection.track_id == Track.id
        ).join(
            RadioStation,
            TrackDetection.station_id == RadioStation.id
        ).filter(
            TrackDetection.detected_at.between(start_date, end_date)
        ).all()

        if not detections:
            logger.warning("No detections found for the specified time range")
            return pd.DataFrame()

        logger.info(f"Found {len(detections)} detections")
        data = pd.DataFrame([{
            'detected_at': d.detected_at,
            'station': s.name,
            'track': t.title,
            'artist': t.artist,
            'isrc': t.isrc or 'N/A',
            'label': t.label or 'N/A',
            'confidence': d.confidence,
            'play_duration': str(d.play_duration)
        } for d, t, s in detections])
        
        logger.info(f"Created DataFrame with {len(data)} rows")
        return data
    except Exception as e:
        logger.error(f"Error getting detection data: {str(e)}")
        return pd.DataFrame()

def get_analytics_data(start_date: datetime, end_date: datetime, db: Session) -> pd.DataFrame:
    """Get analytics data for report"""
    try:
        logger.info(f"Fetching analytics data from {start_date} to {end_date}")
        results = db.query(
            Track.artist,
            Track.label,
            RadioStation.name.label('station'),
            func.count(TrackDetection.id).label('plays'),
            func.avg(TrackDetection.confidence).label('avg_confidence')
        ).join(
            TrackDetection,
            Track.id == TrackDetection.track_id
        ).join(
            RadioStation,
            TrackDetection.station_id == RadioStation.id
        ).filter(
            TrackDetection.detected_at.between(start_date, end_date)
        ).group_by(
            Track.artist,
            Track.label,
            RadioStation.name
        ).all()

        if not results:
            logger.warning("No analytics data found for the specified time range")
            return pd.DataFrame()

        logger.info(f"Found {len(results)} analytics records")
        data = pd.DataFrame([{
            'artist': r.artist or 'Unknown',
            'label': r.label or 'N/A',
            'station': r.station,
            'total_plays': r.plays,
            'average_confidence': round(r.avg_confidence, 2)
        } for r in results])
        
        logger.info(f"Created DataFrame with {len(data)} rows")
        return data
    except Exception as e:
        logger.error(f"Error getting analytics data: {str(e)}")
        return pd.DataFrame()

def get_summary_data(start_date: datetime, end_date: datetime, db: Session) -> pd.DataFrame:
    """Get summary data for report"""
    try:
        logger.info(f"Fetching summary data from {start_date} to {end_date}")
        results = db.query(
            func.date(TrackDetection.detected_at).label('date'),
            func.count(TrackDetection.id).label('detections'),
            func.count(distinct(Track.id)).label('unique_tracks'),
            func.count(distinct(Track.artist)).label('unique_artists'),
            func.count(distinct(RadioStation.id)).label('active_stations')
        ).join(
            Track,
            TrackDetection.track_id == Track.id
        ).join(
            RadioStation,
            TrackDetection.station_id == RadioStation.id
        ).filter(
            TrackDetection.detected_at.between(start_date, end_date)
        ).group_by(
            func.date(TrackDetection.detected_at)
        ).all()

        if not results:
            logger.warning("No summary data found for the specified time range")
            return pd.DataFrame()

        logger.info(f"Found {len(results)} summary records")
        data = pd.DataFrame([{
            'date': r.date,
            'total_detections': r.detections,
            'unique_tracks': r.unique_tracks,
            'unique_artists': r.unique_artists,
            'active_stations': r.active_stations
        } for r in results])
        
        logger.info(f"Created DataFrame with {len(data)} rows")
        return data
    except Exception as e:
        logger.error(f"Error getting summary data: {str(e)}")
        return pd.DataFrame() 