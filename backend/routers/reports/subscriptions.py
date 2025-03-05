"""Report subscription functionality for SODAV Monitor.

This module handles the creation, management, and processing of report subscriptions.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import logging

from backend.models.database import get_db
from backend.models.models import ReportSubscription, User, ReportType, ReportFormat
from backend.utils.auth import get_current_user
from backend.schemas.base import SubscriptionCreate, SubscriptionResponse, SubscriptionUpdate

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/reports/subscriptions",
    tags=["subscriptions"],
    dependencies=[Depends(get_current_user)]  # Require authentication for all endpoints
)

@router.post("", response_model=SubscriptionResponse)
async def create_subscription(
    subscription: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new report subscription."""
    # Create a new subscription record
    db_subscription = ReportSubscription(
        name=subscription.name,
        email=subscription.email,
        frequency=subscription.frequency,
        report_type=subscription.report_type,
        format=subscription.format,
        filters=subscription.filters,
        include_graphs=subscription.include_graphs,
        language=subscription.language,
        created_by=current_user.id,
        next_delivery=calculate_next_delivery(subscription.frequency)
    )
    
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    
    return db_subscription

@router.get("", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a list of report subscriptions."""
    subscriptions = db.query(ReportSubscription).order_by(
        ReportSubscription.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return subscriptions

@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific report subscription by ID."""
    subscription = db.query(ReportSubscription).filter(
        ReportSubscription.id == subscription_id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return subscription

@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    update_data: SubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a specific report subscription."""
    subscription = db.query(ReportSubscription).filter(
        ReportSubscription.id == subscription_id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Update the subscription fields
    update_dict = update_data.dict(exclude_unset=True)
    
    # If frequency is updated, recalculate next_delivery
    if "frequency" in update_dict:
        update_dict["next_delivery"] = calculate_next_delivery(update_dict["frequency"])
    
    for key, value in update_dict.items():
        setattr(subscription, key, value)
    
    subscription.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(subscription)
    
    return subscription

@router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a specific report subscription."""
    subscription = db.query(ReportSubscription).filter(
        ReportSubscription.id == subscription_id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    db.delete(subscription)
    db.commit()
    
    return {"message": "Subscription deleted successfully"}

@router.get("/by-email")
async def list_subscriptions_by_email(
    email: EmailStr,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a list of report subscriptions for a specific email."""
    subscriptions = db.query(ReportSubscription).filter(
        ReportSubscription.email == email
    ).all()
    
    return subscriptions

# Helper functions

def calculate_next_delivery(frequency: str) -> datetime:
    """Calculate the next delivery date based on the subscription frequency."""
    now = datetime.utcnow()
    
    if frequency == "daily":
        # Next day at 6:00 AM
        next_delivery = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
    elif frequency == "weekly":
        # Next Monday at 6:00 AM
        days_until_monday = 7 - now.weekday() if now.weekday() > 0 else 7
        next_delivery = (now + timedelta(days=days_until_monday)).replace(hour=6, minute=0, second=0, microsecond=0)
    elif frequency == "monthly":
        # First day of next month at 6:00 AM
        if now.month == 12:
            next_delivery = datetime(now.year + 1, 1, 1, 6, 0, 0)
        else:
            next_delivery = datetime(now.year, now.month + 1, 1, 6, 0, 0)
    else:
        # Default to tomorrow at 6:00 AM
        next_delivery = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
    
    return next_delivery 