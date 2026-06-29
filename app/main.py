"""
Entry point for the FastAPI application.
Bootstraps core services, registers routers, and sets up exception handling protocols.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import get_settings
from app.core.logger import setup_logger, logger
from app.core.exception import AegisBaseException, global_exception_handler
from app.api.github_events import router as github_events_router

settings = get_settings()


os.makedirs("logs", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle events of the FastAPI application.
    Executes essential startup routines such as logger initialization, and handles graceful shutdown.
    """
    setup_logger()
    logger.info("Aegis Code Review Agent starting")
    logger.info(f"   Environment : {settings.app_env}")
    logger.info(f"   Model       : {settings.nvidia_model}")
    yield
    logger.info("Aegis Code Review Agent shutting down")


# Initialize the core FastAPI application instance.
app = FastAPI(
    title="Aegis Code Review",
    description="Multi-agent code review system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
)

app.add_exception_handler(AegisBaseException, global_exception_handler)

app.include_router(github_events_router, prefix="/api", tags=["Webhook"])


@app.get("/health")
async def health():
    """
    Health check endpoint for container orchestration and monitoring systems.
    
    Returns:
        dict: The operational status and environment metadata.
    """
    return {
        "status": "healthy",
        "env": settings.app_env,
        "model": settings.nvidia_model,
    }