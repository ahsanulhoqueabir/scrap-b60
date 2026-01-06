"""
Central logging configuration module
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from app.config import config


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Set up and configure logger with file and console handlers
    
    Args:
        name: Logger name (typically module name)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers if logger already configured
    if logger.handlers:
        return logger
    
    # Set log level
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # File handler with rotation (max 10MB, keep 5 backups)
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
