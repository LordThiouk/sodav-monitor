from typing import Dict, Optional
from datetime import datetime
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

def check_database_connection() -> Dict[str, bool]:
    """Vérifie la connexion à la base de données."""
    try:
        database_url = os.getenv("DATABASE_URL")
        logger.info(f"Checking database connection...")
        
        if not database_url:
            logger.error("DATABASE_URL not set")
            return {"connected": False, "error": "DATABASE_URL not set"}
        
        # Assurer que l'URL commence par postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
            logger.info("URL converted from postgres:// to postgresql://")
        
        logger.info("Creating database engine...")
        engine = create_engine(database_url)
        
        logger.info("Testing database connection...")
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
        import psutil
        logger.info("Checking system resources...")
        
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        logger.info(f"System resources - CPU: {cpu}%, Memory: {memory}%, Disk: {disk}%")
        
        return {
            "cpu_percent": cpu,
            "memory_percent": memory,
            "disk_percent": disk
        }
    except Exception as e:
        error_msg = f"Error checking system resources: {str(e)}"
        logger.error(error_msg)
        return {
            "cpu_percent": -1,
            "memory_percent": -1,
            "disk_percent": -1,
            "error": error_msg
        }

def get_system_health() -> Dict:
    """Obtient l'état de santé complet du système."""
    try:
        logger.info("Starting system health check...")
        
        db_status = check_database_connection()
        resources = check_system_resources()
        
        health_status = {
            "status": "healthy" if db_status["connected"] else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database": {
                "connected": db_status["connected"],
                "error": db_status["error"]
            },
            "system": resources,
            "environment": {
                "python_version": os.getenv("PYTHON_VERSION", "3.9"),
                "port": os.getenv("PORT", "8000")
            }
        }
        
        logger.info(f"Health check completed. Status: {health_status['status']}")
        return health_status
        
    except Exception as e:
        error_msg = f"Error during health check: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": error_msg
        } 