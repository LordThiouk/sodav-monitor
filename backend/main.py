from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, Dict
import uvicorn
import os
from dotenv import load_dotenv

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

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="SODAV Monitor API",
    description="API for monitoring and detecting music in radio streams",
    version="1.0.0"
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

# Include routers
app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(channels.router)
app.include_router(reports.router)
app.include_router(detections.router)
app.include_router(websocket.router)

@app.on_event("startup")
async def startup_event():
    """Événement de démarrage de l'application."""
    await event_manager.startup()

@app.on_event("shutdown")
async def shutdown_event():
    """Événement d'arrêt de l'application."""
    await event_manager.shutdown()

@app.get("/api/health")
async def health_check():
    """Point de terminaison pour vérifier l'état du système."""
    return await event_manager.health_check()

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