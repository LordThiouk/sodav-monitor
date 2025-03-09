import logging
import os
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
import json
from datetime import datetime
from backend.config import PATHS
from typing import Dict, Any, Optional

# Définir les catégories de logs
LOG_CATEGORIES = [
    "DETECTION",
    "AUDIO_PROCESSOR",
    "STREAM",
    "TRACK_MANAGER",
    "MUSICBRAINZ",
    "AUDD",
    "ACOUSTID",
    "GENERAL"
]

class CategoryFilter(logging.Filter):
    """Filtre pour sélectionner les logs d'une catégorie spécifique."""
    
    def __init__(self, category):
        super().__init__()
        self.category = f"[{category}]"
    
    def filter(self, record):
        if not hasattr(record, 'msg'):
            return False
        return self.category in record.msg

def log_with_category(logger: logging.Logger, category: str, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
    """
    Enregistre un message avec une catégorie spécifique.
    
    Args:
        logger: Logger à utiliser
        category: Catégorie du log (doit être dans LOG_CATEGORIES)
        level: Niveau de log ('debug', 'info', 'warning', 'error', 'critical')
        message: Message à enregistrer
        extra: Données supplémentaires à inclure dans le log
    """
    if category not in LOG_CATEGORIES:
        category = "GENERAL"
    
    # Préfixer le message avec la catégorie
    categorized_message = f"[{category}] {message}"
    
    # Déterminer la méthode de log à utiliser
    log_method = getattr(logger, level.lower(), logger.info)
    
    # Enregistrer le message
    if extra:
        log_method(categorized_message, extra=extra)
    else:
        log_method(categorized_message)

def setup_logging(name: str = None):
    """Configure logging with rotating file handler and console output"""
    # Use LOG_DIR from config
    log_dir = Path(PATHS["LOG_DIR"])
    
    # Configure logging
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Create formatters with detailed information
    file_formatter = logging.Formatter(
        '[%(asctime)s.%(msecs)03d] %(levelname)s [%(name)s:%(lineno)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create module-specific log directory
    module_dir = log_dir / (name.split('.')[0] if name else 'app')
    module_dir.mkdir(parents=True, exist_ok=True)
    
    # Create categories directory
    categories_dir = log_dir / 'categories'
    categories_dir.mkdir(parents=True, exist_ok=True)
    
    # Create and configure file handler with daily rotation
    log_file = module_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding='utf-8',
        delay=False
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Create JSON handler for structured logging
    json_log_file = module_dir / f"{datetime.now().strftime('%Y-%m-%d')}_structured.json"
    json_handler = RotatingFileHandler(
        json_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    json_handler.setLevel(logging.INFO)
    
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            dt = datetime.fromtimestamp(record.created)
            log_data = {
                'timestamp': dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                'name': record.name,
                'level': record.levelname,
                'message': record.getMessage(),
                'process': record.process,
                'thread': record.thread,
                'line': record.lineno,
                'function': record.funcName
            }
            
            # Add extra fields if they exist
            if hasattr(record, 'station'):
                log_data['station'] = record.station
            if hasattr(record, 'detection_data'):
                log_data['detection'] = record.detection_data
            if hasattr(record, 'duration'):
                log_data['duration'] = record.duration
            if hasattr(record, 'error'):
                log_data['error'] = record.error
                
            # Extract category from message if present
            for category in LOG_CATEGORIES:
                if f"[{category}]" in record.getMessage():
                    log_data['category'] = category
                    break
                
            # Add stack trace for errors
            if record.exc_info:
                log_data['exc_info'] = self.formatException(record.exc_info)
                
            return json.dumps(log_data, ensure_ascii=False)
    
    json_handler.setFormatter(JsonFormatter())
    
    # Create and configure console handler with UTF-8 encoding
    if sys.platform == 'win32':
        # On Windows, use sys.stdout with UTF-8 encoding
        sys.stdout.reconfigure(encoding='utf-8')
        console_handler = logging.StreamHandler(sys.stdout)
    else:
        console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Create category-specific handlers
    category_handlers = {}
    for category in LOG_CATEGORIES:
        category_log_file = categories_dir / f"{category.lower()}.log"
        handler = RotatingFileHandler(
            category_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(file_formatter)
        
        # Add category filter
        category_filter = CategoryFilter(category)
        handler.addFilter(category_filter)
        
        category_handlers[category] = handler
    
    # Remove any existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(json_handler)
    logger.addHandler(console_handler)
    
    # Add category handlers
    for handler in category_handlers.values():
        logger.addHandler(handler)
    
    return logger 