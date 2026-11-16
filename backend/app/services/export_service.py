"""
PrivShield Export Service & Pre-Export Privacy Verification Gateway
Provides secure export to CSV, Excel (XLSX), and JSON formats with formula injection neutralization
and pre-export privacy verification checks.
"""

import io
import json
from typing import Any, Tuple, Union
import pandas as pd
from backend.app.core.security import sanitize_csv_cell, sanitize_dataframe_for_export


def verify_pre_export_privacy_gateway(run_or_result: Any) -> Tuple[bool, str]:
    """
    Pre-export privacy verification gateway.
    For Mode 2 (Irreversible Anonymization), verifies that the anonymization run
    passed privacy evaluation (Strict K-anonymity invariant satisfied) before permitting export.
    """
    if run_or_result is None:
        return False, "Export blocked: Invalid or missing anonymization run metadata."

    if isinstance(run_or_result, dict):
        metrics = run_or_result.get("metrics") or run_or_result
        k_satisfied = bool(metrics.get("k_satisfied", False))
        mode = run_or_result.get("processing_mode") or (
            run_or_result.get("config", {}).get("processing_mode")
            if isinstance(run_or_result.get("config"), dict)
            else "irreversible_anonymization"
        )
    else:
        k_satisfied = bool(getattr(run_or_result, "k_satisfied", False))
        mode = getattr(run_or_result, "processing_mode", "irreversible_anonymization")

    if mode == "irreversible_anonymization" and not k_satisfied:
        return False, "Export blocked: Irreversible Anonymization (Mode 2) requires passing privacy evaluation (Strict K-anonymity invariant satisfied) before data release."

    return True, "Pre-export verification passed: Dataset certified safe for release."


def export_dataset(df: pd.DataFrame, format: str = "csv") -> bytes:
    """
    Exports a DataFrame into sanitized bytes stream in CSV, XLSX, or JSON format.
    Raises ValueError on unsupported formats.
    """
    fmt = format.lower().strip()
    if fmt == "csv":
        sanitized = sanitize_dataframe_for_export(df)
        csv_str = sanitized.to_csv(index=False)
        return csv_str.encode("utf-8")

    elif fmt in ("xlsx", "excel"):
        sanitized = sanitize_dataframe_for_export(df)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            sanitized.to_excel(writer, index=False, sheet_name="Anonymized Data")
        return buffer.getvalue()

    elif fmt == "json":
        json_str = df.to_json(orient="records", date_format="iso")
        return json_str.encode("utf-8")

    else:
        raise ValueError(f"Unsupported export format '{format}'. Supported formats: csv, xlsx, json.")


class ExportService:
    """Namespace providing static export and pre-export verification methods."""
    export_dataset = staticmethod(export_dataset)
    verify_pre_export_privacy_gateway = staticmethod(verify_pre_export_privacy_gateway)

