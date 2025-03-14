import logging
import os
import time
from datetime import datetime
from typing import Dict, Optional

import psutil
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configuration du logging avec plus de détails
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Variable globale pour stocker le temps de démarrage
START_TIME = time.time()


def get_uptime() -> float:
    """Retourne le uptime de l'application en secondes."""
    return time.time() - START_TIME


def check_database_connection() -> Dict[str, bool]:
    """Vérifie la connexion à la base de données."""
    try:
        database_url = os.getenv("DATABASE_URL")
        logger.info(
            f"Checking database connection with URL type: {database_url.split('://')[0] if database_url else 'None'}"
        )

        if not database_url:
            error_msg = "DATABASE_URL not set in environment"
            logger.error(error_msg)
            return {"connected": False, "error": error_msg}

        # Assurer que l'URL commence par postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
            logger.info("URL converted from postgres:// to postgresql://")

        logger.info("Creating database engine with URL type: %s", database_url.split("://")[0])
        engine = create_engine(database_url, pool_pre_ping=True)

        logger.info("Testing database connection with SELECT 1 query...")
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
            logger.info(f"Database connection successful, test query returned: {result}")
            return {"connected": True, "error": None}

    except SQLAlchemyError as e:
        error_msg = f"Database connection error: {str(e)}"
        logger.error(error_msg)
        return {"connected": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error during database check: {str(e)}"
        logger.error(error_msg)
        return {"connected": False, "error": error_msg}


def check_system_resources() -> Dict[str, float]:
    """Vérifie les ressources système."""
    try:
        logger.info("Starting system resources check...")

        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        resources = {
            "cpu_percent": cpu,
            "memory_percent": memory.percent,
            "memory_available": memory.available / 1024 / 1024,  # MB
            "disk_percent": disk.percent,
            "disk_free": disk.free / 1024 / 1024 / 1024,  # GB
        }

        logger.info(
            f"System resources check completed - CPU: {cpu}%, Memory: {memory.percent}% ({resources['memory_available']:.1f}MB free), Disk: {disk.percent}% ({resources['disk_free']:.1f}GB free)"
        )

        return resources
    except Exception as e:
        error_msg = f"Error checking system resources: {str(e)}"
        logger.error(error_msg)
        return {
            "cpu_percent": -1,
            "memory_percent": -1,
            "memory_available": -1,
            "disk_percent": -1,
            "disk_free": -1,
            "error": error_msg,
        }


def get_system_health() -> Dict:
    """Obtient l'état de santé complet du système."""
    try:
        logger.info("Starting comprehensive system health check...")

        # Vérifier si nous sommes en période de démarrage
        is_startup = os.getenv("STARTUP_GRACE_PERIOD", "false").lower() == "true"
        startup_message = (
            "System is in startup grace period"
            if is_startup
            else "System is in normal operation mode"
        )
        logger.info(startup_message)

        if is_startup:
            # During startup, always return healthy
            return {
                "status": "healthy",
                "message": "Application is in startup grace period",
                "timestamp": datetime.now().isoformat(),
                "uptime": get_uptime(),
                "startup_time_remaining": float(os.getenv("HEALTHCHECK_START_PERIOD", "600"))
                - get_uptime(),
            }

        # Vérifier la base de données
        db_status = check_database_connection()
        logger.info(f"Database health check completed: {db_status}")

        # Vérifier les ressources système
        resources = check_system_resources()
        logger.info(f"System resources check completed: {resources}")

        # Vérifier l'espace disque critique
        disk_critical = resources.get("disk_percent", 0) > 90 or resources.get("disk_free", 0) < 1
        memory_critical = (
            resources.get("memory_percent", 0) > 90 or resources.get("memory_available", 0) < 100
        )

        # Déterminer le statut global
        status = "healthy"
        status_message = "All systems operational"

        if not db_status["connected"]:
            status = "error"
            status_message = f"Database connection failed: {db_status['error']}"
        elif disk_critical:
            status = "warning"
            status_message = "Disk space critically low"
        elif memory_critical:
            status = "warning"
            status_message = "Memory usage critically high"
        elif resources.get("cpu_percent", 0) > 90:
            status = "warning"
            status_message = "CPU usage critically high"

        health_status = {
            "status": status,
            "message": status_message,
            "timestamp": datetime.now().isoformat(),
            "uptime": get_uptime(),
            "database": {"connected": db_status["connected"], "error": db_status["error"]},
            "system": resources,
            "environment": {
                "python_version": os.getenv("PYTHON_VERSION", "3.9"),
                "api_port": os.getenv("API_PORT", "8000"),
                "port": os.getenv("PORT", "3000"),
                "startup_grace_period": is_startup,
                "database_url_type": os.getenv("DATABASE_URL", "").split("://")[0]
                if os.getenv("DATABASE_URL")
                else None,
                "redis_configured": bool(os.getenv("REDIS_URL")),
            },
        }

        logger.info(f"Health check completed. Status: {status}, Message: {status_message}")
        return health_status

    except Exception as e:
        error_msg = f"Error during health check: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "timestamp": datetime.now().isoformat(),
            "uptime": get_uptime(),
        }
