"""
PrivShield Consolidated API Router
Aggregates datasets, runs, export, presets, profiles, recovery, and health check routes.
"""

from fastapi import APIRouter

from backend.app.api.routes.anonymization import router as anonymization_router
from backend.app.api.routes.datasets import router as datasets_router
from backend.app.api.routes.export import router as export_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.presets import router as presets_router
from backend.app.api.routes.profiles import router as profiles_router
from backend.app.api.routes.recovery import router as recovery_router

api_router = APIRouter()

api_router.include_router(datasets_router)
api_router.include_router(anonymization_router)
api_router.include_router(export_router)
api_router.include_router(presets_router)
api_router.include_router(profiles_router)
api_router.include_router(recovery_router)
api_router.include_router(health_router)

