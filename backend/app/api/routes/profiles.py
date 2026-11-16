"""
PrivShield Industry Profiles API Routes
Provides endpoints for:
- Listing pre-built industry profiles (Healthcare, Finance, Education, Government, HR, E-Commerce, Custom)
- Retrieving single profile details and suggested rules
- Matching and applying profiles to dataset schemas
"""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.models.schemas import IndustryProfile
from backend.app.services.profile_service import ProfileService
from backend.app.services.dataset_service import DatasetService

router = APIRouter(prefix="/profiles", tags=["Industry Profiles"])


class ApplyProfileRequest(BaseModel):
    columns: List[str] = Field(default_factory=list)
    dataset_id: str | None = None


@router.get("", response_model=List[IndustryProfile])
@router.get("/", response_model=List[IndustryProfile])
def list_profiles() -> List[IndustryProfile]:
    """Lists all available industry profiles with suggested classifications and privacy rules."""
    return ProfileService.list_profiles()


@router.get("/{profile_id}", response_model=IndustryProfile)
def get_profile(profile_id: str) -> IndustryProfile:
    """Retrieves a specific industry profile by its identifier."""
    profile = ProfileService.get_profile(profile_id) or ProfileService.get_profile(profile_id.lower().strip())
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Industry profile '{profile_id}' not found.",
        )
    return profile


@router.post("/{profile_id}/apply", response_model=Dict[str, Any])
def apply_profile(profile_id: str, request: ApplyProfileRequest) -> Dict[str, Any]:
    """
    Applies the industry profile rules against dataset columns,
    producing suggested masking rules, generalization levels, QIs, and sensitive attributes.
    """
    columns = list(request.columns)
    if request.dataset_id and not columns:
        meta = DatasetService.get_dataset(request.dataset_id)
        if meta and "columns" in meta:
            columns = meta["columns"]
        else:
            profiles = DatasetService.get_dataset_profiles(request.dataset_id)
            columns = [p.column_name for p in profiles]

    if not columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No columns provided or found for dataset to apply profile rules.",
        )

    return ProfileService.apply_profile_to_dataset(profile_id, columns)

