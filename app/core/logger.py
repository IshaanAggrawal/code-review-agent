"""
Application logging configuration.
Initializes the Loguru logger with structured formatting for both console output
and rotating file storage.
"""
import sys
from loguru import logger
from app.core.config import get_settings

settings = get_settings()


def setup_logger() -> None:
    """
    Bootstraps the logging infrastructure.
    Configures standard output and file-based log sinks with distinct formatting
    and retention policies tailored for the deployment environment.
    """
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=settings.is_development,
    )

    logger.add(
        "logs/pr_review_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="DEBUG",
        rotation="00:00",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=False,
    )

    logger.info(f"Logger initialized | env={settings.app_env} | level={settings.log_level}")


__all__ = ["logger", "setup_logger"]