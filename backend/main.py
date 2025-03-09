from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, Dict
import uvicorn
import os
import logging
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import redis.asyncio as redis
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio

# Local imports - using consistent backend prefix
from backend.logs.log_manager import LogManager
from backend.core.events import event_manager
from backend.routers import (
    auth,
    websocket
)
from backend.routers.analytics import router as analytics_router
from backend.routers.reports import router as reports_router
from backend.routers.channels import router as channels_router
from backend.routers.detections import router as detections_router
from backend.models.database import init_db, get_db
from backend.core.config import get_settings, PATHS
from backend.utils.redis_config import init_redis_pool
from backend.utils.auth import get_current_user
from backend.utils.radio import fetch_and_save_senegal_stations
from backend.detection.audio_processor.stream_handler import StreamHandler
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.scripts.detection.detect_music_all_stations import detect_music_all_stations
from backend.detection.detect_music import MusicDetector
from backend.routers.channels.monitoring import detect_station_music
from backend.models.models import RadioStation, StationStatus

# Load environment variables first
load_dotenv()

# Initialize logging once
log_manager = LogManager()
logger = log_manager.get_logger("main")

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the application."""
    # Startup
    try:
        # Validate required API keys
        settings = get_settings()
        if not settings.ACOUSTID_API_KEY:
            logger.warning("ACOUSTID_API_KEY is not set. MusicBrainz recognition will be disabled.")
        if not settings.AUDD_API_KEY:
            logger.warning("AUDD_API_KEY is not set. AudD recognition will be disabled.")
            
        # Initialize database
        init_db()
        logger.info("Database initialized successfully")

        # Initialize Redis pool
        app.state.redis_pool = await init_redis_pool()
        logger.info("Redis pool initialized successfully")
        
        # Fetch Senegalese radio stations and start detection
        db = next(get_db())
        try:
            logger.info("Fetching Senegalese radio stations from Radio Browser API...")
            stations_count = await fetch_and_save_senegal_stations(db)
            logger.info(f"Successfully processed {stations_count} Senegalese radio stations")
            
            if stations_count > 0:
                # Lancer la détection de musique sur toutes les stations
                logger.info("Starting music detection on all stations...")
                
                # Obtenir toutes les stations actives
                active_stations = db.query(RadioStation).filter(
                    RadioStation.status == StationStatus.ACTIVE
                ).all()
                
                if active_stations:
                    logger.info(f"Found {len(active_stations)} active stations for music detection")
                    
                    # Informer sur le service de détection séparé
                    logger.info("Music detection is not started automatically to prevent server blocking.")
                    logger.info("To start the detection service, run: python backend/scripts/run_detection_service.py")
                    logger.info("You can customize the service with: --max_concurrent 5 --interval 60")
                else:
                    logger.warning("No active stations found for music detection")
            else:
                logger.warning("No stations found, skipping music detection")
                
        except Exception as e:
            logger.error(f"Error during startup sequence: {str(e)}")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

    yield  # Application runs here

    # Shutdown
    try:
        if hasattr(app.state, 'redis_pool'):
            await app.state.redis_pool.aclose()
            logger.info("Redis pool closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# Create FastAPI app
app = FastAPI(
    title="SODAV Monitor",
    description="API for monitoring radio stations and detecting music",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
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
app.mount("/static", StaticFiles(directory=PATHS["STATIC_DIR"]), name="static")

# Include routers in specific order
app.include_router(auth.router, prefix="/api")
app.include_router(detections_router, prefix="/api")  # Detections router first for /search endpoint
app.include_router(channels_router, prefix="/api")
app.include_router(analytics_router, prefix="/api/analytics")
app.include_router(reports_router, prefix="/api/reports")
app.include_router(websocket.router, prefix="/api/ws")

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