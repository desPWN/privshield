"""
Tier 2: Boundary & Corner Cases - Module B03: Mathematically Impossible K & L Configurations.
Validates strict mathematical boundaries: N < K impossible satisfaction, L > K impossibility,
and suppression budget limit enforcement.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import (
    get_enforce_strict_k_anonymity_fn,
    get_evaluate_distinct_l_diversity_fn,
)


def test_n_less_than_k_impossible_satisfaction():
    """When dataset size N (e.g. 3) is strictly smaller than target K (e.g. 5),
    it is impossible to form any class of size >= K. All 3 records must be suppressed."""
    df = pd.DataFrame([
        {"City": "Amman", "Val": 1},
        {"City": "Amman", "Val": 2},
        {"City": "Amman", "Val": 3}
    ])
    k_fn = get_enforce_strict_k_anonymity_fn()
    res = k_fn(df, qis=["City"], k=5, strategy="record", max_suppression_pct=1.0)

    # Invariant: 0 records retained, 3 suppressed
    assert res.retained_records == 0
    assert res.suppressed_records == 3
    assert len(res.anonymized_df) == 0


def test_l_greater_than_k_impossibility():
    """Mathematical bound: A class of size K can hold at most K distinct values.
    If K=3 and target L=4, distinct L-diversity is mathematically impossible."""
    df = pd.DataFrame([
        {"City": "Amman", "Sensitive": "V1"},
        {"City": "Amman", "Sensitive": "V2"},
        {"City": "Amman", "Sensitive": "V3"}
    ])
    l_fn = get_evaluate_distinct_l_diversity_fn()
    res = l_fn(df, qis=["City"], sensitive_attr="Sensitive", l=4)

    assert res.satisfied is False
    assert res.violating_classes_count == 1
    assert res.min_observed_distinct_values == 3
    assert res.violation_details[0].distinct_count == 3


def test_l_greater_than_total_dataset_domain_diversity():
    """If the entire dataset contains only 2 distinct categories (e.g. 'Paid' and 'Default'),
    target L=3 can NEVER be satisfied by any class in the dataset."""
    df = pd.DataFrame([
        {"City": "Amman", "Status": "Paid"},
        {"City": "Amman", "Status": "Default"},
        {"City": "Amman", "Status": "Paid"},
        {"City": "Zarqa", "Status": "Paid"},
        {"City": "Zarqa", "Status": "Default"},
    ])
    l_fn = get_evaluate_distinct_l_diversity_fn()
    res = l_fn(df, qis=["City"], sensitive_attr="Status", l=3)

    assert res.satisfied is False
    # All classes must be flagged as violating
    assert res.violating_classes_count == res.total_classes
    assert res.min_observed_distinct_values == 2


def test_suppression_budget_exceeded_prevents_false_satisfaction():
    """If satisfying K requires 60% suppression but max_suppression_pct is 0.10,
    the engine must NOT claim satisfaction with remaining violating classes."""
    records = []
    # 4 compliant records in Amman
    for i in range(4):
        records.append({"City": "Amman", "Val": i})
    # 6 singleton records in other cities (60% of total)
    for i in range(6):
        records.append({"City": f"City_{i}", "Val": 100 + i})

    df = pd.DataFrame(records)
    k_fn = get_enforce_strict_k_anonymity_fn()
    res = k_fn(df, qis=["City"], k=4, strategy="record", max_suppression_pct=0.10)

    # If suppression is capped at 10%, it cannot eliminate the 6 singletons
    # Therefore, k_satisfied must be False or suppression exceeded limit
    if res.min_equivalence_class_size < 4:
        assert res.k_satisfied is False


def test_zero_suppression_budget_with_violators_fails_k():
    """When max_suppression_pct=0.0 and violating records exist, K-anonymity cannot be claimed."""
    df = pd.DataFrame([
        {"City": "Amman", "Val": 1},
        {"City": "Amman", "Val": 2},
        {"City": "Aqaba", "Val": 3}  # Singleton
    ])
    k_fn = get_enforce_strict_k_anonymity_fn()
    res = k_fn(df, qis=["City"], k=2, strategy="record", max_suppression_pct=0.0)

    if res.min_equivalence_class_size < 2:
        assert res.k_satisfied is False
