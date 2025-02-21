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
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

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
    email: EmailStr
    frequency: str  # quotidien, hebdomadaire, mensuel
    report_type: str  # artist, track, station, label, comprehensive
    format: str = "xlsx"
    filters: Optional[Dict] = None
    include_graphs: bool = True
    language: str = "fr"

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

class ReportRequest(BaseModel):
    report_type: str  # "artist", "track", "station", "label", "comprehensive"
    format: str = "xlsx"  # "xlsx", "csv", "pdf"
    start_date: datetime
    end_date: datetime
    email: Optional[EmailStr] = None
    filters: Optional[Dict] = None
    include_graphs: bool = True
    language: str = "fr"  # fr, en
    timezone: str = "Africa/Dakar"

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
        # Validate frequency
        valid_frequencies = ["quotidien", "hebdomadaire", "mensuel"]
        if subscription.frequency not in valid_frequencies:
            raise HTTPException(
                status_code=400, 
                detail=f"Fréquence invalide. Doit être l'un de : {', '.join(valid_frequencies)}"
            )

        # Calculate next delivery
        next_delivery = calculate_next_delivery(subscription.frequency)

        new_subscription = ReportSubscription(
            name=subscription.name,
            email=subscription.email,
            frequency=subscription.frequency,
            report_type=subscription.report_type,
            format=subscription.format,
            filters=subscription.filters,
            include_graphs=subscription.include_graphs,
            language=subscription.language,
            next_delivery=next_delivery,
            user_id=current_user.id
        )
        db.add(new_subscription)
        db.commit()
        db.refresh(new_subscription)
        
        return {
            "message": "Abonnement créé avec succès",
            "subscription_id": new_subscription.id,
            "next_delivery": next_delivery.strftime("%Y-%m-%d %H:%M:%S")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création de l'abonnement")

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

def send_email_with_report(email: str, report_path: str, report_type: str, language: str = "fr"):
    """Send email with report attachment"""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    msg = MIMEMultipart()
    msg["From"] = "SODAV Monitor <rapports@sodav.sn>"
    msg["To"] = email
    
    # Email templates based on language
    templates = {
        "fr": {
            "subject": "SODAV Monitor - Rapport {type}",
            "body": """
            Cher utilisateur,

            Veuillez trouver ci-joint votre rapport {type} de SODAV Monitor.
            
            Ce rapport contient des informations détaillées sur les diffusions musicales 
            et les statistiques d'utilisation pour la période du {start_date} au {end_date}.

            Résumé :
            - Total diffusions : {total_plays}
            - Artistes uniques : {unique_artists}
            - Stations actives : {active_stations}

            Cordialement,
            L'équipe SODAV Monitor
            """
        },
        "en": {
            "subject": "SODAV Monitor - {type} Report",
            "body": """
            Dear user,

            Please find attached your SODAV Monitor {type} report.
            
            This report contains detailed information about music broadcasts 
            and usage statistics for the period from {start_date} to {end_date}.

            Summary:
            - Total plays: {total_plays}
            - Unique artists: {unique_artists}
            - Active stations: {active_stations}

            Best regards,
            SODAV Monitor Team
            """
        }
    }

    template = templates.get(language, templates["fr"])
    
    # Get summary statistics
    db = SessionLocal()
    stats = get_summary_stats(db, report_type, report.start_date, report.end_date)
    db.close()

    msg["Subject"] = template["subject"].format(type=report_type.title())
    body = template["body"].format(
        type=report_type,
        start_date=stats["start_date"].strftime("%d/%m/%Y"),
        end_date=stats["end_date"].strftime("%d/%m/%Y"),
        total_plays=stats["total_plays"],
        unique_artists=stats["unique_artists"],
        active_stations=stats["active_stations"]
    )
    
    msg.attach(MIMEText(body, "plain"))

    with open(report_path, "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype=os.path.splitext(report_path)[1][1:])
        attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(report_path))
        msg.attach(attachment)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

def get_summary_stats(db: Session, report_type: str, start_date: datetime, end_date: datetime) -> Dict:
    """Get summary statistics for email"""
    total_plays = db.query(func.count(TrackDetection.id))\
        .filter(TrackDetection.detected_at.between(start_date, end_date))\
        .scalar() or 0

    unique_artists = db.query(func.count(distinct(Track.artist_id)))\
        .join(TrackDetection)\
        .filter(TrackDetection.detected_at.between(start_date, end_date))\
        .scalar() or 0

    active_stations = db.query(func.count(distinct(RadioStation.id)))\
        .join(TrackDetection)\
        .filter(TrackDetection.detected_at.between(start_date, end_date))\
        .scalar() or 0

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_plays": total_plays,
        "unique_artists": unique_artists,
        "active_stations": active_stations
    }

def generate_comprehensive_report(db: Session, start_date: datetime, end_date: datetime, format: str, include_graphs: bool, filters: Optional[Dict] = None) -> str:
    """Generate a comprehensive report with all metrics"""
    # Create report directory if it doesn't exist
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"comprehensive_report_{timestamp}.{format}"
    filepath = reports_dir / filename

    # Collect all data
    data = {
        "tracks": get_tracks_data(db, start_date, end_date),
        "artists": get_artists_data(db, start_date, end_date),
        "stations": get_stations_data(db, start_date, end_date),
        "labels": get_labels_data(db, start_date, end_date)
    }

    if format == "xlsx":
        with pd.ExcelWriter(filepath) as writer:
            for sheet_name, df in data.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    elif format == "csv":
        # For CSV, concatenate all data with headers
        all_data = pd.concat(data.values(), keys=data.keys())
        all_data.to_csv(filepath, index=True)
    elif format == "pdf":
        # Implement PDF generation using a library like reportlab
        pass

    return str(filepath)

def get_tracks_data(db: Session, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Get detailed tracks data"""
    tracks = db.query(
        Track.title,
        Track.artist,
        Track.album,
        Track.isrc,
        Track.label,
        func.count(TrackDetection.id).label('play_count'),
        func.sum(func.extract('epoch', TrackDetection.play_duration)).label('total_play_time')
    ).join(TrackDetection).filter(
        TrackDetection.detected_at.between(start_date, end_date)
    ).group_by(Track.id).all()

    return pd.DataFrame(tracks)

def get_artists_data(db: Session, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Get detailed artists data"""
    artists = db.query(
        Track.artist,
        func.count(distinct(Track.id)).label('unique_tracks'),
        func.count(TrackDetection.id).label('total_plays'),
        func.sum(func.extract('epoch', TrackDetection.play_duration)).label('total_play_time')
    ).join(TrackDetection).filter(
        TrackDetection.detected_at.between(start_date, end_date)
    ).group_by(Track.artist).all()

    return pd.DataFrame(artists)

def get_stations_data(db: Session, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Get detailed stations data"""
    stations = db.query(
        RadioStation.name,
        RadioStation.country,
        RadioStation.language,
        func.count(TrackDetection.id).label('total_detections'),
        func.count(distinct(Track.id)).label('unique_tracks')
    ).join(TrackDetection).join(Track).filter(
        TrackDetection.detected_at.between(start_date, end_date)
    ).group_by(RadioStation.id).all()

    return pd.DataFrame(stations)

def get_labels_data(db: Session, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Get detailed labels data"""
    labels = db.query(
        Track.label,
        func.count(distinct(Track.id)).label('unique_tracks'),
        func.count(TrackDetection.id).label('total_plays'),
        func.sum(func.extract('epoch', TrackDetection.play_duration)).label('total_play_time')
    ).join(TrackDetection).filter(
        TrackDetection.detected_at.between(start_date, end_date)
    ).group_by(Track.label).all()

    return pd.DataFrame(labels)

@router.post("/generate")
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new report"""
    try:
        # Create report record
        report = Report(
            type=request.report_type,
            format=request.format,
            start_date=request.start_date,
            end_date=request.end_date,
            status="pending",
            user_id=current_user.id,
            filters=request.filters
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Generate report
        report_path = generate_comprehensive_report(
            db,
            request.start_date,
            request.end_date,
            request.format,
            request.include_graphs,
            request.filters
        )

        # Update report status
        report.status = "completed"
        report.file_path = report_path
        report.completed_at = datetime.now()
        db.commit()

        # If email provided, send report via email
        if request.email:
            background_tasks.add_task(
                send_email_with_report,
                request.email,
                report_path,
                request.report_type,
                request.language
            )
            return {"message": "Rapport généré et envoyé par email", "status": "success"}

        # Otherwise return file for download
        return FileResponse(
            report_path,
            filename=f"sodav_rapport_{request.report_type}_{datetime.now().strftime('%Y%m%d')}.{request.format}",
            media_type="application/octet-stream"
        )

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        if report:
            report.status = "failed"
            report.error_message = str(e)
            db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/subscriptions")
async def list_subscriptions(
    email: EmailStr,
    db: Session = Depends(get_db)
):
    """List all subscriptions for an email"""
    subscriptions = db.query(ReportSubscription).filter(
        ReportSubscription.email == email
    ).all()
    return subscriptions

@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    """Delete a subscription"""
    subscription = db.query(ReportSubscription).filter(
        ReportSubscription.id == subscription_id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    db.delete(subscription)
    db.commit()
    return {"message": "Subscription deleted successfully"}

def calculate_next_delivery(frequency: str) -> datetime:
    """Calculate next delivery date based on frequency"""
    now = datetime.now()
    if frequency == "quotidien":
        # Next day at 06:00
        next_day = now + timedelta(days=1)
        return datetime(next_day.year, next_day.month, next_day.day, 6, 0, 0)
    elif frequency == "hebdomadaire":
        # Next Monday at 06:00
        days_ahead = 7 - now.weekday()
        next_monday = now + timedelta(days=days_ahead)
        return datetime(next_monday.year, next_monday.month, next_monday.day, 6, 0, 0)
    elif frequency == "mensuel":
        # First day of next month at 06:00
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1, 6, 0, 0)
        else:
            next_month = datetime(now.year, now.month + 1, 1, 6, 0, 0)
        return next_month
    else:
        raise ValueError("Fréquence invalide") 