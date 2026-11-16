"""
Tier 3: Cross-Feature Combinations - Module C01: Masking + Generalization + Strict K-Anonymity.
Validates the coordinated pipeline: Direct ID masking, multi-tier QI generalization,
and strict K-anonymity enforcement with zero residual PII.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import (
    get_apply_masking_fn,
    get_apply_generalization_fn,
    get_enforce_strict_k_anonymity_fn,
)
from tests_e2e.conftest import assert_strict_k_anonymity, assert_zero_raw_pii


def test_masking_generalization_strict_k_pipeline(synthetic_jordanian_df):
    """Executes masking on direct IDs, generalization on QIs, and strict K=4."""
    mask_fn = get_apply_masking_fn()
    gen_fn = get_apply_generalization_fn()
    k_fn = get_enforce_strict_k_anonymity_fn()

    # Step 1: Mask direct identifiers
    mask_rules = {
        "National_ID": "national_id",
        "IBAN": "iban",
        "Email": "email",
        "Phone": "phone",
        "Card_Number": "card_number",
        "Customer_Name": "redact"
    }
    df_masked = mask_fn(synthetic_jordanian_df, mask_rules)

    # Step 2: Generalize quasi-identifiers (City to Region, Age to range)
    gen_rules = {"City": 2, "Age": 1}
    df_gen = gen_fn(df_masked, gen_rules)

    # Step 3: Enforce strict K=4
    qis = ["City", "Age", "Gender"]
    res = k_fn(df_gen, qis=qis, k=4, strategy="record", max_suppression_pct=0.50)

    assert res.k_satisfied is True
    assert res.retained_records > 0
    assert_strict_k_anonymity(res.anonymized_df, qis, 4)

    # Step 4: Verify zero raw PII in final released dataset
    anon_csv = res.anonymized_df.to_csv(index=False)
    assert_zero_raw_pii(anon_csv)


def test_masked_direct_ids_do_not_fragment_equivalence_classes(synthetic_jordanian_df):
    """Direct identifiers are excluded from QIs so masking does not distort class sizes."""
    mask_fn = get_apply_masking_fn()
    gen_fn = get_apply_generalization_fn()
    k_fn = get_enforce_strict_k_anonymity_fn()

    df_masked = mask_fn(synthetic_jordanian_df, {"National_ID": "national_id"})
    df_gen = gen_fn(df_masked, {"City": 2})

    qis = ["City", "Gender"]
    res = k_fn(df_gen, qis=qis, k=5)

    assert res.k_satisfied is True
    # The number of classes depends purely on QIs (City, Gender), not National_ID
    assert res.num_equivalence_classes <= (3 * 2)  # At most 3 regions x 2 genders


def test_multi_tier_generalization_enhances_k_compliance(synthetic_jordanian_df):
    """Climbing from City Level 1 (Governorate) to Level 2 (Region) strictly increases class sizes and reduces suppression."""
    gen_fn = get_apply_generalization_fn()
    k_fn = get_enforce_strict_k_anonymity_fn()

    qis = ["City", "Gender"]

    # Level 1: Governorate
    df_l1 = gen_fn(synthetic_jordanian_df, {"City": 1})
    res_l1 = k_fn(df_l1, qis=qis, k=10, strategy="record", max_suppression_pct=0.90)

    # Level 2: Region (broader)
    df_l2 = gen_fn(synthetic_jordanian_df, {"City": 2})
    res_l2 = k_fn(df_l2, qis=qis, k=10, strategy="record", max_suppression_pct=0.90)

    # Level 2 should retain at least as many records as Level 1
    assert res_l2.retained_records >= res_l1.retained_records
    assert res_l2.suppression_rate <= res_l1.suppression_rate


def test_suppressed_records_completely_omitted_from_output(synthetic_jordanian_df):
    """Suppressed rows must not appear in the anonymized DataFrame under record suppression."""
    k_fn = get_enforce_strict_k_anonymity_fn()
    qis = ["City", "Age"]

    res = k_fn(synthetic_jordanian_df, qis=qis, k=4, strategy="record")

    if res.suppressed_records > 0:
        assert len(res.anonymized_df) == res.retained_records
        assert len(res.anonymized_df) < len(synthetic_jordanian_df)
        assert res.retained_records + res.suppressed_records == len(synthetic_jordanian_df)
