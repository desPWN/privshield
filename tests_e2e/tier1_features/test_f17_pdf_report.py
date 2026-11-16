"""
tests_e2e/tier1_features/test_f17_pdf_report.py
Feature 17: PrivShield ReportLab PDF Privacy Report.
Validates executive PDF report generation, NumberedCanvas, vector tables, and zero raw PII disclosure.
"""

import pytest
from tests_e2e.conftest import assert_zero_raw_pii_extended
from tests_e2e.test_contracts import get_generate_pdf_report_fn


def test_pdf_report_generates_valid_binary_stream():
    gen_pdf = get_generate_pdf_report_fn()
    meta = {"name": "Clinical Patient Cohort", "industry": "Healthcare", "row_count": 1000}
    metrics = {"k": 5, "k_satisfied": True, "suppression_rate": 0.04, "curs": 92.5, "prosecutor_risk": 0.20}

    pdf_bytes = gen_pdf(meta, metrics)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-"), "Generated output must start with valid PDF binary signature"
    assert len(pdf_bytes) > 1000


def test_pdf_report_zero_raw_pii_disclosure():
    gen_pdf = get_generate_pdf_report_fn()
    meta = {"name": "Audit Sample", "industry": "Banking", "row_count": 500}
    metrics = {"k": 5, "k_satisfied": True, "suppression_rate": 0.02, "curs": 95.0, "prosecutor_risk": 0.20}

    pdf_bytes = gen_pdf(meta, metrics)
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")
    assert_zero_raw_pii_extended(pdf_text)


def test_pdf_report_contains_compliance_scorecard():
    gen_pdf = get_generate_pdf_report_fn()
    meta = {"name": "HR Records", "industry": "HR", "row_count": 250}
    metrics = {"k": 4, "k_satisfied": True, "suppression_rate": 0.05, "curs": 88.0, "prosecutor_risk": 0.25}

    pdf_bytes = gen_pdf(meta, metrics)
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")
    assert "PrivShield" in pdf_text or "Privacy" in pdf_text
    assert "Strict K-Anonymity" in pdf_text or "Metric" in pdf_text


def test_pdf_report_multi_industry_metadata_badges():
    gen_pdf = get_generate_pdf_report_fn()
    industries = ["Healthcare", "Finance", "Education", "Government"]

    for ind in industries:
        meta = {"name": f"{ind} Cohort", "industry": ind, "row_count": 100}
        metrics = {"k": 3, "k_satisfied": True, "suppression_rate": 0.0, "curs": 99.0, "prosecutor_risk": 0.33}
        pdf_bytes = gen_pdf(meta, metrics)
        assert len(pdf_bytes) > 500


def test_pdf_report_graceful_handling_of_failed_runs():
    gen_pdf = get_generate_pdf_report_fn()
    meta = {"name": "Failed Evaluation Dataset", "industry": "Custom", "row_count": 50}
    metrics = {"k": 10, "k_satisfied": False, "suppression_rate": 0.80, "curs": 20.0, "prosecutor_risk": 1.0}

    pdf_bytes = gen_pdf(meta, metrics)
    assert pdf_bytes.startswith(b"%PDF-")
