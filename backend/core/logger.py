"""
Central logging configuration for the organizador backend.

Provides a configured logger instance named "organizador" that can be
imported across the backend modules.
"""

import logging
import sys
from typing import Final

# Logger configuration constants
LOGGER_NAME: Final = "organizador"
LOG_LEVEL: Final = logging.INFO
LOG_FORMAT: Final = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logger() -> logging.Logger:
    """
    Configure and return a logger instance.
    
    Returns:
        Configured logger with standard formatting and INFO level.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(LOG_LEVEL)
    
    # Avoid adding multiple handlers if logger is already configured
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(LOG_LEVEL)
        
        # Create formatter
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
    
    return logger


# Create and export the logger instance
logger = setup_logger()
