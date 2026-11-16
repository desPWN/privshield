"""
tests_e2e/tier1_features/test_f08_l_diversity.py
Feature 8: Distinct, Entropy & Recursive L-Diversity.
Validates distinct sensitive attributes per equivalence class, isolates homogeneity attacks, and audits entropy.
"""

import pandas as pd
import pytest
from tests_e2e.conftest import oracle_verify_distinct_l, oracle_verify_entropy_l
from tests_e2e.test_contracts import get_evaluate_distinct_l_diversity_fn


def test_distinct_l_diversity_satisfied_when_classes_meet_threshold(hospital_patient_df: pd.DataFrame):
    evaluate_l = get_evaluate_distinct_l_diversity_fn()
    qis = ["Zip_Code"]
    audit = evaluate_l(hospital_patient_df, qis=qis, sensitive_attr="ICD10_Code", l=2)

    assert audit.satisfied is True
    assert audit.violating_classes_count == 0
    assert audit.min_observed_distinct_values >= 2


def test_distinct_l_diversity_flags_homogeneity_attack():
    df = pd.DataFrame({
        "City": ["Boston", "Boston", "Boston", "Austin", "Austin"],
        "Diagnosis": ["Cancer", "Cancer", "Cancer", "Flu", "Diabetes"]
    })
    evaluate_l = get_evaluate_distinct_l_diversity_fn()
    audit = evaluate_l(df, qis=["City"], sensitive_attr="Diagnosis", l=2)

    assert audit.satisfied is False
    assert audit.violating_classes_count == 1
    violator = audit.violation_details[0]
    assert violator.distinct_count == 1
    assert "Cancer" in violator.values_present


@pytest.mark.parametrize("target_l", [2, 3, 4])
def test_distinct_l_diversity_across_range(employee_records_df: pd.DataFrame, target_l: int):
    evaluate_l = get_evaluate_distinct_l_diversity_fn()
    qis = ["Department"]
    audit = evaluate_l(employee_records_df, qis=qis, sensitive_attr="Job_Title", l=target_l)
    assert audit.total_classes == employee_records_df["Department"].nunique()
    if audit.satisfied:
        assert audit.min_observed_distinct_values >= target_l


def test_entropy_l_diversity_calculation():
    df = pd.DataFrame({
        "Department": ["Engineering"] * 10 + ["Sales"] * 10,
        "Rating": [1, 2, 3, 4, 5] * 2 + [3, 3, 3, 3, 3, 3, 3, 3, 3, 3]
    })
    qis = ["Department"]
    sat, min_ent, violators = oracle_verify_entropy_l(df, qis=qis, sensitive_col="Rating", l=2)

    # Sales has identical rating (entropy = 0) which strictly violates target entropy log(2)
    assert sat is False
    assert len(violators) >= 1
    assert ("Sales",) in violators


def test_l_diversity_detailed_frequency_breakdown():
    df = pd.DataFrame({
        "City": ["Austin", "Austin", "Austin"],
        "Sensitive": ["A", "B", "B"]
    })
    evaluate_l = get_evaluate_distinct_l_diversity_fn()
    audit = evaluate_l(df, qis=["City"], sensitive_attr="Sensitive", l=3)

    assert audit.satisfied is False
    assert audit.violating_classes_count == 1
    detail = audit.violation_details[0]
    assert detail.distinct_count == 2
    assert detail.frequency_breakdown["B"] == 2
    assert detail.frequency_breakdown["A"] == 1
