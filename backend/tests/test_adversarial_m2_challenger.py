"""
PrivShield Milestone M2 Adversarial Test Suite - Challenger 2
Empirical verification and stress harness for:
1. Multi-Industry Demo Ingestion (POST /api/datasets/load-industry-demo/{industry})
2. Industry Profile Endpoints (GET /api/profiles and GET /api/profiles/{id})
3. ReportLab PDF Security & Format Integrity (GET /api/runs/{run_id}/report/pdf & generate_pdf_report)
"""

import os
import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import pandas as pd

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.db.database import DatabaseRepository, get_db
from backend.app.services.dataset_service import DatasetService
from backend.app.services.profile_service import ProfileService, PREBUILT_PROFILES
from backend.app.services.pdf_service import generate_pdf_report
import httpx

client = TestClient(app)

# ----------------------------------------------------------------------
# 1. Multi-Industry Demo Ingestion Adversarial Tests
# ----------------------------------------------------------------------

INVALID_INDUSTRY_DOMAINS = [
    "invalid_domain",
    "nonexistent_sector",
    "../traversal",
    "..%2Ftraversal",
    "..%2F..%2Fetc%2Fpasswd",
    "../../shadow",
    "sql'injection",
    "' OR '1'='1",
    "'; DROP TABLE datasets; --",
    "admin'--",
    "$(whoami)",
    "; calc.exe",
    "& dir",
    "`whoami`",
    " ",
    "   ",
    "%20",
    "%20%20%20",
    "%09%0D%0A",
    "\t\r\n",
    "<script>alert('xss')</script>",
    "healthcare/malicious",
    "finance%00nullbyte",
    "a" * 1000,
    "!@#$%^&*()_+",
    "hospital_fake",
    "banking_unsupported",
    "hr_illegal",
    "1234567890",
]


@pytest.mark.parametrize("bad_industry", INVALID_INDUSTRY_DOMAINS)
def test_load_industry_demo_invalid_domain_rejection(bad_industry: str):
    """
    Stress-test /api/datasets/load-industry-demo/{industry} with invalid, adversarial,
    and injection strings. Must return clean HTTP 4xx (400, 404, or 405) or client-side URL rejection,
    and NEVER crash with an unhandled 500 error.
    """
    try:
        response = client.post(f"/api/datasets/load-industry-demo/{bad_industry}")
    except (httpx.InvalidURL, ValueError):
        # Raw unprintable/control characters correctly rejected at HTTP protocol layer
        return
    except Exception as exc:
        pytest.fail(f"Client raised unhandled exception for input '{bad_industry}': {exc}")

    assert response.status_code in (400, 404, 405), (
        f"Expected clean HTTP 4xx rejection for bad industry '{bad_industry}', "
        f"got {response.status_code}: {response.text}"
    )

    if response.status_code == 400:
        body = response.json()
        assert "detail" in body
        assert "Unsupported industry" in body["detail"] or "Invalid" in body["detail"]


VALID_INDUSTRIES = ["healthcare", "finance", "education", "hr", "ecommerce", "government"]


@pytest.mark.parametrize("industry", VALID_INDUSTRIES)
def test_load_industry_demo_valid_instantiation_and_persistence(industry: str):
    """
    Verify that all 6 valid industries instantiate genuine 1,000-record datasets
    with masked previews and valid SQLite records.
    """
    response = client.post(f"/api/datasets/load-industry-demo/{industry}")
    assert response.status_code == 201, f"Failed for {industry}: {response.text}"
    data = response.json()

    # 1. Response Envelope
    dataset_id = data.get("dataset_id")
    assert dataset_id is not None
    assert data["row_count"] == 1000
    assert data["column_count"] >= 10
    assert len(data["columns"]) == data["column_count"]
    assert data["industry"] == industry
    assert len(data["preview"]) == 10

    # 2. Masked Preview Verification: Direct identifiers must not be in raw form
    preview = data["preview"]
    sample_row = preview[0]
    for col_name, val in sample_row.items():
        val_str = str(val)
        col_lower = col_name.lower()
        if any(id_key in col_lower for id_key in ("ssn", "national", "nat_id", "card", "iban", "mrn", "patientid", "accountid", "studentid", "employeeid", "customerid")):
            assert "[REDACTED]" in val_str or "*" in val_str or len(val_str) < 16, (
                f"Field {col_name} appears unmasked in preview: {val_str}"
            )

    # 3. SQLite Database Invariant Verification
    db_meta = DatabaseRepository.get_dataset(dataset_id)
    assert db_meta is not None
    assert db_meta["row_count"] == 1000
    assert db_meta["column_count"] == data["column_count"]
    assert db_meta["id"] == dataset_id

    # 4. Storage Disk Invariant Verification
    raw_path = Path(db_meta["raw_storage_path"])
    assert raw_path.exists(), f"Storage CSV does not exist at {raw_path}"
    df_disk = pd.read_csv(raw_path)
    assert len(df_disk) == 1000, f"Expected 1000 rows on disk, found {len(df_disk)}"
    assert list(df_disk.columns) == data["columns"]

    # 5. Column Profile Metadata Verification
    col_profiles = DatabaseRepository.get_column_metadata(dataset_id)
    assert len(col_profiles) == data["column_count"]
    has_direct_id = any(c.get("inferred_category") == "direct_identifier" for c in col_profiles)
    assert has_direct_id, f"Expected direct identifiers discovered in {industry} dataset"

    # 6. Audit Trail Logging Verification in SQLite
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs WHERE dataset_id = ? AND action = 'load_industry_demo'", (dataset_id,))
        matching_audit = cursor.fetchall()
    assert len(matching_audit) >= 1, "Audit record for load_industry_demo not found in SQLite audit_logs"



# ----------------------------------------------------------------------
# 2. Industry Profile Endpoints Adversarial Tests
# ----------------------------------------------------------------------

PROFILE_CASING_CASES = [
    ("healthcare", "hEaLtHcArE"),
    ("healthcare", "HEALTHCARE"),
    ("finance", "Finance"),
    ("finance", "FINANCE"),
    ("education", "EdUcAtIoN"),
    ("education", "EDUCATION"),
    ("government", "Government"),
    ("government", "GOVERNMENT"),
    ("hr", "Hr"),
    ("hr", "HR"),
    ("ecommerce", "ECommerce"),
    ("ecommerce", "ECOMMERCE"),
    ("custom", "Custom"),
    ("custom", "CUSTOM"),
]


@pytest.mark.parametrize("expected_id, query_id", PROFILE_CASING_CASES)
def test_profiles_get_casing_resilience(expected_id: str, query_id: str):
    """Verifies that GET /api/profiles/{id} is resilient to casing variations."""
    res = client.get(f"/api/profiles/{query_id}")
    assert res.status_code == 200, f"Failed for variant '{query_id}': {res.text}"
    data = res.json()
    assert data["id"] == expected_id


PROFILE_SPACED_CASES = [
    ("healthcare", " healthcare "),
    ("healthcare", "%20healthcare%20"),
    ("finance", " finance "),
    ("finance", "%20finance%20"),
    ("hr", " hr "),
    ("hr", "%20hr%20"),
]


@pytest.mark.parametrize("expected_id, query_id", PROFILE_SPACED_CASES)
def test_profiles_get_whitespace_resilience(expected_id: str, query_id: str):
    """Verifies that GET /api/profiles/{id} handles leading/trailing spaces gracefully."""
    res = client.get(f"/api/profiles/{query_id}")
    assert res.status_code == 200, f"Failed for spaced '{query_id}': {res.text}"
    assert res.json()["id"] == expected_id


NON_EXISTENT_PROFILES = [
    "nonexistent",
    "unknown_industry",
    "healthcare123",
    "health",
    "fin",
    "banking_fake",
    "sql'injection",
    "' OR '1'='1",
    "custom_extra",
    "12345",
]


@pytest.mark.parametrize("bad_id", NON_EXISTENT_PROFILES)
def test_profiles_get_nonexistent_returns_404(bad_id: str):
    """Verifies that non-existent profiles return clean 404 without crashing."""
    res = client.get(f"/api/profiles/{bad_id}")
    assert res.status_code == 404
    assert f"Industry profile '{bad_id}' not found." in res.json()["detail"]


def test_profiles_all_seven_builtins_schema_and_defaults():
    """
    Asserts all 7 pre-built profiles return valid suggested rules and default K/L/T values:
    Healthcare (K=5, L=3, T=0.15)
    Finance (K=5, L=3, T=0.15)
    Education (K=4, L=2, T=0.20)
    Government (K=5, L=3, T=0.15)
    HR (K=4, L=2, T=0.20)
    E-Commerce (K=3, L=2, T=0.25)
    Custom (K=3, L=None, T=None)
    """
    res = client.get("/api/profiles")
    assert res.status_code == 200
    profiles = res.json()
    assert len(profiles) == 7

    profile_map = {p["id"]: p for p in profiles}
    expected_expectations = {
        "healthcare": {"k": 5, "l": 3, "t": 0.15},
        "finance": {"k": 5, "l": 3, "t": 0.15},
        "education": {"k": 4, "l": 2, "t": 0.20},
        "government": {"k": 5, "l": 3, "t": 0.15},
        "hr": {"k": 4, "l": 2, "t": 0.20},
        "ecommerce": {"k": 3, "l": 2, "t": 0.25},
        "custom": {"k": 3, "l": None, "t": None},
    }

    for pid, expected in expected_expectations.items():
        assert pid in profile_map, f"Missing profile '{pid}'"
        prof = profile_map[pid]
        rules = prof.get("suggested_rules", {})
        assert rules.get("k_metric") == expected["k"], f"K metric mismatch for {pid}"
        assert rules.get("l_metric") == expected["l"], f"L metric mismatch for {pid}"
        assert rules.get("t_metric") == expected["t"], f"T metric mismatch for {pid}"

        # Invariant checks for rules structure
        assert isinstance(rules.get("masking_rules"), dict)
        assert isinstance(rules.get("generalization_levels"), dict)
        assert isinstance(rules.get("direct_identifiers"), list)
        assert isinstance(rules.get("quasi_identifiers"), list)
        assert isinstance(rules.get("sensitive_attributes"), list)
        assert rules.get("suppression_strategy") in ("record", "cell")
        assert 0.0 < rules.get("max_suppression_pct") <= 1.0


# ----------------------------------------------------------------------
# 3. ReportLab PDF Security & Format Integrity Tests
# ----------------------------------------------------------------------

RAW_PII_PATTERNS = [
    # Formatted or unformatted credit cards (16 digits or 4x4)
    re.compile(rb"\b(?:\d{4}[ -]){3}\d{4}\b|\b(?:4\d{15}|5[1-5]\d{14}|3[47]\d{13})\b"),
    # International & Jordanian IBANs
    re.compile(rb"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
    # US SSN (XXX-XX-XXXX)
    re.compile(rb"\b\d{3}-\d{2}-\d{4}\b"),
    # 10-digit Jordanian National IDs (starting with 9)
    re.compile(rb"\b9\d{9}\b"),
]


@pytest.mark.parametrize("industry", VALID_INDUSTRIES)
def test_pdf_report_binary_integrity_and_zero_pii_across_all_industries(industry: str):
    """
    Generates PDF reports across all industry domains with synthetic PII datasets.
    Scans binary output stream and asserts:
    1. Starts with '%PDF-'
    2. Valid xref table
    3. Ends with '%%EOF'
    4. Zero leakage of unmasked credit cards, IBANs, SSNs, and national IDs in content stream.
    """
    # 1. Load Industry Demo
    load_res = client.post(f"/api/datasets/load-industry-demo/{industry}")
    assert load_res.status_code == 201
    dataset_id = load_res.json()["dataset_id"]
    df_raw = DatasetService.get_dataset_df(dataset_id)

    # Collect known raw PII values from the dataset to test for direct literal leakage
    pii_terms = ("ssn", "nat", "card", "iban", "phone", "mail", "pass", "name", "address")
    pii_columns = [c for c in df_raw.columns if any(t in c.lower() for t in pii_terms)]
    raw_pii_strings = set()
    for col in pii_columns:
        for val in df_raw[col].dropna().astype(str).unique()[:20]:
            if len(val) >= 7 and not val.replace(".", "").isdigit():
                raw_pii_strings.add(val)

    # 2. Execute Anonymization Run
    cols = list(df_raw.columns)
    qis = [c for c in cols if c in ("Age", "Gender", "City", "Municipality", "CustomerAge", "AgeGroup", "Department")]
    sens = [c for c in cols if c in ("DiagnosisCode", "TransactionAmount", "GPA", "BaseSalary", "AnnualIncome", "Taxable_Income")]
    if not qis:
        qis = [cols[0]]
    if not sens:
        sens = [cols[1]]

    anon_res = client.post(f"/api/datasets/{dataset_id}/anonymize", json={
        "processing_mode": "irreversible_anonymization",
        "quasi_identifiers": qis[:2],
        "sensitive_attributes": sens[:1],
        "k_metric": 3,
    })
    assert anon_res.status_code == 200, f"Anonymize failed: {anon_res.text}"
    run_id = anon_res.json()["run_id"]

    # 3. Retrieve PDF via Endpoint
    pdf_res = client.get(f"/api/runs/{run_id}/report/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    pdf_bytes = pdf_res.content

    # 4. Stream Format Validity
    assert pdf_bytes.startswith(b"%PDF-"), "PDF stream does not start with %PDF-"
    assert b"xref" in pdf_bytes, "PDF stream does not contain xref table"
    assert pdf_bytes.rstrip().endswith(b"%%EOF"), "PDF stream does not end with %%EOF"

    # 5. Content Stream Extraction (exclude standard xref table which contains 10-digit byte offsets)
    xref_idx = pdf_bytes.find(b"xref")
    content_stream = pdf_bytes[:xref_idx]

    # 6. Regex Scan for Unmasked PII in Content Stream
    for pattern in RAW_PII_PATTERNS:
        matches = pattern.findall(content_stream)
        assert len(matches) == 0, (
            f"PII Leakage detected in {industry} PDF report! Pattern {pattern.pattern} matched: {matches}"
        )

    # 7. Exact String Matching for Dataset Identifiers
    for raw_val in raw_pii_strings:
        encoded = raw_val.encode("latin1", errors="ignore")
        assert encoded not in content_stream, (
            f"Literal raw PII value '{raw_val}' leaked into {industry} PDF binary content stream!"
        )


def test_pdf_report_adversarial_metadata_pii_injection():
    """
    Attempts to inject raw PII directly into report metadata (name, industry, attributes)
    and verifies that sanitize_report_text and RedactingFilter prevent raw PII leakage.
    """
    card_sample = "4123 9999 8888 7777"
    iban_sample = "JO94ARAB1234567890123456789012"
    natid_sample = "9988776655"
    email_sample = "adversary_target@leakage.test"

    adversarial_meta = {
        "name": f"Hacked Dataset {card_sample} {iban_sample} {natid_sample} {email_sample}",
        "industry": "Healthcare",
        "row_count": 500,
    }
    adversarial_metrics = {
        "k": 5,
        "k_satisfied": True,
        "achieved_k": 5,
        "curs": 91.0,
    }

    pdf_bytes = generate_pdf_report(dataset_meta=adversarial_meta, metrics=adversarial_metrics)

    # Stream format validity
    assert pdf_bytes.startswith(b"%PDF-")
    assert pdf_bytes.rstrip().endswith(b"%%EOF")
    assert b"xref" in pdf_bytes

    # Assert raw card, iban, national id, and email do NOT appear in the PDF
    assert card_sample.encode("latin1") not in pdf_bytes
    assert iban_sample.encode("latin1") not in pdf_bytes
    assert natid_sample.encode("latin1") not in pdf_bytes
    assert email_sample.encode("latin1") not in pdf_bytes

    # Assert redaction token appears
    assert b"[REDACTED_PII]" in pdf_bytes
