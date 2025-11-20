"""
Logging utilities for PR Analyzer
"""

import logging
import sys
from typing import Optional


def setup_logger(config, name: str = "pr_analyzer") -> logging.Logger:
    """
    Setup and configure logger.
    
    Args:
        config: Configuration object
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Set level
    level_str = config.get('logging.level', 'INFO')
    level = getattr(logging, level_str.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Format
    formatter = logging.Formatter(
        config.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_file = config.get('logging.file', 'pr_analyzer.log')
    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not create file handler: {e}")
    
    return logger


def get_logger(name: str = "pr_analyzer") -> logging.Logger:
    """
    Get existing logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
