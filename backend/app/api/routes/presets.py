"""
FinGuard Anonymization Presets API Routes
Manages pre-configured and custom anonymization policies (CBJ strict, balanced, high utility).
"""

import json
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.db.database import DatabaseRepository

router = APIRouter(prefix="/presets", tags=["Presets"])


class PresetCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., max_length=500)
    rules: Dict[str, Any]


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def list_presets():
    """Lists built-in and user-defined anonymization presets."""
    return DatabaseRepository.list_presets()


@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_preset(request: PresetCreateRequest):
    """Creates a new reusable anonymization policy preset."""
    preset_id = request.id or f"preset_{uuid.uuid4().hex[:8]}"
    data = {
        "id": preset_id,
        "name": request.name,
        "description": request.description,
        "rules_json": json.dumps(request.rules),
        "is_system_preset": 0,
    }
    return DatabaseRepository.create_preset(data)
