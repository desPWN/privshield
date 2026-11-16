"""
FinGuard Security & Sanitization Utilities
Includes path traversal guards and CSV formula injection neutralization.
"""

from pathlib import Path
import re
from typing import Any
from fastapi import HTTPException, status
import pandas as pd

DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
UUID_PATTERN = re.compile(
    r"^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$",
    re.IGNORECASE,
)
SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")


def validate_uuid_id(entity_id: str) -> str:
    """Validate UUID format to prevent path traversal injection."""
    if not isinstance(entity_id, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identifier must be a string.",
        )
    clean_id = entity_id.strip()
    if not (UUID_PATTERN.match(clean_id) or SAFE_ID_PATTERN.match(clean_id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entity identifier format.",
        )
    return clean_id


def resolve_safe_path(base_dir: Path, target_subpath: str) -> Path:
    """Ensure resolved file path remains strictly inside the intended directory."""
    base_resolved = base_dir.resolve()
    target_resolved = (base_dir / target_subpath).resolve()
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Path traversal attempt detected.",
        )
    return target_resolved


def sanitize_csv_cell(val: Any) -> Any:
    """
    Neutralize spreadsheet formula injection on cell values.
    Dangerous prefixes (=, +, -, @, \\t, \\r) are escaped with a leading single quote (')
    while strictly preserving legitimate numbers (e.g. -142.50, +100).
    """
    if val is None:
        return val
    # If already a number type, keep as is
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return val

    s = str(val)
    if not s:
        return s

    if s[0] in DANGEROUS_PREFIXES:
        if s[0] in ("+", "-"):
            try:
                float(s)
                return val  # Legitimate number
            except ValueError:
                pass
        return "'" + s
    return val


sanitize_cell_value = sanitize_csv_cell


def sanitize_dataframe_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """Return a sanitized copy of the dataframe safe for CSV/XLSX export."""
    sanitized_df = df.copy()
    for col in sanitized_df.columns:
        sanitized_df[col] = sanitized_df[col].apply(sanitize_csv_cell)
    sanitized_df.columns = [str(sanitize_csv_cell(c)) for c in sanitized_df.columns]
    return sanitized_df
