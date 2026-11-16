"""
tests_e2e/tier3_combinations/test_c05_reversible_pseudonymization_recovery_pipeline.py
Tier 3 Combination: Reversible Pseudonymization (Mode 1), token lookup, full dataset restoration, and audit trail verification.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import get_apply_masking_fn, get_recovery_vault, format_preserving_token


def test_reversible_pseudonymization_full_recovery_lifecycle(hospital_patient_df: pd.DataFrame):
    vault = get_recovery_vault()
    dataset_id = "ds-hosp-recovery-c05"
    admin_key = "AdminPasskey2026!"

    # 1. Generate format-preserving tokens for MRN
    token_mapping = {}
    tokens = []
    for mrn in hospital_patient_df["MRN"]:
        tok = format_preserving_token(mrn, prefix="TOK-MRN")
        tokens.append(tok)
        token_mapping[tok] = mrn

    pseudonymized_df = hospital_patient_df.copy()
    pseudonymized_df["MRN"] = tokens

    # 2. Store in Mode 1 encrypted vault
    vault.store_dataset_mode1(dataset_id, hospital_patient_df, token_mapping)

    # 3. Single token lookup
    sample_tok = tokens[0]
    expected_mrn = hospital_patient_df["MRN"].iloc[0]
    recovered_mrn = vault.lookup_token(dataset_id, sample_tok, admin_key)
    assert recovered_mrn == expected_mrn

    # 4. Full dataset restoration
    restored_df = vault.restore_dataset(dataset_id, admin_key)
    assert len(restored_df) == len(hospital_patient_df)
    assert (restored_df["MRN"] == hospital_patient_df["MRN"]).all()

    # 5. Audit log verification
    audit_events = [log for log in vault.audit_log if log["dataset_id"] == dataset_id]
    actions = [e["action"] for e in audit_events]
    assert "lookup_token" in actions
    assert "restore_dataset" in actions
    assert all(e["status"] == "success" for e in audit_events)
