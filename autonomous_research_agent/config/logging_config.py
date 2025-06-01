"""
Logging Configuration Module

This module configures the logging system for the application.
It provides a centralized configuration for consistent logging across all components.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path


def configure_logging(log_level=logging.INFO, log_dir="logs", log_filename="research_agent.log"):
    """
    Configure the logging system for the application.
    
    Args:
        log_level: The logging level to use
        log_dir: Directory to store log files
        log_filename: Name of the log file
        
    Returns:
        Logger instance
    """
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    log_file = log_path / log_filename
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove any existing handlers to avoid duplicates when reconfiguring
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # Create file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    # Add handlers to logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Create application logger
    logger = logging.getLogger('autonomous_research_agent')
    
    # Log startup message
    logger.info("Logging configured")
    
    return logger


def get_logger(name):
    """
    Get a logger for a specific module
    
    Args:
        name: Name of the module
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f'autonomous_research_agent.{name}')
