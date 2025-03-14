"""Detections router module for SODAV Monitor.

This module handles music detection operations and management.
"""

from fastapi import APIRouter

from .core import router as core_router
from .processing import router as processing_router
from .search import router as search_router

# Create a combined router
router = APIRouter()

# Include the sub-routers
router.include_router(core_router)
router.include_router(search_router)
router.include_router(processing_router)

__all__ = ["router"]
