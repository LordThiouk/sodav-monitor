import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(app_name="sodav-monitor", log_level=logging.INFO):
    """
    Set up logging configuration for the application.
    
    Args:
        app_name (str): Name of the application for log file naming
        log_level (int): Logging level (default: logging.INFO)
    """
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set up file handler
    log_file = os.path.join(log_dir, f"{app_name}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    
    # Create formatters and add it to the handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove any existing handlers
    root_logger.handlers = []
    
    # Add the handlers to the logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger 