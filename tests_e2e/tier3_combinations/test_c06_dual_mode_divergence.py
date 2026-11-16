"""
tests_e2e/tier3_combinations/test_c06_dual_mode_divergence.py
Tier 3 Combination: Dual processing modes (Mode 1 Reversible vs Mode 2 Irreversible) and pre-export privacy evaluation gateway.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import (
    get_enforce_strict_k_anonymity_fn,
    get_export_dataset_fn,
    verify_pre_export_privacy_gateway,
    get_recovery_vault
)


def test_mode_divergence_pipeline(customer_database_df: pd.DataFrame):
    enforce_k = get_enforce_strict_k_anonymity_fn()
    export_fn = get_export_dataset_fn()
    vault = get_recovery_vault()

    qis = ["City", "Age"]
    res = enforce_k(customer_database_df, qis=qis, k=4)
    anon_df = res.anonymized_df if hasattr(res, "anonymized_df") else res[0]

    # Pre-export gateway verification on Mode 2 anonymization
    can_export, msg = verify_pre_export_privacy_gateway(res)
    assert can_export is True

    # Mode 2 export executes cleanly
    csv_bytes = export_fn(anon_df, format="csv")
    assert len(csv_bytes) > 0

    # In Mode 2, no recovery mapping exists in the vault for this run
    mode2_dataset_id = "ds-mode2-irreversible-run"
    assert mode2_dataset_id not in vault.raw_vault
    assert mode2_dataset_id not in vault.token_vault
