"""Channels router module for SODAV Monitor.

This module handles radio station management, monitoring, and status.
"""

from fastapi import APIRouter

from .core import router as core_router
from .monitoring import router as monitoring_router
from .status import router as status_router

# Create a combined router
router = APIRouter()

# Include the sub-routers
router.include_router(core_router)
router.include_router(monitoring_router)
router.include_router(status_router)

__all__ = ["router"]
