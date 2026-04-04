"""
Logging utilities using loguru
"""
from loguru import logger
from pathlib import Path
import sys

from config import settings


def setup_logger():
    """Configure loguru logger"""
    
    # Remove default handler
    logger.remove()
    
    # Add console handler with colors
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Add file handler
    log_path = Path(settings.LOGS_DIR) / "rag_system.log"
    logger.add(
        log_path,
        rotation="500 MB",
        retention="10 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )
    
    # Add error file handler
    error_log_path = Path(settings.LOGS_DIR) / "errors.log"
    logger.add(
        error_log_path,
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR"
    )
    
    logger.info("Logger configured successfully")


# Initialize logger on import
setup_logger()
