"""Main FastAPI application for the OSINT platform."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api import unified_router, health_router
from app.cache import cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting OSINT Geospatial Intelligence Platform")
    logger.info(f"API will be available at http://{settings.api_host}:{settings.api_port}")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await cache.close()


# Create FastAPI app
app = FastAPI(
    title="OSINT Geospatial Intelligence Platform",
    description="Unified platform for aggregating and visualizing multiple OSINT data sources",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(unified_router)
app.include_router(health_router)

# Mount static files for frontend
try:
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
    logger.info("Frontend mounted at /")
except Exception as e:
    logger.warning(f"Could not mount frontend: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "OSINT Geospatial Intelligence Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/unified",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )