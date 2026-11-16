"""
FinGuard Health Check Route
"""

from fastapi import APIRouter
from backend.app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Returns local service health status."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": "localhost",
        "telemetry": "zero_external_transmission",
    }
