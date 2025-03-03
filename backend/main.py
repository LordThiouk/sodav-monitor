from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, Dict
import uvicorn
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import logging
import redis.asyncio as redis
from datetime import datetime

# Local imports
from backend.core.events import event_manager
from backend.routers import (
    auth,
    analytics,
    channels,
    reports,
    detections,
    websocket
)
from .models.database import init_db, get_db
from .core.config import get_settings
from .utils.redis_config import init_redis_pool
from .core.security import get_current_user

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SODAV Monitor",
    description="API for monitoring radio stations and detecting music",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers in specific order
app.include_router(auth.router, prefix="/api")
app.include_router(detections.router)  # Detections router first for /search endpoint
app.include_router(channels.router, prefix="/api")
app.include_router(analytics.router, prefix="/api/analytics")
app.include_router(reports.router, prefix="/api/reports")
app.include_router(websocket.router, prefix="/api/ws")

@app.on_event("startup")
async def startup_event():
    """Événement de démarrage de l'application."""
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized successfully")

        # Initialize Redis pool
        app.state.redis_pool = await init_redis_pool()
        logger.info("Redis pool initialized successfully")

    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Événement d'arrêt de l'application."""
    try:
        if hasattr(app.state, 'redis_pool'):
            await app.state.redis_pool.close()
            logger.info("Redis pool closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

@app.get("/health")
async def health_check():
    """Point de terminaison pour vérifier l'état du système."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to SODAV Monitor API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', '8000'))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Configure uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=debug,
        log_config=log_config,
        log_level="debug" if debug else "info",
        access_log=True,
        workers=1  # Ensure single worker for WebSocket support
    ) 