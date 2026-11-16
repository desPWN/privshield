"""
Unit tests for PrivShield RecoveryService.
Verifies reversible pseudonymization:
1. Token mapping generation & encrypted vault storage
2. Authorized single-token lookup with passkey verification
3. Full dataset restoration from encrypted storage
4. Rejection of unauthorized recovery attempts (403 Forbidden)
5. Immutable audit logging in recovery_audit_logs
"""

from pathlib import Path
from fastapi import HTTPException
import pandas as pd
import pytest

from backend.app.db.database import DatabaseRepository
from backend.app.services.encryption_service import EncryptionService
from backend.app.services.recovery_service import RecoveryService


def test_pseudonymize_and_single_token_lookup(tmp_path: Path):
    dataset_id = "test-ds-rec-001"
    run_id = "test-run-rec-001"

    # Register dataset in DB
    DatabaseRepository.create_dataset({
        "id": dataset_id,
        "name": "Patient Clinical Trial",
        "filename": "patients.csv",
        "format": "csv",
        "file_size_bytes": 1024,
        "row_count": 3,
        "column_count": 3,
        "raw_storage_path": str(tmp_path / "patients.csv"),
    })

    df = pd.DataFrame({
        "PatientID": ["PAT-101", "PAT-102", "PAT-103"],
        "PatientName": ["Ahmad Al-Majali", "Rania Haddad", "Omar Al-Zubi"],
        "Diagnosis": ["I10", "E11.9", "J45.0"]
    })

    pseudo_df, token_count = RecoveryService.pseudonymize_dataframe(
        df=df,
        dataset_id=dataset_id,
        run_id=run_id,
        direct_identifiers=["PatientID", "PatientName"],
        token_prefix="PATIENT_TOK"
    )

    assert token_count == 6  # 3 rows * 2 direct identifier columns
    assert pseudo_df["PatientName"].iloc[0].startswith("PATIENT_TOK-")
    assert pseudo_df["PatientName"].iloc[0] != "Ahmad Al-Majali"

    # Authorized lookup with valid passkey
    sample_token = pseudo_df["PatientName"].iloc[0]
    resp = RecoveryService.lookup_token(
        token=sample_token,
        passkey="PrivShieldAdmin2026!",
        run_id=run_id,
        justification="Statutory clinical trial audit"
    )

    assert resp.found is True
    assert resp.original_value == "Ahmad Al-Majali"
    assert resp.token == sample_token

    # Verify token count queries
    assert DatabaseRepository.count_token_mappings(dataset_id=dataset_id, run_id=run_id) == 6
    assert DatabaseRepository.count_tokens_for_run(run_id) == 6


def test_lookup_token_unauthorized_passkey():
    with pytest.raises(HTTPException) as exc_info:
        RecoveryService.lookup_token(
            token="PATIENT_TOK-123456789012",
            passkey="InvalidPasskey123"
        )
    assert exc_info.value.status_code == 403
    assert "Invalid administrator recovery passkey" in exc_info.value.detail


def test_restore_full_dataset_encrypted(tmp_path: Path):
    dataset_id = "test-ds-restore-002"

    raw_csv = b"id,name,diagnosis\n1,Alice,I10\n2,Bob,E11\n"
    raw_path = tmp_path / "raw.csv"
    raw_path.write_bytes(raw_csv)

    enc_path = tmp_path / f"{dataset_id}.enc"
    EncryptionService.encrypt_file(raw_path, enc_path)

    DatabaseRepository.create_dataset({
        "id": dataset_id,
        "name": "Encrypted Patient Data",
        "filename": "raw.csv",
        "format": "csv",
        "file_size_bytes": len(raw_csv),
        "row_count": 2,
        "column_count": 3,
        "raw_storage_path": str(enc_path),
    })

    # Unauthorized attempt
    with pytest.raises(HTTPException) as exc_info:
        RecoveryService.restore_dataset(
            dataset_id=dataset_id,
            passkey="BadPasskey"
        )
    assert exc_info.value.status_code == 403

    # Authorized restoration
    restored_bytes = RecoveryService.restore_dataset(
        dataset_id=dataset_id,
        passkey="PrivShieldAdmin2026!",
        justification="Court subpoena verification"
    )
    assert restored_bytes == raw_csv

    # Verify audit log recorded
    logs = RecoveryService.get_audit_logs(limit=10)
    matching = [l for l in logs if l.dataset_id == dataset_id and l.action == "restore_dataset"]
    assert len(matching) >= 1
    assert "Court subpoena verification" in matching[0].justification
