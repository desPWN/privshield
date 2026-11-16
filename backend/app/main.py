"""
FinGuard FastAPI Application Factory
Main entry point providing:
- Zero-PII logging configuration
- SQLite database initialization
- CORS middleware configuration for local React frontend
- Consolidated API routing under /api and /api/v1
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.core.logging_filter import setup_logging
from backend.app.db.database import init_db

# Configure Zero-PII Logging
setup_logging()
logger = logging.getLogger("finguard")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle hooks: initialize database and verify storage dirs."""
    logger.info("Initializing FinGuard application on localhost...")
    init_db()
    yield
    logger.info("FinGuard application shutdown.")


app = FastAPI(
    title="PrivShield API",
    description="Universal Privacy-Preserving Data Anonymization Engine",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(api_router, prefix="/api")
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
def root_health():
    """Root health and status endpoint."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": "localhost",
        "telemetry": "zero_external_transmission",
    }


if __name__ == "__main__":
    import uvicorn
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
