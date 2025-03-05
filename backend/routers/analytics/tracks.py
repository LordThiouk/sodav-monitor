"""Track analytics functionality for SODAV Monitor.

This module handles the track analytics endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import logging

from backend.models.database import get_db
from backend.analytics.stats_manager import StatsManager
from backend.utils.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    tags=["analytics"],
    responses={404: {"description": "Not found"}}
)

async def get_stats_manager(db: Session = Depends(get_db)) -> StatsManager:
    """Dependency to get StatsManager instance."""
    stats_manager = StatsManager(db)
    try:
        yield stats_manager
    finally:
        await stats_manager.close()

@router.get(
    "/tracks",
    response_model=List[Dict],
    summary="Get Track Analytics",
    description="Returns detailed analytics data for all tracks"
)
async def get_track_analytics(
    stats_manager: StatsManager = Depends(get_stats_manager),
    current_user = Depends(get_current_user)
):
    """
    Get detailed track analytics including:
    - Detection counts
    - Play duration
    - Confidence scores
    - Station distribution
    """
    try:
        return await stats_manager.get_all_track_stats()
    except Exception as e:
        logger.error(f"Error in track analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving track analytics: {str(e)}"
        )

@router.get(
    "/tracks/{track_id}/stats",
    response_model=Dict,
    summary="Get Track Statistics",
    description="Returns statistics for a specific track"
)
async def get_track_stats(
    track_id: int,
    stats_manager: StatsManager = Depends(get_stats_manager),
    current_user = Depends(get_current_user)
):
    """Get statistics for a specific track."""
    try:
        return await stats_manager.get_track_stats(track_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting track stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving track statistics: {str(e)}"
        ) 