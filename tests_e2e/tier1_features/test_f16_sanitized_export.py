"""
tests_e2e/tier1_features/test_f16_sanitized_export.py
Feature 16: Multi-Format Sanitized Export with Formula Guard.
Validates neutralization of formula triggers (=, +, -, @, \\t, \\r) across CSV, XLSX, and JSON formats.
"""

import io
import json
import pandas as pd
import pytest
from tests_e2e.conftest import assert_formula_safe
from tests_e2e.test_contracts import get_export_dataset_fn, get_sanitize_csv_cell_fn


def test_sanitize_csv_cell_neutralizes_dangerous_prefixes():
    sanitize = get_sanitize_csv_cell_fn()
    dangerous_inputs = [
        "=cmd|'/C calc'!A0",
        "+12345678_not_a_number",
        "-2+3*4_formula",
        "@SUM(1+1)*cmd",
        "\tmalicious_tab",
        "\rreturn_payload"
    ]
    for inp in dangerous_inputs:
        sanitized = sanitize(inp)
        assert sanitized.startswith("'"), f"Failed to neutralize: {inp} -> {sanitized}"


def test_sanitize_csv_cell_preserves_legitimate_numbers():
    sanitize = get_sanitize_csv_cell_fn()
    legitimate_numbers = [
        "-250.75",
        "+1000",
        "0.00",
        "42",
        "-0.5"
    ]
    for num in legitimate_numbers:
        sanitized = sanitize(num)
        assert not sanitized.startswith("'"), f"Corrupted legitimate number: {num} -> {sanitized}"


def test_export_dataset_csv_guarantees_formula_safety(formula_injection_df: pd.DataFrame):
    export_fn = get_export_dataset_fn()
    csv_bytes = export_fn(formula_injection_df, format="csv")
    csv_text = csv_bytes.decode("utf-8")
    assert_formula_safe(csv_text)


def test_export_dataset_xlsx_generates_valid_workbook(employee_records_df: pd.DataFrame):
    export_fn = get_export_dataset_fn()
    xlsx_bytes = export_fn(employee_records_df.head(20), format="xlsx")
    assert xlsx_bytes.startswith(b"PK"), "XLSX export must begin with ZIP PK header"

    excel_file = io.BytesIO(xlsx_bytes)
    read_df = pd.read_excel(excel_file, engine="openpyxl")
    assert len(read_df) == 20
    assert "EmployeeID" in read_df.columns


def test_export_dataset_json_generates_valid_json(customer_database_df: pd.DataFrame):
    export_fn = get_export_dataset_fn()
    json_bytes = export_fn(customer_database_df.head(15), format="json")
    parsed = json.loads(json_bytes.decode("utf-8"))
    assert isinstance(parsed, list)
    assert len(parsed) == 15
    assert "CustomerID" in parsed[0]


def test_export_dataset_invalid_format_raises_error(single_record_df: pd.DataFrame):
    export_fn = get_export_dataset_fn()
    with pytest.raises(ValueError, match=r"Unsupported.*format"):
        export_fn(single_record_df, format="yaml")
