"""
PrivShield Secure Recovery API Routes
Provides Mode 1 Reversible Pseudonymization endpoints:
- Authorized token lookup with admin passkey verification
- Full dataset restoration from encrypted storage
- Immutable audit trail queries
- Pseudonymization vault status queries
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from backend.app.db.database import DatabaseRepository
from backend.app.models.schemas import (
    DatasetRestoreRequest,
    RecoveryAuditLogItem,
    TokenLookupRequest,
    TokenLookupResponse,
)
from backend.app.services.recovery_service import RecoveryService

router = APIRouter(prefix="/recovery", tags=["Secure Recovery"])


@router.post("/lookup", response_model=TokenLookupResponse)
@router.post("/lookup-token", response_model=TokenLookupResponse)
def lookup_pseudonym_token(
    payload: TokenLookupRequest,
    request: Request,
) -> TokenLookupResponse:
    """
    Recovers the original sensitive value associated with a cryptographic pseudonym token.
    Requires administrator passkey verification and records an immutable audit log entry.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return RecoveryService.lookup_token(
        token=payload.token,
        passkey=payload.passkey,
        run_id=payload.run_id,
        column_name=payload.column_name,
        actor="admin",
        ip_address=client_ip,
        justification=payload.justification or "Authorized token recovery",
    )


@router.post("/restore")
@router.post("/restore-dataset")
def restore_encrypted_dataset(
    payload: DatasetRestoreRequest,
    request: Request,
) -> Response:
    """
    Decrypts and restores the original dataset from encrypted storage.
    Verifies administrator passkey and writes an immutable audit log.
    Returns the restored dataset file as a downloadable attachment.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    data_bytes = RecoveryService.restore_dataset(
        dataset_id=payload.dataset_id,
        passkey=payload.passkey,
        actor=payload.actor or "admin",
        ip_address=client_ip,
        justification=payload.justification or "Authorized full dataset restore",
    )

    dataset = DatabaseRepository.get_dataset(payload.dataset_id)
    dataset_name = dataset.get("name", "dataset") if dataset else "dataset"
    filename = f"restored_{payload.dataset_id[:8]}_{dataset_name.replace(' ', '_').lower()}.csv"

    return Response(
        content=data_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/audit-logs", response_model=List[RecoveryAuditLogItem])
def list_recovery_audit_logs(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of logs to return"),
) -> List[RecoveryAuditLogItem]:
    """Retrieves immutable audit log entries recording all recovery and token lookup operations."""
    return RecoveryService.get_audit_logs(limit=limit)


@router.get("/status/{run_id}")
def get_vault_status(run_id: str) -> Dict[str, Any]:
    """Retrieves token mapping count and encrypted vault state for a given anonymization run."""
    run = DatabaseRepository.get_anonymization_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anonymization run '{run_id}' not found.",
        )

    dataset_id = run["dataset_id"]
    dataset = DatabaseRepository.get_dataset(dataset_id)
    token_count = DatabaseRepository.count_token_mappings(dataset_id=dataset_id, run_id=run_id)

    return {
        "run_id": run_id,
        "dataset_id": dataset_id,
        "dataset_name": dataset.get("name") if dataset else "Unknown",
        "processing_mode": "reversible_pseudonymization" if token_count > 0 else "irreversible_anonymization",
        "is_reversible": token_count > 0,
        "token_mapping_count": token_count,
        "is_encrypted": bool(dataset.get("is_encrypted", 0)) if dataset else False,
    }

