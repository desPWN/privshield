"""
Tier 2: Boundary & Corner Cases - Module B02: Identical & Unique Quasi-Identifiers.
Validates behavior when QIs collapse into a single monolithic equivalence class (M=1)
or fragment into all-unique singleton equivalence classes (M=N).
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import (
    get_enforce_strict_k_anonymity_fn,
    get_evaluate_distinct_l_diversity_fn,
    get_compute_privacy_risks_fn,
)
from tests_e2e.conftest import assert_strict_k_anonymity


def test_all_identical_qis_collapses_into_monolithic_class(uniform_qis_df):
    """50 records sharing identical QIs (City='Amman', Age=30, Gender='M') form exactly 1 class of size 50."""
    k_fn = get_enforce_strict_k_anonymity_fn()
    res = k_fn(uniform_qis_df, qis=["City", "Age", "Gender"], k=5)

    assert res.k_satisfied is True
    assert res.num_equivalence_classes == 1
    assert res.min_equivalence_class_size == len(uniform_qis_df)
    assert res.achieved_k == len(uniform_qis_df)
    assert res.suppression_rate == 0.0
    assert_strict_k_anonymity(res.anonymized_df, ["City", "Age", "Gender"], 5)


def test_all_identical_qis_prosecutor_risk_equals_reciprocal_of_population(uniform_qis_df):
    """When all records collapse into 1 class of size N, Prosecutor risk drops to 1 / N."""
    risk_fn = get_compute_privacy_risks_fn()
    res = risk_fn(uniform_qis_df, qis=["City", "Age", "Gender"])

    n = len(uniform_qis_df)
    expected_risk = round(1.0 / n, 4)
    assert res.prosecutor_risk == expected_risk
    assert res.marketer_risk == expected_risk  # M / N = 1 / 50


def test_all_unique_qis_causes_total_suppression_under_strict_k(all_unique_qis_df):
    """25 completely unique records (all classes of size 1) must be 100% suppressed under K=2."""
    k_fn = get_enforce_strict_k_anonymity_fn()
    res = k_fn(all_unique_qis_df, qis=["City", "Age"], k=2, strategy="record", max_suppression_pct=1.0)

    # Invariant: no singleton classes may be retained
    assert res.retained_records == 0
    assert res.suppressed_records == len(all_unique_qis_df)
    assert res.suppression_rate == 1.0


def test_all_unique_qis_resolved_by_generalization(all_unique_qis_df):
    """Climbing generalization hierarchy aggregates unique records into compliant classes."""
    k_fn = get_enforce_strict_k_anonymity_fn()
    # Generalize Age into a single bin [20-50] and City to '*'
    df_gen = all_unique_qis_df.copy()
    df_gen["Age"] = "[20-50]"
    df_gen["City"] = "Jordan"

    res = k_fn(df_gen, qis=["City", "Age"], k=5, strategy="record")

    assert res.k_satisfied is True
    assert res.retained_records == len(all_unique_qis_df)
    assert res.suppressed_records == 0
    assert res.min_equivalence_class_size >= 5


def test_uniform_sensitive_attribute_fails_l_diversity_above_one(uniform_qis_df):
    """When sensitive attribute is uniform constant across entire dataset, L >= 2 is mathematically impossible."""
    df_const = uniform_qis_df.copy()
    df_const["Category"] = "Gambling"  # Only 1 unique sensitive value in entire dataset

    l_fn = get_evaluate_distinct_l_diversity_fn()
    res = l_fn(df_const, qis=["City"], sensitive_attr="Category", l=2)

    assert res.satisfied is False
    assert res.violating_classes_count == 1
    assert res.min_observed_distinct_values == 1
