"""Reports router module for SODAV Monitor.

This module handles report generation, management, and subscriptions.
"""

from fastapi import APIRouter

from .core import router as core_router
from .generation import router as generation_router
from .subscriptions import router as subscriptions_router

# Create a combined router
router = APIRouter()

# Include the sub-routers
router.include_router(core_router)
router.include_router(generation_router)
router.include_router(subscriptions_router)

__all__ = ["router"] 