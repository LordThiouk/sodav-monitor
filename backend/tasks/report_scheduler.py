from datetime import datetime, timedelta
import asyncio
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_
import os

from models import ReportSubscription, Report
from database import SessionLocal
from routers.reports import generate_comprehensive_report, send_email_with_report

logger = logging.getLogger(__name__)

async def process_subscriptions():
    """Process all due subscriptions and generate reports"""
    while True:
        try:
            db = SessionLocal()
            now = datetime.now()
            
            # Get all active subscriptions that are due
            due_subscriptions = db.query(ReportSubscription).filter(
                and_(
                    ReportSubscription.is_active == True,
                    ReportSubscription.next_delivery <= now
                )
            ).all()
            
            for subscription in due_subscriptions:
                try:
                    # Calculate report period based on frequency
                    if subscription.frequency == "quotidien":
                        start_date = now - timedelta(days=1)
                    elif subscription.frequency == "hebdomadaire":
                        start_date = now - timedelta(weeks=1)
                    else:  # mensuel
                        start_date = now - timedelta(days=30)
                    
                    # Generate report
                    report_path = generate_comprehensive_report(
                        db,
                        start_date,
                        now,
                        subscription.format,
                        True,  # include_graphs
                        subscription.filters
                    )
                    
                    # Send email
                    await send_email_with_report(
                        subscription.email,
                        report_path,
                        subscription.report_type,
                        subscription.language
                    )
                    
                    # Update subscription
                    subscription.last_delivery = now
                    subscription.next_delivery = calculate_next_delivery(subscription.frequency)
                    subscription.delivery_count += 1
                    db.commit()
                    
                    logger.info(f"Successfully processed subscription {subscription.id}")
                    
                except Exception as e:
                    logger.error(f"Error processing subscription {subscription.id}: {str(e)}")
                    subscription.error_count += 1
                    subscription.last_error = str(e)
                    db.commit()
            
        except Exception as e:
            logger.error(f"Error in subscription processor: {str(e)}")
        
        finally:
            db.close()
        
        # Wait for 5 minutes before next check
        await asyncio.sleep(300)

async def cleanup_old_reports():
    """Clean up old report files"""
    while True:
        try:
            db = SessionLocal()
            now = datetime.now()
            
            # Get reports older than 90 days
            old_reports = db.query(Report).filter(
                Report.created_at <= now - timedelta(days=90)
            ).all()
            
            for report in old_reports:
                try:
                    if report.file_path:
                        # Delete file
                        os.remove(report.file_path)
                    # Delete database record
                    db.delete(report)
                except Exception as e:
                    logger.error(f"Error deleting report {report.id}: {str(e)}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error in report cleanup: {str(e)}")
        
        finally:
            db.close()
        
        # Run cleanup daily
        await asyncio.sleep(86400)

async def start_schedulers():
    """Start all scheduler tasks"""
    await asyncio.gather(
        process_subscriptions(),
        cleanup_old_reports()
    ) 