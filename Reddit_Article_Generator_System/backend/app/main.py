"""
Reddit Article Generator System - FastAPI Application
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import articles_router, images_router, doubts_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    settings = get_settings()

    # Create temp storage directory
    temp_path = Path(settings.temp_storage_path)
    temp_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Temp storage directory: {temp_path.absolute()}")

    logger.info("Reddit Article Generator System starting up...")
    logger.info(f"Backend URL: {settings.backend_url}")
    logger.info(f"Frontend URL: {settings.frontend_url}")

    yield

    logger.info("Reddit Article Generator System shutting down...")


# Create FastAPI application
app = FastAPI(
    title="Reddit Article Generator System",
    description="AI-powered GMAT educational article generation system",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(articles_router, prefix="/api/articles", tags=["Articles"])
app.include_router(images_router, prefix="/api/images", tags=["Images"])
app.include_router(doubts_router, prefix="/api/doubts", tags=["Doubts"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Reddit Article Generator System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
