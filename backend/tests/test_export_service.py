"""
Unit Tests for FinGuard Export Service & CSV Formula Injection Guard
"""

import io
import json
import openpyxl
import pandas as pd
import pytest

from backend.app.core.security import sanitize_csv_cell, sanitize_dataframe_for_export
from backend.app.services.export_service import export_dataset


@pytest.fixture
def sample_test_df():
    """Generates test dataframe containing both standard values and malicious formula triggers."""
    return pd.DataFrame({
        "Customer_Name": ["Ahmad Tariq", "=cmd|' /C calc'!A0", "@SUM(1+1)*calc", "\tTabsMalicious"],
        "City": ["Amman", "Zarqa", "Irbid", "\rCarriageReturn"],
        "Amount": [-142.50, 250.00, +100.0, 0.0],
        "Formula_Col": ["=2+5", "-50.25", "+PositiveNumber", "@alert('xss')"],
    })


def test_sanitize_csv_cell_escapes_dangerous_prefixes():
    """Verifies that cells starting with =, +, -, @, \\t, \\r are escaped if not numbers."""
    dangerous = [
        "=cmd|' /C calc'!A0",
        "@SUM(1+1)*cmd",
        "\tcalc.exe",
        "\rtest_payload",
        "=2+5",
        "@alert('xss')",
        "+cmd.exe",
        "-malicious_text",
    ]
    for payload in dangerous:
        sanitized = sanitize_csv_cell(payload)
        assert str(sanitized).startswith("'"), f"Failed to escape dangerous payload: {payload}"


def test_sanitize_csv_cell_preserves_legitimate_numbers():
    """Verifies that legitimate financial numbers (e.g. negative balances) are NOT escaped."""
    numbers = [-142.50, -50, "-50.25", "+100", 0, 75.50, 1000]
    for num in numbers:
        sanitized = sanitize_csv_cell(num)
        assert not str(sanitized).startswith("'"), f"Incorrectly escaped legitimate number: {num}"


def test_export_dataset_csv_produces_sanitized_output(sample_test_df):
    """Verifies CSV export contains escaped formulas and preserves legitimate numbers."""
    csv_bytes = export_dataset(sample_test_df, format="csv")
    assert isinstance(csv_bytes, bytes)
    csv_text = csv_bytes.decode("utf-8")

    # Verify malicious cells are escaped with leading single quote
    assert "'=cmd|' /C calc'!A0" in csv_text
    assert "'@SUM(1+1)*calc" in csv_text
    assert "'=2+5" in csv_text

    # Verify numbers are intact
    assert "-142.5" in csv_text or "-142.50" in csv_text


def test_export_dataset_xlsx_creates_valid_workbook(sample_test_df):
    """Verifies XLSX export creates valid OpenPyXL workbook with matching rows."""
    xlsx_bytes = export_dataset(sample_test_df, format="xlsx")
    assert isinstance(xlsx_bytes, bytes)

    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active
    assert ws.title == "Anonymized Data"
    assert ws.max_row == len(sample_test_df) + 1  # Header + 4 rows
    assert ws.max_column == len(sample_test_df.columns)


def test_export_dataset_json_creates_valid_json_array(sample_test_df):
    """Verifies JSON export creates valid records JSON array."""
    json_bytes = export_dataset(sample_test_df, format="json")
    assert isinstance(json_bytes, bytes)

    records = json.loads(json_bytes.decode("utf-8"))
    assert isinstance(records, list)
    assert len(records) == len(sample_test_df)
    assert records[0]["Customer_Name"] == "Ahmad Tariq"
    assert records[0]["City"] == "Amman"


def test_export_dataset_invalid_format_raises_value_error(sample_test_df):
    """Verifies that requesting unsupported format raises ValueError."""
    with pytest.raises(ValueError):
        export_dataset(sample_test_df, format="pdf_archive_zip")
