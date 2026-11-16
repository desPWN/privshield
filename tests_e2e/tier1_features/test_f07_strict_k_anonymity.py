"""
tests_e2e/tier1_features/test_f07_strict_k_anonymity.py
Feature 7: Strict K-Anonymity Engine.
Enforces the invariant min(|EC_j|) >= K across all equivalence classes with zero violating classes.
"""

import pandas as pd
import pytest
from tests_e2e.conftest import assert_strict_k_anonymity, oracle_equivalence_classes
from tests_e2e.test_contracts import get_enforce_strict_k_anonymity_fn


def test_strict_k_anonymity_enforced_across_all_classes(hospital_patient_df: pd.DataFrame):
    enforce_k = get_enforce_strict_k_anonymity_fn()
    qis = ["Gender", "Zip_Code"]
    res = enforce_k(hospital_patient_df, qis=qis, k=5)

    anon_df = res.anonymized_df if hasattr(res, "anonymized_df") else res[0]
    assert_strict_k_anonymity(anon_df, qis, target_k=5)

    ec_map = oracle_equivalence_classes(anon_df, qis)
    for key, idxs in ec_map.items():
        assert len(idxs) >= 5, f"Equivalence class {key} has size {len(idxs)} < 5"


@pytest.mark.parametrize("target_k", [2, 3, 5, 8, 10])
def test_strict_k_anonymity_across_k_range(bank_transactions_df: pd.DataFrame, target_k: int):
    enforce_k = get_enforce_strict_k_anonymity_fn()
    qis = ["City", "Gender"]
    res = enforce_k(bank_transactions_df, qis=qis, k=target_k)

    anon_df = res.anonymized_df if hasattr(res, "anonymized_df") else res[0]
    if len(anon_df) > 0:
        assert_strict_k_anonymity(anon_df, qis, target_k=target_k)
        assert res.min_equivalence_class_size >= target_k


def test_strict_k_anonymity_achieved_k_equals_min_class_size(employee_records_df: pd.DataFrame):
    enforce_k = get_enforce_strict_k_anonymity_fn()
    qis = ["Department", "Office_Location"]
    res = enforce_k(employee_records_df, qis=qis, k=4)

    anon_df = res.anonymized_df if hasattr(res, "anonymized_df") else res[0]
    if len(anon_df) > 0:
        ec_map = oracle_equivalence_classes(anon_df, qis)
        min_ec = min(len(v) for v in ec_map.values())
        assert res.achieved_k == min_ec
        assert res.min_equivalence_class_size == min_ec


def test_strict_k_anonymity_suppression_rate_within_budget(university_students_df: pd.DataFrame):
    enforce_k = get_enforce_strict_k_anonymity_fn()
    qis = ["State", "Gender"]
    res = enforce_k(university_students_df, qis=qis, k=4, max_suppression_pct=0.60)

    assert res.suppression_rate <= 0.60
    assert res.total_records == len(university_students_df)
    assert res.retained_records + res.suppressed_records == res.total_records


def test_strict_k_anonymity_rejects_false_satisfaction():
    df = pd.DataFrame({
        "City": ["Boston", "Boston", "Austin"],
        "Age": [30, 30, 45],
        "Value": [10, 20, 30]
    })
    qis = ["City", "Age"]
    ec_map = oracle_equivalence_classes(df, qis)
    sizes = [len(v) for v in ec_map.values()]
    min_size = min(sizes)
    # Target K=2 is violated because ('Austin', 45) has size 1
    assert min_size == 1
    assert min_size < 2
