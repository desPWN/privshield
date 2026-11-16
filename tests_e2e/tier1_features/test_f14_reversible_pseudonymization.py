"""
tests_e2e/tier1_features/test_f14_reversible_pseudonymization.py
Feature 14: Reversible Pseudonymization Mode & Recovery Service.
Validates Mode 1: encrypted vault preservation, single-token lookup, full dataset restoration, and audit logging.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import get_recovery_vault


def test_mode1_retains_encrypted_vault_and_mappings(hospital_patient_df: pd.DataFrame):
    vault = get_recovery_vault()
    dataset_id = "ds-hosp-001"
    mappings = {
        "TOK-MRN-001": hospital_patient_df["MRN"].iloc[0],
        "TOK-MRN-002": hospital_patient_df["MRN"].iloc[1]
    }
    vault.store_dataset_mode1(dataset_id, hospital_patient_df, mappings)

    assert dataset_id in vault.raw_vault
    assert dataset_id in vault.token_vault
    assert len(vault.token_vault[dataset_id]) == 2


def test_single_token_lookup_with_valid_passkey():
    vault = get_recovery_vault()
    dataset_id = "ds-hosp-001"
    token = "TOK-MRN-001"
    passkey = "AdminPasskey2026!"

    original_val = vault.lookup_token(dataset_id, token, passkey)
    assert original_val.startswith("MRN-")


def test_full_dataset_restoration_with_valid_passkey():
    vault = get_recovery_vault()
    dataset_id = "ds-hosp-001"
    passkey = "AdminPasskey2026!"

    restored_df = vault.restore_dataset(dataset_id, passkey)
    assert isinstance(restored_df, pd.DataFrame)
    assert len(restored_df) >= 100
    assert "MRN" in restored_df.columns


def test_recovery_with_invalid_passkey_fails_securely():
    vault = get_recovery_vault()
    dataset_id = "ds-hosp-001"

    with pytest.raises(PermissionError, match="Invalid recovery passkey"):
        vault.lookup_token(dataset_id, "TOK-MRN-001", "WrongPasskey!")

    with pytest.raises(PermissionError, match="Invalid recovery passkey"):
        vault.restore_dataset(dataset_id, "WrongPasskey!")


def test_recovery_attempts_logged_in_audit_trail():
    vault = get_recovery_vault()
    dataset_id = "ds-hosp-001"

    # Perform one successful and one failed recovery
    vault.lookup_token(dataset_id, "TOK-MRN-001", "AdminPasskey2026!")
    try:
        vault.lookup_token(dataset_id, "TOK-MRN-001", "BadPasskey")
    except PermissionError:
        pass

    recent_logs = [log for log in vault.audit_log if log["dataset_id"] == dataset_id]
    statuses = [log["status"] for log in recent_logs]
    assert "success" in statuses
    assert "failed_auth" in statuses
