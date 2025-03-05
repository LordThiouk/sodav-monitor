"""Analytics router module for SODAV Monitor.

This module handles analytics and statistics operations.
"""

from fastapi import APIRouter

from .overview import router as overview_router
from .stations import router as stations_router
from .artists import router as artists_router
from .tracks import router as tracks_router
from .export import router as export_router

# Create a combined router
router = APIRouter()

# Include the sub-routers
router.include_router(overview_router)
router.include_router(stations_router)
router.include_router(artists_router)
router.include_router(tracks_router)
router.include_router(export_router)

__all__ = ["router"] 