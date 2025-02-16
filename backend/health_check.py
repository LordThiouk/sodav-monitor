from typing import Dict, Optional
from datetime import datetime
import psycopg2
import os
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

def check_database_connection() -> Dict[str, bool]:
    """Vérifie la connexion à la base de données."""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return {"connected": False, "error": "DATABASE_URL not set"}
        
        engine = create_engine(database_url)
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        return {"connected": True, "error": None}
    except SQLAlchemyError as e:
        return {"connected": False, "error": str(e)}

def check_system_resources() -> Dict[str, float]:
    """Vérifie les ressources système."""
    import psutil
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent
    }

def get_system_health() -> Dict:
    """Obtient l'état de santé complet du système."""
    db_status = check_database_connection()
    resources = check_system_resources()
    
    return {
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