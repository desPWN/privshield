"""
PrivShield Milestone M4 Phase 2 - Adversarial Verification Suite
Challenger 2: White-box stress testing across API security boundaries,
Pre-Export Privacy Verification Gateway, Cryptographic Recovery Vault Tampering,
Passkey Authentication & Audit Logging, and Formula Injection Sanitization.
"""

import io
import os
import re
import uuid
import pytest
from fastapi.testclient import TestClient
import pandas as pd
from cryptography.exceptions import InvalidTag
import openpyxl

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.security import sanitize_csv_cell, sanitize_dataframe_for_export
from backend.app.db.database import DatabaseRepository, get_db
from backend.app.services.anonymization_service import AnonymizationService
from backend.app.services.dataset_service import DatasetService
from backend.app.services.encryption_service import (
    EncryptionService,
    _DEFAULT_RECOVERY_PASSKEY,
)
from backend.app.services.export_service import (
    export_dataset,
    verify_pre_export_privacy_gateway,
)
from backend.app.services.recovery_service import RecoveryService

client = TestClient(app)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(scope="module")
def sample_dataset():
    """Uploads a test dataset for anonymization and recovery testing."""
    csv_data = (
        "PatientID,FullName,Age,Gender,Diagnosis,TotalCharges\n"
        "P101,John Doe,45,M,E11.9,1200.50\n"
        "P102,Jane Smith,45,F,I10,2300.00\n"
        "P103,Bob Johnson,45,M,E11.9,1150.75\n"
        "P104,Alice Brown,50,F,I10,3400.25\n"
        "P105,Charlie White,50,M,E11.9,1500.00\n"
        "P106,Diana Prince,50,F,I10,2100.50\n"
    )
    files = {"file": ("patients_sample.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    resp = client.post("/api/datasets/upload", files=files, data={"name": "M4 Challenger Test Dataset"})
    assert resp.status_code == 201, f"Failed to upload test dataset: {resp.text}"
    return resp.json()["dataset_id"]


@pytest.fixture(scope="module")
def compliant_mode2_run(sample_dataset):
    """Generates a compliant Mode 2 run where k_satisfied is True."""
    payload = {
        "processing_mode": "irreversible_anonymization",
        "quasi_identifiers": ["Age"],
        "sensitive_attributes": ["Diagnosis"],
        "k_metric": 3,
        "suppression_strategy": "record",
        "max_suppression_pct": 0.50,
    }
    resp = client.post(f"/api/datasets/{sample_dataset}/anonymize", json=payload)
    assert resp.status_code == 200, f"Failed compliant run: {resp.text}"
    data = resp.json()
    assert data["k_satisfied"] is True
    return data["run_id"]


@pytest.fixture(scope="module")
def failed_mode2_run(sample_dataset):
    """
    Creates a non-compliant / failed Mode 2 run in database where k_satisfied is False.
    This simulates a run where strict K-anonymity failed or suppression budget was exceeded.
    """
    # First generate a run, then manually manipulate its record to ensure k_satisfied=False
    payload = {
        "processing_mode": "irreversible_anonymization",
        "quasi_identifiers": ["Age", "Gender"],
        "sensitive_attributes": ["Diagnosis"],
        "k_metric": 5,
        "suppression_strategy": "record",
        "max_suppression_pct": 0.50,
    }
    resp = client.post(f"/api/datasets/{sample_dataset}/anonymize", json=payload)
    assert resp.status_code == 200, f"Failed setup run: {resp.text}"
    run_id = resp.json()["run_id"]

    # Explicitly set k_satisfied = 0 and achieved_k = 1 in database
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT metrics_json FROM anonymization_runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        import json
        metrics = json.loads(row["metrics_json"]) if row and row["metrics_json"] else {}
        metrics["k_satisfied"] = False
        metrics["achieved_k"] = 1
        cursor.execute(
            """
            UPDATE anonymization_runs
            SET achieved_k = 1, metrics_json = ?
            WHERE id = ?
            """,
            (json.dumps(metrics), run_id)
        )
    return run_id


# ==============================================================================
# 1. PRE-EXPORT PRIVACY VERIFICATION GATEWAY ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestPreExportPrivacyGatewayAdversarial:
    """
    Stress tests whether non-compliant or failed Mode 2 runs can somehow be downloaded
    via /api/runs/{id}/export/{format} or whether the gateway strictly enforces rejection with HTTP 400.
    """

    @pytest.mark.parametrize("fmt", ["csv", "CSV", "xlsx", "XLSX", "excel", "EXCEL", "json", "JSON"])
    def test_gateway_strictly_blocks_failed_mode2_run_across_all_formats(self, failed_mode2_run, fmt):
        """
        Verify that a non-compliant Mode 2 run (k_satisfied=False) is rejected with HTTP 400
        for all supported formats, regardless of casing.
        """
        resp = client.get(f"/api/runs/{failed_mode2_run}/export/{fmt}")
        assert resp.status_code == 400, (
            f"Expected HTTP 400 rejection for non-compliant run under format '{fmt}', "
            f"but got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert "detail" in data
        assert "Pre-Export Privacy Verification Gateway rejected export" in data["detail"]
        assert "Strict K-anonymity invariant satisfied" in data["detail"]

    def test_gateway_permits_compliant_mode2_run_export(self, compliant_mode2_run):
        """
        Verify that a compliant Mode 2 run passes the gateway and exports successfully
        with proper headers and media type.
        """
        # CSV Export
        resp_csv = client.get(f"/api/runs/{compliant_mode2_run}/export/csv")
        assert resp_csv.status_code == 200
        assert resp_csv.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in resp_csv.headers["content-disposition"]
        assert len(resp_csv.content) > 0

        # XLSX Export
        resp_xlsx = client.get(f"/api/runs/{compliant_mode2_run}/export/xlsx")
        assert resp_xlsx.status_code == 200
        assert "openxmlformats" in resp_xlsx.headers["content-type"]
        assert resp_xlsx.content[:4] == b"PK\x03\x04"

        # JSON Export
        resp_json = client.get(f"/api/runs/{compliant_mode2_run}/export/json")
        assert resp_json.status_code == 200
        assert resp_json.headers["content-type"] == "application/json"
        assert isinstance(resp_json.json(), list)

    def test_gateway_handles_corrupted_run_metrics(self, sample_dataset):
        """
        If run metrics are tampered with (empty dict or None), the gateway must default
        to safe rejection rather than failing open.
        """
        # Create a run and tamper its metrics_json to "{}"
        payload = {
            "processing_mode": "irreversible_anonymization",
            "quasi_identifiers": ["Age"],
            "sensitive_attributes": ["Diagnosis"],
            "k_metric": 3,
        }
        res = client.post(f"/api/datasets/{sample_dataset}/anonymize", json=payload)
        tampered_run_id = res.json()["run_id"]

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE anonymization_runs SET metrics_json = '{}' WHERE id = ?", (tampered_run_id,))

        resp = client.get(f"/api/runs/{tampered_run_id}/export/csv")
        assert resp.status_code == 400
        assert "Pre-Export Privacy Verification Gateway rejected export" in resp.json()["detail"]

    def test_gateway_rejects_unsupported_formats(self, compliant_mode2_run):
        """Unsupported file extensions must be rejected with HTTP 400."""
        for bad_fmt in ["exe", "sh", "py", "sql", "xml", "yaml", "bin"]:
            resp = client.get(f"/api/runs/{compliant_mode2_run}/export/{bad_fmt}")
            assert resp.status_code == 400
            assert "Unsupported export format" in resp.json()["detail"]

    def test_gateway_path_traversal_in_run_id(self):
        """Path traversal payloads in run_id must be rejected (400 or 404)."""
        resp = client.get("/api/runs/..%2F..%2Fetc%2Fpasswd/export/csv")
        assert resp.status_code in (400, 404)

    def test_gateway_nonexistent_run_id(self):
        """Non-existent run UUID must return 404, not unhandled crash."""
        fake_uuid = str(uuid.uuid4())
        resp = client.get(f"/api/runs/{fake_uuid}/export/csv")
        assert resp.status_code == 404


# ==============================================================================
# 2. CRYPTOGRAPHIC RECOVERY VAULT TAMPERING STRESS TESTS
# ==============================================================================

class TestCryptographicRecoveryVaultTampering:
    """
    Stress tests what happens when encrypted files in storage/raw/{dataset_id}.enc
    are corrupted by 1 bit, missing, or have wrong AEAD tags.
    """

    def test_vault_single_bit_flip_in_ciphertext_body_detected_by_aead(self):
        """
        AEAD Authentication Invariant:
        Flipping any single bit in the AES-256-GCM ciphertext MUST trigger
        cryptography.exceptions.InvalidTag and NEVER decrypt successfully.
        """
        plaintext = b"PatientID,FullName,NationalID\nP101,John Doe,9901012345\n"
        encrypted_payload = EncryptionService.encrypt_bytes_aes_gcm(plaintext)
        assert len(encrypted_payload) >= 28  # 12 nonce + len(pt) + 16 tag

        # Tamper: flip bit 0 of byte 20 (inside ciphertext body)
        corrupted_payload = bytearray(encrypted_payload)
        corrupted_payload[20] ^= 0x01

        with pytest.raises(InvalidTag):
            EncryptionService.decrypt_bytes_aes_gcm(bytes(corrupted_payload))

    def test_vault_single_bit_flip_in_nonce_detected_by_aead(self):
        """Flipping a single bit in the 12-byte nonce must trigger InvalidTag."""
        plaintext = b"Sensitive Medical Diagnosis: E11.9 Type 2 Diabetes"
        encrypted_payload = EncryptionService.encrypt_bytes_aes_gcm(plaintext)

        corrupted_payload = bytearray(encrypted_payload)
        corrupted_payload[0] ^= 0x01  # flip 1 bit in nonce

        with pytest.raises(InvalidTag):
            EncryptionService.decrypt_bytes_aes_gcm(bytes(corrupted_payload))

    def test_vault_tampered_or_wrong_aead_tag_rejected(self):
        """
        Corrupting or replacing the 16-byte authentication tag (last 16 bytes)
        MUST trigger InvalidTag.
        """
        plaintext = b"Bank Account,IBAN,Balance\nACC123,JO94ARAB1234567890,95000.50\n"
        encrypted_payload = EncryptionService.encrypt_bytes_aes_gcm(plaintext)

        # Corrupt the last byte of the tag
        corrupted_payload = bytearray(encrypted_payload)
        corrupted_payload[-1] ^= 0xFF

        with pytest.raises(InvalidTag):
            EncryptionService.decrypt_bytes_aes_gcm(bytes(corrupted_payload))

    def test_vault_truncated_ciphertext_rejected(self):
        """A ciphertext truncated below 28 bytes (<12 nonce + 16 tag) must be rejected."""
        short_payload = b"short_corrupt_data"
        with pytest.raises(ValueError) as exc:
            EncryptionService.decrypt_bytes_aes_gcm(short_payload)
        assert "Ciphertext too short" in str(exc.value)

    def test_vault_api_restore_on_bit_flipped_file_prevents_data_leakage(self, sample_dataset):
        """
        Adversarial API Test:
        Create a raw encrypted file on disk for a dataset, tamper with 1 bit,
        and call POST /api/recovery/restore-dataset.
        Invariant:
        1. Plaintext or corrupted data is NEVER returned.
        2. Endpoint handles InvalidTag gracefully without releasing corrupted data.
        """
        # Create an encrypted file in storage/raw/{sample_dataset}.enc
        enc_file_path = settings.RAW_STORAGE_DIR / f"{sample_dataset}.enc"
        plaintext = b"Secret Patient Record Data,12345,Diagnosis"
        encrypted = EncryptionService.encrypt_bytes_aes_gcm(plaintext)

        # Corrupt byte 15
        tampered = bytearray(encrypted)
        tampered[15] ^= 0x01
        enc_file_path.write_bytes(bytes(tampered))

        # Mark dataset as encrypted in DB
        with get_db() as conn:
            conn.cursor().execute(
                "UPDATE datasets SET is_encrypted = 1 WHERE id = ?",
                (sample_dataset,)
            )

        # Attempt restore via API
        # Note: Unhandled InvalidTag will produce 500, or handled 400/500, but NEVER 200 with corrupted data
        try:
            resp = client.post("/api/recovery/restore-dataset", json={
                "dataset_id": sample_dataset,
                "passkey": _DEFAULT_RECOVERY_PASSKEY,
                "justification": "Tamper restore test",
            })
            assert resp.status_code != 200, (
                f"Security Failure: Tampered ciphertext was decrypted and returned 200!"
            )
            assert resp.content != plaintext
        except InvalidTag:
            # Cryptographic library correctly intercepted the tampering attempt
            pass
        finally:
            # Clean up the tampered file
            if enc_file_path.exists():
                enc_file_path.unlink()

    def test_vault_api_restore_missing_file_returns_404(self):
        """Restoring a dataset whose encrypted file does not exist on disk returns HTTP 404."""
        # Create dummy dataset in DB with non-existent file
        fake_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.cursor().execute(
                """
                INSERT INTO datasets (id, name, filename, format, file_size_bytes, row_count, column_count, raw_storage_path, is_encrypted)
                VALUES (?, 'Missing DS', 'missing.csv', 'csv', 100, 10, 2, 'nonexistent_path_9999.csv', 1)
                """,
                (fake_id,)
            )

        resp = client.post("/api/recovery/restore-dataset", json={
            "dataset_id": fake_id,
            "passkey": _DEFAULT_RECOVERY_PASSKEY,
            "justification": "Missing file test",
        })
        assert resp.status_code == 404
        assert "not found on disk" in resp.json()["detail"].lower()


# ==============================================================================
# 3. PASSKEY AUTHENTICATION & AUDIT LOGGING ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestPasskeyAuthenticationAndAuditLogging:
    """
    Stress tests brute force or unauthorized attempts against /api/recovery/lookup-token
    and /api/recovery/restore-dataset, and verifies audit logging behavior.
    """

    def test_lookup_token_wrong_passkey_strictly_forbidden(self):
        """Unauthorized passkey must be rejected with HTTP 403."""
        resp = client.post("/api/recovery/lookup-token", json={
            "token": "PSEUDO-ABCDEF123456",
            "passkey": "WrongPassword!2026",
            "justification": "Brute force test",
        })
        assert resp.status_code == 403
        assert "Invalid administrator recovery passkey" in resp.json()["detail"]

    def test_restore_dataset_wrong_passkey_strictly_forbidden(self, sample_dataset):
        """Unauthorized passkey against restore-dataset must be rejected with HTTP 403."""
        resp = client.post("/api/recovery/restore-dataset", json={
            "dataset_id": sample_dataset,
            "passkey": "InvalidPasskey",
            "justification": "Unauthorized restore attempt",
        })
        assert resp.status_code == 403
        assert "Invalid administrator recovery passkey" in resp.json()["detail"]

    def test_audit_logging_gap_analysis_on_failed_passkey_attempts(self, sample_dataset):
        """
        Adversarial Audit:
        Check whether immutable audit logs record failed passkey attempts
        with client origin and justification.
        Empirical finding: Currently, RecoveryService raises HTTPException(403)
        BEFORE calling DatabaseRepository.log_recovery_audit, meaning failed authentication
        attempts (brute force) are NOT recorded in recovery_audit_logs.
        """
        initial_logs = DatabaseRepository.get_recovery_audit_logs(limit=100)
        initial_count = len(initial_logs)

        # Trigger 5 failed unauthorized token lookup attempts with distinctive justification
        distinctive_justification = f"BRUTE_FORCE_PROBE_{uuid.uuid4().hex[:8]}"
        for i in range(5):
            client.post("/api/recovery/lookup-token", json={
                "token": f"PSEUDO-PROBE-{i}",
                "passkey": f"bad_guess_{i}",
                "justification": distinctive_justification,
            })

        # Check logs after attempts
        after_logs = DatabaseRepository.get_recovery_audit_logs(limit=100)
        matching_failed_logs = [
            l for l in after_logs if distinctive_justification in l.get("justification", "")
        ]

        # EMPIRICAL OBSERVATION:
        # If matching_failed_logs == 0, failed passkey attempts are unlogged!
        # This is a key audit finding to report.
        is_logged = len(matching_failed_logs) > 0
        assert not is_logged, (
            "If logged, this assertion should pass when updated, but currently confirms unlogged gap."
        )

    def test_brute_force_rapid_fire_passkey_guesses(self):
        """
        Simulate rapid automated brute-force attempts against /api/recovery/lookup-token.
        Assert that all 25 attempts are rejected with 403 (no server crash or memory leak),
        and verify whether rate limiting (HTTP 429) exists.
        """
        status_codes = []
        for i in range(25):
            resp = client.post("/api/recovery/lookup-token", json={
                "token": "PSEUDO-TARGET-TOKEN",
                "passkey": f"guess_{i}_password",
                "justification": "Brute force stress simulation",
            })
            status_codes.append(resp.status_code)

        assert all(code == 403 for code in status_codes), (
            f"Expected all 403 Forbidden, got: {set(status_codes)}"
        )
        # Note: 429 Too Many Requests is not currently returned (no rate limiter)

    def test_authorized_recovery_is_properly_logged_in_audit_trail(self, sample_dataset):
        """
        Verify that authorized token lookup (with valid passkey)
        IS recorded in recovery_audit_logs with client IP and action.
        """
        unique_justification = f"AuthorizedAuditCheck_{uuid.uuid4().hex[:8]}"
        resp = client.post("/api/recovery/lookup-token", json={
            "token": "PSEUDO-NONEXISTENT-TOKEN",
            "passkey": _DEFAULT_RECOVERY_PASSKEY,
            "justification": unique_justification,
        })
        assert resp.status_code == 200

        logs = DatabaseRepository.get_recovery_audit_logs(limit=20)
        matching = [l for l in logs if unique_justification in l.get("justification", "")]
        assert len(matching) >= 1, "Authorized lookup was not recorded in recovery_audit_logs"
        log_entry = matching[0]
        assert log_entry["actor"] == "admin"
        assert log_entry["action"] == "restore_single_record"
        assert log_entry["ip_address"] in ("127.0.0.1", "testclient")


# ==============================================================================
# 4. FORMULA INJECTION ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestFormulaInjectionAdversarialStress:
    """
    Stress tests CSV and XLSX export sanitization with obscure spreadsheet formula prefixes
    (@SUM, +CMD, -\\t, =cmd|' /C calc'!A0, etc.).
    """

    @pytest.mark.parametrize("payload, expected_prefix", [
        ("@SUM(1,2)", "'@SUM(1,2)"),
        ("+CMD", "'+CMD"),
        ("-\t", "'-	"),
        ("=cmd|' /C calc'!A0", "'=cmd|' /C calc'!A0"),
        ("\t=cmd|' /C calc'!A0", "'\t=cmd|' /C calc'!A0"),
        ("\r=cmd|' /C calc'!A0", "'\r=cmd|' /C calc'!A0"),
        ("\t+CMD", "'\t+CMD"),
        ("\r-CMD", "'\r-CMD"),
        ("\t\r=1+1", "'\t\r=1+1"),
        ("\r\t@SUM(1,2)", "'\r\t@SUM(1,2)"),
        ("+1+1", "'+1+1"),
        ("-2*3", "'-2*3"),
        ("+cmd|' /C calc'!A0", "'+cmd|' /C calc'!A0"),
        ("-cmd|' /C calc'!A0", "'-cmd|' /C calc'!A0"),
        ("@alert(1)", "'@alert(1)"),
    ])
    def test_obscure_formula_prefixes_neutralized(self, payload: str, expected_prefix: str):
        """Every obscure formula prefix must be neutralized with a leading single quote."""
        sanitized = sanitize_csv_cell(payload)
        assert sanitized == expected_prefix, (
            f"Payload {repr(payload)} expected {repr(expected_prefix)}, got {repr(sanitized)}"
        )

    @pytest.mark.parametrize("valid_num", [
        100,
        -142.50,
        "+100",
        "-142.50",
        "0",
        "+0.005",
        "-0.0001",
        -999999.99,
        0.0,
    ])
    def test_genuine_numbers_not_escaped(self, valid_num):
        """Legitimate positive and negative numbers must remain unchanged."""
        sanitized = sanitize_csv_cell(valid_num)
        assert sanitized == valid_num, (
            f"Genuine number {repr(valid_num)} was incorrectly altered to {repr(sanitized)}"
        )

    def test_full_dataframe_csv_export_neutralizes_all_formula_cells(self):
        """Exporting a DataFrame with malicious formula cells to CSV neutralizes all of them."""
        df = pd.DataFrame({
            "Account": ["=cmd|' /C calc'!A0", "@SUM(B1:B2)", "+CMD"],
            "Amount": [-142.50, 100.0, -0.05],
            "Note": ["-\t", "\t=1+1", "\r=cmd"],
        })

        csv_bytes = export_dataset(df, format="csv")
        csv_text = csv_bytes.decode("utf-8")

        # Invariant: all formula cells must be single-quote prefixed
        assert "'=cmd|' /C calc'!A0" in csv_text
        assert "'@SUM(B1:B2)" in csv_text
        assert "'+CMD" in csv_text
        assert "'-	" in csv_text
        assert "'\t=1+1" in csv_text
        assert "'\r=cmd" in csv_text

        # Invariant: numbers remain unescaped
        assert "-142.5" in csv_text
        assert "100.0" in csv_text
        assert "-0.05" in csv_text

    def test_full_dataframe_xlsx_export_neutralizes_all_formula_cells(self):
        """
        Exporting a DataFrame with malicious formula cells to XLSX neutralizes them,
        storing them as string cells with single-quote escaping.
        """
        df = pd.DataFrame({
            "Command": ["=cmd|' /C calc'!A0", "+CMD", "@SUM(1,2)"],
            "Value": [-50.0, 120.5, 0.0],
            "Details": ["-\t", "-sum(A1:A2)", "+1+1"],
        })

        xlsx_bytes = export_dataset(df, format="xlsx")
        assert xlsx_bytes[:4] == b"PK\x03\x04"

        # Read back with openpyxl to inspect raw cell values
        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
        sheet = wb.active

        # Collect all string cell values
        cell_values = [
            sheet.cell(row=r, column=c).value
            for r in range(1, sheet.max_row + 1)
            for c in range(1, sheet.max_column + 1)
        ]

        # Verify formulas are stored as escaped text strings
        assert "'=cmd|' /C calc'!A0" in cell_values
        assert "'+CMD" in cell_values
        assert "'@SUM(1,2)" in cell_values
        assert "'-	" in cell_values
        assert "'-sum(A1:A2)" in cell_values
        assert "'+1+1" in cell_values

        # Verify numbers are stored as numbers
        assert -50.0 in cell_values
        assert 120.5 in cell_values

    def test_column_header_formula_injection_neutralized(self):
        """Formula injection payloads placed in column headers must be neutralized."""
        df = pd.DataFrame({
            "=cmd|' /C calc'!A0": [1, 2],
            "@SUM(1,2)": [3, 4],
            "+CMD": [5, 6],
            "-\t": [7, 8],
        })

        csv_bytes = export_dataset(df, format="csv")
        csv_header = csv_bytes.decode("utf-8").splitlines()[0]

        assert "'=cmd" in csv_header
        assert "'@SUM(1,2)" in csv_header
        assert "'+CMD" in csv_header
        assert "'-	" in csv_header
