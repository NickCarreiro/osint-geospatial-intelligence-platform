"""API endpoints for the OSINT platform."""
from app.api.unified import router as unified_router
from app.api.health import router as health_router

__all__ = ["unified_router", "health_router"]