from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, Dict, Any
import uvicorn
import os
import logging
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import redis.asyncio as redis
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio
import threading

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
from backend.routers.metrics import router as metrics_router
from backend.models.database import init_db, get_db
from backend.core.config import get_settings, PATHS
from backend.utils.redis_config import init_redis_pool
from backend.utils.auth import get_current_user
from backend.utils.radio import fetch_and_save_senegal_stations
from backend.utils.middleware import PrometheusMiddleware, SystemMetricsCollector
from backend.detection.audio_processor.stream_handler import StreamHandler
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.scripts.detection.detect_music_all_stations import detect_music_all_stations
from backend.detection.detect_music import MusicDetector
from backend.routers.channels.monitoring import detect_station_music
from backend.models.models import RadioStation, StationStatus
from backend.detection.audio_processor.track_manager import TrackManager

# Load environment variables first
load_dotenv()

# Initialize logging once
log_manager = LogManager()
logger = log_manager.get_logger("main")

# Créer le collecteur de métriques système
system_metrics_collector = SystemMetricsCollector(interval=15)

# Variable globale pour stocker la tâche de détection
detection_task = None
detection_running = False

# Fonction pour exécuter le service de détection en arrière-plan
async def run_detection_service(interval: int = 300):
    """
    Exécute le service de détection en arrière-plan.
    
    Args:
        interval: Intervalle en secondes entre les cycles de détection
    """
    global detection_running
    
    logger.info(f"Starting automatic detection service with interval of {interval} seconds")
    detection_running = True
    
    while detection_running:
        try:
            # Créer une nouvelle session de base de données
            from backend.models.database import SessionLocal
            db = SessionLocal()
            
            try:
                # Récupérer toutes les stations actives
                active_stations = db.query(RadioStation).filter(
                    RadioStation.status == StationStatus.ACTIVE
                ).all()
                
                if active_stations:
                    logger.info(f"Running automatic detection for {len(active_stations)} active stations")
                    
                    # Traiter chaque station
                    for station in active_stations:
                        if not detection_running:
                            break
                        
                        try:
                            logger.info(f"Detecting music for station: {station.name} (ID: {station.id})")
                            await detect_station_music(station.id)
                            # Petite pause entre les stations pour éviter de surcharger le système
                            await asyncio.sleep(2)
                        except Exception as e:
                            logger.error(f"Error detecting music for station {station.name}: {str(e)}")
                else:
                    logger.warning("No active stations found for automatic detection")
            finally:
                db.close()
                
            # Attendre l'intervalle spécifié avant le prochain cycle
            logger.info(f"Waiting {interval} seconds until next detection cycle")
            for _ in range(interval // 10):  # Diviser l'attente en segments de 10 secondes
                if not detection_running:
                    break
                await asyncio.sleep(10)
                
        except Exception as e:
            logger.error(f"Error in detection service: {str(e)}")
            await asyncio.sleep(60)  # Attendre 1 minute en cas d'erreur

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the application."""
    global detection_task, detection_running
    
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
        
        # Démarrer le collecteur de métriques système
        system_metrics_collector.start()
        logger.info("System metrics collector started successfully")
        
        # Fetch Senegalese radio stations and start detection
        db = next(get_db())
        try:
            logger.info("Fetching Senegalese radio stations from Radio Browser API...")
            stations_count = await fetch_and_save_senegal_stations(db)
            logger.info(f"Successfully processed {stations_count} Senegalese radio stations")
            
            if stations_count > 0:
                # Obtenir toutes les stations actives
                active_stations = db.query(RadioStation).filter(
                    RadioStation.status == StationStatus.ACTIVE
                ).all()
                
                if active_stations:
                    logger.info(f"Found {len(active_stations)} active stations for music detection")
                    
                    # Démarrer le service de détection automatique en arrière-plan
                    detection_task = asyncio.create_task(run_detection_service(interval=300))
                    logger.info("Automatic detection service started successfully")
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
        # Arrêter le service de détection
        detection_running = False
        if detection_task:
            logger.info("Stopping automatic detection service...")
            try:
                detection_task.cancel()
                await asyncio.wait_for(detection_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Timeout while waiting for detection task to cancel")
            except asyncio.CancelledError:
                logger.info("Detection task cancelled successfully")
            except Exception as e:
                logger.error(f"Error cancelling detection task: {str(e)}")
        
        # Arrêter le collecteur de métriques système
        system_metrics_collector.stop()
        logger.info("System metrics collector stopped successfully")
        
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

# Ajouter le middleware Prometheus
app.add_middleware(
    PrometheusMiddleware,
    exclude_paths=["/api/metrics", "/health", "/favicon.ico", "/api/docs", "/api/redoc", "/api/openapi.json"]
)

# Mount static files
app.mount("/static", StaticFiles(directory=PATHS["STATIC_DIR"]), name="static")

# Inclure le routeur des métriques en premier (sans authentification)
app.include_router(metrics_router, prefix="/api")

# Include routers in specific order (with authentication)
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

@app.get("/api/tracks/isrc/{isrc}", response_model=Dict[str, Any])
async def get_track_by_isrc(isrc: str, db: Session = Depends(get_db)):
    """
    Recherche une piste par son code ISRC.
    
    Args:
        isrc: Code ISRC à rechercher
        
    Returns:
        Informations sur la piste trouvée ou un message d'erreur
    """
    track_manager = TrackManager(db)
    result = await track_manager.find_track_by_isrc(isrc)
    
    if result:
        return {
            "success": True,
            "track": result["track"],
            "confidence": result["confidence"],
            "detection_method": result["detection_method"]
        }
    else:
        return {
            "success": False,
            "message": f"Aucune piste trouvée avec l'ISRC {isrc}"
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