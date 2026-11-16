"""
PrivShield Sanitized Export API Routes
Provides endpoints for:
- Sanitized multi-format export (CSV with formula injection neutralization, XLSX, JSON)
- Pre-Export Privacy Verification Gateway enforcing privacy evaluation for Mode 2
- Executive ReportLab PDF privacy evaluation report download
"""

from fastapi import APIRouter, HTTPException, Response, status

from backend.app.db.database import DatabaseRepository
from backend.app.services.anonymization_service import AnonymizationService
from backend.app.services.export_service import export_dataset, verify_pre_export_privacy_gateway
from backend.app.services.pdf_service import generate_pdf_report

router = APIRouter(prefix="/runs", tags=["Export"])


@router.get("/{run_id}/export/{format}")
def export_anonymized_dataset(run_id: str, format: str):
    """
    Downloads anonymized dataset in CSV, XLSX, or JSON format.
    Enforces Pre-Export Privacy Verification Gateway for Mode 2.
    Applies formula injection neutralization to protect against spreadsheet DDE attacks.
    """
    fmt = format.lower().strip()
    if fmt not in ("csv", "xlsx", "excel", "json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format '{format}'. Supported formats: csv, xlsx, json.",
        )

    run = AnonymizationService.get_run(run_id)
    passed, reason = verify_pre_export_privacy_gateway(run)
    if not passed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pre-Export Privacy Verification Gateway rejected export: {reason}",
        )

    anon_df = AnonymizationService.get_run_df(run_id)
    content_bytes = export_dataset(anon_df, format=fmt)

    if fmt == "csv":
        media_type = "text/csv"
        filename = f"privshield_anonymized_{run_id}.csv"
    elif fmt in ("xlsx", "excel"):
        media_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename = f"privshield_anonymized_{run_id}.xlsx"
    elif fmt == "json":
        media_type = "application/json"
        filename = f"privshield_anonymized_{run_id}.json"
    else:
        media_type = "application/octet-stream"
        filename = f"privshield_anonymized_{run_id}.dat"

    return Response(
        content=content_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/{run_id}/report/pdf")
def download_pdf_report(run_id: str):
    """
    Generates and downloads publication-grade ReportLab executive PDF privacy evaluation report.
    Guarantees zero raw PII leakage and two-pass NumberedCanvas dynamic page numbering.
    """
    run = AnonymizationService.get_run(run_id)
    dataset_id = run["dataset_id"]
    dataset_meta = DatabaseRepository.get_dataset(dataset_id) or {}
    metrics = run.get("metrics") or {}

    pdf_bytes = generate_pdf_report(dataset_meta=dataset_meta, metrics=metrics)

    filename = f"privshield_privacy_report_{run_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
