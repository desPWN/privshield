"""
PrivShield Dataset Management API Routes
Endpoints for:
- Uploading CSV/XLSX/JSON files
- Listing and inspecting datasets
- Masked paginated previews
- Loading multi-industry demonstration datasets
- Loading Jordanian demonstration dataset
- Sensitive data discovery and classification overrides
- Launching anonymization pipelines
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from backend.app.db.database import DatabaseRepository
from backend.app.models.schemas import (
    AnonymizationConfig,
    ColumnOverrideRequest,
    ColumnProfile,
)
from backend.app.services.anonymization_service import AnonymizationService
from backend.app.services.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
):
    """Uploads a local dataset (CSV, XLSX, JSON) with validation and sensitive data discovery."""
    return DatasetService.upload_dataset(file=file, custom_name=name)


@router.post("/load-demo", status_code=status.HTTP_201_CREATED)
def load_demo_dataset():
    """Loads the built-in synthetic Jordanian financial transaction demonstration dataset."""
    return DatasetService.load_demo_dataset()


@router.post("/load-industry-demo/{industry}", status_code=status.HTTP_201_CREATED)
def load_industry_demo(industry: str):
    """Loads a synthetic industry demonstration dataset (healthcare, finance, education, hr, ecommerce, government)."""
    return DatasetService.load_industry_demo(industry)


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def list_datasets():
    """Lists all registered datasets stored locally."""
    return DatabaseRepository.list_datasets()


@router.get("/{id}")
def get_dataset(id: str):
    """Retrieves dataset schema and metadata."""
    meta = DatabaseRepository.get_dataset(id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{id}' not found.",
        )
    return meta


@router.get("/{id}/preview")
def get_dataset_preview(
    id: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Records per page"),
    mask_sensitive: bool = Query(True, description="Whether to mask sensitive raw values"),
):
    """Returns a paginated preview with sensitive identifiers masked."""
    return DatasetService.get_dataset_preview(
        dataset_id=id, page=page, size=size, mask_sensitive=mask_sensitive
    )


@router.get("/{id}/discover")
def discover_dataset_columns(id: str):
    """Executes sensitive data discovery and returns classified column profiles."""
    profiles = DatasetService.get_dataset_profiles(id)
    return {
        "dataset_id": id,
        "profiles": [p.model_dump() for p in profiles],
    }


@router.get("/{id}/latest-run")
def get_latest_dataset_run(id: str):
    """Retrieves the most recent completed anonymization run analytics for this dataset."""
    run = DatabaseRepository.get_latest_run_for_dataset(id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed anonymization runs found for dataset '{id}'.",
        )
    return AnonymizationService.get_run_analytics(run["id"])


@router.post("/{id}/overrides")
def update_column_overrides(id: str, request: ColumnOverrideRequest):
    """Updates user classification overrides for dataset columns."""
    updated = DatasetService.update_overrides(id, request.overrides)
    return {
        "dataset_id": id,
        "profiles": [p.model_dump() for p in updated],
        "message": f"Successfully updated {len(request.overrides)} column overrides.",
    }


@router.post("/{id}/anonymize")
def anonymize_dataset(id: str, config: AnonymizationConfig):
    """
    Executes full de-identification pipeline:
    - Direct identifier masking
    - Generalization hierarchies
    - Strict K-Anonymity with deterministic suppression
    - Distinct L-Diversity and T-Closeness audits
    - Re-identification risk and CURS utility metrics
    """
    return AnonymizationService.execute_anonymization(dataset_id=id, config=config)


@router.delete("/{id}")
def delete_dataset(id: str):
    """Deletes dataset record from SQLite and raw storage."""
    deleted = DatabaseRepository.delete_dataset(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{id}' not found.",
        )
    DatabaseRepository.log_audit("delete_dataset", dataset_id=id)
    return {"success": True, "dataset_id": id, "message": "Dataset marked as deleted."}
