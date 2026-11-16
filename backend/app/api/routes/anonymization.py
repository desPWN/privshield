"""
PrivShield Anonymization Runs API Routes
Endpoints for:
- Retrieving run execution status and summary
- Full privacy risk & CURS utility analytics (for Recharts)
- Paginated side-by-side comparative diff
"""

from fastapi import APIRouter, Query

from backend.app.services.anonymization_service import AnonymizationService
from backend.app.api.routes.export import (
    export_anonymized_dataset,
    download_pdf_report,
)

router = APIRouter(prefix="/runs", tags=["Runs"])


@router.get("/{run_id}")
def get_run(run_id: str):
    """Retrieves anonymization run execution record."""
    return AnonymizationService.get_run(run_id)


@router.get("/{run_id}/analytics")
def get_run_analytics(run_id: str):
    """Retrieves full privacy risk, equivalence class histogram, and CURS utility metrics."""
    return AnonymizationService.get_run_analytics(run_id)


@router.get("/{run_id}/diff")
def get_run_diff(
    run_id: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(50, ge=1, le=100, description="Records per page"),
):
    """Returns side-by-side comparison between original and anonymized records."""
    return AnonymizationService.get_run_diff(run_id=run_id, page=page, size=size)

