"""Export analytics functionality for SODAV Monitor.

This module handles the export analytics endpoints.
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.analytics.stats_manager import StatsManager
from backend.models.database import get_db
from backend.utils.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["analytics"], responses={404: {"description": "Not found"}})


async def get_stats_manager(db: Session = Depends(get_db)) -> StatsManager:
    """Dependency to get StatsManager instance."""
    stats_manager = StatsManager(db)
    try:
        yield stats_manager
    finally:
        await stats_manager.close()


@router.get(
    "/export",
    response_model=List[Dict],
    summary="Export Analytics Data",
    description="Exports analytics data in the specified format",
)
async def export_analytics(
    format: str = "json",
    stats_manager: StatsManager = Depends(get_stats_manager),
    current_user=Depends(get_current_user),
):
    """Export analytics data in the specified format."""
    try:
        if format not in ["json", "csv", "xlsx"]:
            raise HTTPException(status_code=400, detail="Invalid export format")

        return await stats_manager.export_analytics(format)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error exporting analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error exporting analytics data: {str(e)}")
