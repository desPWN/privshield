"""
Tier 3: Cross-Feature Combinations - Module C03: Privacy vs Utility Tradeoff Verification.
Validates the fundamental privacy-utility tradeoff: monotonic decrease in CURS and increase in suppression
as privacy parameters (K, L, T) tighten.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import (
    get_apply_generalization_fn,
    get_enforce_strict_k_anonymity_fn,
    get_compute_utility_metrics_fn,
    get_compute_privacy_risks_fn,
)


def test_monotonic_suppression_increase_with_higher_k(synthetic_jordanian_df):
    """As target K increases from 2 to 5 to 10, suppression rate monotonically increases or stays constant."""
    k_fn = get_enforce_strict_k_anonymity_fn()
    qis = ["City", "Age"]

    res_k2 = k_fn(synthetic_jordanian_df, qis=qis, k=2, strategy="record", max_suppression_pct=1.0)
    res_k5 = k_fn(synthetic_jordanian_df, qis=qis, k=5, strategy="record", max_suppression_pct=1.0)
    res_k10 = k_fn(synthetic_jordanian_df, qis=qis, k=10, strategy="record", max_suppression_pct=1.0)

    # Monotonicity check
    assert res_k2.suppression_rate <= res_k5.suppression_rate
    assert res_k5.suppression_rate <= res_k10.suppression_rate

    assert res_k2.retained_records >= res_k5.retained_records
    assert res_k5.retained_records >= res_k10.retained_records


def test_monotonic_prosecutor_risk_decrease_with_higher_k(synthetic_jordanian_df):
    """As target K increases, maximum Prosecutor risk strictly decreases: Risk <= 1 / K."""
    k_fn = get_enforce_strict_k_anonymity_fn()
    risk_fn = get_compute_privacy_risks_fn()
    gen_fn = get_apply_generalization_fn()

    df_gen = gen_fn(synthetic_jordanian_df, {"City": 2})
    qis = ["City", "Gender"]

    res_k3 = k_fn(df_gen, qis=qis, k=3)
    res_k8 = k_fn(df_gen, qis=qis, k=8)

    risk_k3 = risk_fn(res_k3.anonymized_df, qis=qis)
    risk_k8 = risk_fn(res_k8.anonymized_df, qis=qis)

    # Prosecutor risk at K=8 must be strictly less than or equal to risk at K=3
    assert risk_k8.prosecutor_risk <= risk_k3.prosecutor_risk
    assert risk_k8.prosecutor_risk <= (1.0 / 8.0)
    assert risk_k3.prosecutor_risk <= (1.0 / 3.0)


def test_monotonic_curs_decrease_with_deeper_generalization(synthetic_jordanian_df):
    """Climbing generalization levels penalizes information granularity, reducing CURS."""
    util_fn = get_compute_utility_metrics_fn()

    res_l0 = util_fn(
        original_df=synthetic_jordanian_df,
        anonymized_df=synthetic_jordanian_df.copy(),
        quasi_identifiers=["City", "Age"],
        generalization_levels={"City": 0, "Age": 0}
    )

    res_l1 = util_fn(
        original_df=synthetic_jordanian_df,
        anonymized_df=synthetic_jordanian_df.copy(),
        quasi_identifiers=["City", "Age"],
        generalization_levels={"City": 1, "Age": 1}
    )

    res_l3 = util_fn(
        original_df=synthetic_jordanian_df,
        anonymized_df=synthetic_jordanian_df.copy(),
        quasi_identifiers=["City", "Age"],
        generalization_levels={"City": 3, "Age": 3}
    )

    assert res_l0.composite_utility_score >= res_l1.composite_utility_score
    assert res_l1.composite_utility_score >= res_l3.composite_utility_score


def test_utility_suppression_rate_consistency_with_k_anonymity_result(synthetic_jordanian_df):
    """Suppression rate computed in UtilityMetrics strictly mirrors AnonymizationResult suppression rate."""
    k_fn = get_enforce_strict_k_anonymity_fn()
    util_fn = get_compute_utility_metrics_fn()

    res_k = k_fn(synthetic_jordanian_df, qis=["City", "Age"], k=4, strategy="record")
    util = util_fn(synthetic_jordanian_df, res_k.anonymized_df)

    assert abs(res_k.suppression_rate - util.suppression_rate) < 1e-4
    assert res_k.suppressed_records == util.suppressed_records
