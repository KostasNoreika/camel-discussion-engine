"""
Logging configuration for CAMEL Discussion API
"""
from loguru import logger
import sys
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_format: str = "text"):
    """
    Configure logging for the application

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Format type (text or json)
    """
    # Remove default handler
    logger.remove()

    # Console handler
    if log_format == "json":
        logger.add(
            sys.stdout,
            serialize=True,
            level=log_level
        )
    else:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level=log_level,
            colorize=True
        )

    # File handler
    log_dir = Path("./data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_dir / "camel-api-{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        level=log_level
    )

    return logger
