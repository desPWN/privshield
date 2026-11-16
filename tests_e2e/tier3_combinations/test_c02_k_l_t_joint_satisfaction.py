"""
Tier 3: Cross-Feature Combinations - Module C02: Joint K-L-T Satisfaction Verification.
Validates combined privacy verification across K-anonymity, Distinct L-diversity, and T-closeness,
preventing false compliance when any sub-model fails.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import (
    get_apply_generalization_fn,
    get_enforce_strict_k_anonymity_fn,
    get_evaluate_distinct_l_diversity_fn,
    get_evaluate_t_closeness_fn,
)
from tests_e2e.conftest import (
    assert_strict_k_anonymity,
    assert_distinct_l_diversity,
    assert_t_closeness,
)


def test_joint_k_l_t_simultaneous_satisfaction():
    """Validates simultaneous compliance across (K=3, L=2, T=0.25) on a well-distributed dataset."""
    records = []
    # 2 equivalence classes, each with 4 records and 2 categories, amounts matching global range
    for i in range(4):
        records.append({"City": "Amman", "Cat": "Shopping" if i % 2 == 0 else "Dining", "Amount": float(10 + i * 20)})
    for i in range(4):
        records.append({"City": "Zarqa", "Cat": "Shopping" if i % 2 == 0 else "Dining", "Amount": float(15 + i * 20)})

    df = pd.DataFrame(records)
    qis = ["City"]

    k_fn = get_enforce_strict_k_anonymity_fn()
    l_fn = get_evaluate_distinct_l_diversity_fn()
    t_fn = get_evaluate_t_closeness_fn()

    res_k = k_fn(df, qis=qis, k=3)
    res_l = l_fn(res_k.anonymized_df, qis=qis, sensitive_attr="Cat", l=2)
    res_t = t_fn(res_k.anonymized_df, qis=qis, sensitive_attr="Amount", t_threshold=0.25, metric="numeric")

    assert res_k.k_satisfied is True
    assert res_l.satisfied is True
    assert res_t.satisfied is True

    assert_strict_k_anonymity(res_k.anonymized_df, qis, 3)
    assert_distinct_l_diversity(res_k.anonymized_df, qis, "Cat", 2)
    assert_t_closeness(res_k.anonymized_df, qis, "Amount", 0.25, is_numeric=True)


def test_k_satisfied_but_l_diversity_violated_homogeneity_attack():
    """Dataset satisfies K=4, but class 1 contains homogeneous sensitive values (fails L=2)."""
    records = [
        # Class 1: Amman (4 records, all 'Default' -> fails L=2)
        {"City": "Amman", "Status": "Default", "Amount": 100.0},
        {"City": "Amman", "Status": "Default", "Amount": 120.0},
        {"City": "Amman", "Status": "Default", "Amount": 110.0},
        {"City": "Amman", "Status": "Default", "Amount": 130.0},
        # Class 2: Zarqa (4 records, diverse -> passes L=2)
        {"City": "Zarqa", "Status": "Paid", "Amount": 50.0},
        {"City": "Zarqa", "Status": "Current", "Amount": 70.0},
        {"City": "Zarqa", "Status": "Paid", "Amount": 80.0},
        {"City": "Zarqa", "Status": "Current", "Amount": 90.0},
    ]
    df = pd.DataFrame(records)
    qis = ["City"]

    k_fn = get_enforce_strict_k_anonymity_fn()
    l_fn = get_evaluate_distinct_l_diversity_fn()

    res_k = k_fn(df, qis=qis, k=4)
    res_l = l_fn(res_k.anonymized_df, qis=qis, sensitive_attr="Status", l=2)

    # K is satisfied (min class size is 4 >= 4)
    assert res_k.k_satisfied is True
    # L is violated because Amman has only 1 distinct status
    assert res_l.satisfied is False
    assert res_l.violating_classes_count == 1
    assert res_l.violation_details[0].qi_values["City"] == "Amman"


def test_k_and_l_satisfied_but_t_closeness_violated_skewness_attack():
    """Dataset satisfies K=3 and L=2, but class 2 amounts are heavily skewed (fails T=0.15)."""
    records = [
        # Class 1: Modest amounts (10, 20, 30 JOD)
        {"City": "Amman", "Cat": "A", "Amount": 10.0},
        {"City": "Amman", "Cat": "B", "Amount": 20.0},
        {"City": "Amman", "Cat": "A", "Amount": 30.0},
        # Class 2: Extreme amounts (10,000, 20,000, 30,000 JOD)
        {"City": "Zarqa", "Cat": "A", "Amount": 10000.0},
        {"City": "Zarqa", "Cat": "B", "Amount": 20000.0},
        {"City": "Zarqa", "Cat": "A", "Amount": 30000.0},
    ]
    df = pd.DataFrame(records)
    qis = ["City"]

    k_fn = get_enforce_strict_k_anonymity_fn()
    l_fn = get_evaluate_distinct_l_diversity_fn()
    t_fn = get_evaluate_t_closeness_fn()

    res_k = k_fn(df, qis=qis, k=3)
    res_l = l_fn(res_k.anonymized_df, qis=qis, sensitive_attr="Cat", l=2)
    res_t = t_fn(res_k.anonymized_df, qis=qis, sensitive_attr="Amount", t_threshold=0.15, metric="numeric")

    assert res_k.k_satisfied is True
    assert res_l.satisfied is True
    # T-closeness is violated due to massive distribution gap
    assert res_t.satisfied is False
    assert res_t.violating_classes_count >= 1


def test_joint_k_l_t_on_synthetic_jordanian_dataset(synthetic_jordanian_df):
    """Evaluates (K=3, L=2, T=0.35) on the synthetic Jordanian dataset."""
    gen_fn = get_apply_generalization_fn()
    k_fn = get_enforce_strict_k_anonymity_fn()
    l_fn = get_evaluate_distinct_l_diversity_fn()
    t_fn = get_evaluate_t_closeness_fn()

    # Generalize City to Region (Level 2)
    df_gen = gen_fn(synthetic_jordanian_df, {"City": 2})
    qis = ["City", "Gender"]

    res_k = k_fn(df_gen, qis=qis, k=3, strategy="record")
    assert res_k.k_satisfied is True

    res_l = l_fn(res_k.anonymized_df, qis=qis, sensitive_attr="Category", l=2)
    assert res_l.satisfied is True

    res_t = t_fn(res_k.anonymized_df, qis=qis, sensitive_attr="Transaction_Amount", t_threshold=0.35)
    assert res_t.max_observed_distance <= 1.0
