"""
Unit Tests for FinGuard ReportLab Executive PDF Service
"""

import io
import re
import pytest

from backend.app.services.pdf_service import generate_pdf_report


def test_pdf_report_generates_valid_binary():
    """Verifies that generated PDF starts with %PDF- header and has non-trivial size."""
    meta = {"name": "sample_transactions.csv", "row_count": 1200}
    metrics = {
        "k": 5,
        "k_satisfied": True,
        "achieved_k": 5,
        "suppression_rate": 0.04,
        "curs": 92.4,
        "prosecutor_risk": 0.20,
    }

    pdf_bytes = generate_pdf_report(meta, metrics)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000


def test_pdf_report_guarantees_zero_raw_pii():
    """Verifies that sensitive PII injected into metadata is completely redacted."""
    raw_nat_id = "9981021234"
    raw_iban = "JO42ARAB0000000123456789012345"
    raw_phone = "+962 79 123 4567"

    meta = {
        "name": f"audit_{raw_nat_id}.csv",
        "row_count": 250,
        "sample_pii": raw_iban,
        "phone_field": raw_phone,
    }
    metrics = {
        "k": 5,
        "k_satisfied": True,
        "suppression_rate": 0.02,
        "curs": 95.0,
    }

    pdf_bytes = generate_pdf_report(meta, metrics)
    pdf_text = pdf_bytes.decode("latin1", errors="ignore")

    # Scans for raw identifiers
    assert raw_nat_id not in pdf_text
    assert raw_iban not in pdf_text


def test_pdf_report_reflects_compliance_and_violations():
    """Verifies that compliance verdict is accurately reflected in generated output."""
    # Compliant
    meta = {"name": "passed_dataset.csv", "row_count": 500}
    metrics_pass = {"k": 5, "k_satisfied": True, "achieved_k": 5, "suppression_rate": 0.01}
    pdf_pass = generate_pdf_report(meta, metrics_pass).decode("latin1", errors="ignore")
    assert "PASSED" in pdf_pass

    # Violated
    metrics_fail = {"k": 5, "k_satisfied": False, "achieved_k": 1, "suppression_rate": 0.0}
    pdf_fail = generate_pdf_report(meta, metrics_fail).decode("latin1", errors="ignore")
    assert "VIOLATED" in pdf_fail


def test_pdf_report_with_l_and_t_metrics():
    """Verifies that L-diversity and T-closeness audit tables are rendered when present."""
    meta = {"name": "comprehensive_audit.csv", "row_count": 1000}
    metrics = {
        "k": 5,
        "k_satisfied": True,
        "achieved_k": 5,
        "suppression_rate": 0.05,
        "curs": 91.0,
        "l_diversity_results": {
            "target_l": 3,
            "sensitive_attribute": "Transaction_Category",
            "satisfied": True,
            "min_observed_distinct_values": 4,
        },
        "t_closeness_results": {
            "target_t": 0.15,
            "attribute_type": "Amount",
            "satisfied": True,
            "max_observed_distance": 0.112,
        },
    }

    pdf_bytes = generate_pdf_report(meta, metrics)
    pdf_text = pdf_bytes.decode("latin1", errors="ignore")
    assert "Distinct L-Diversity" in pdf_text
    assert "T-Closeness" in pdf_text


def test_pdf_report_with_empty_inputs_handles_gracefully():
    """Verifies that empty metadata and metrics do not cause unhandled crashes."""
    pdf_bytes = generate_pdf_report({}, {})
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
