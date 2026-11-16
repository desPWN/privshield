"""
Unit tests for FinGuard Distinct L-Diversity Evaluator.
Verifies sensitivity diversity audit, violation detection, offending value reporting,
and edge cases.
"""

import pandas as pd

from backend.app.engine.l_diversity import evaluate_distinct_l_diversity


def test_distinct_l_diversity_satisfied():
    # Class has 3 distinct categories: Shopping, Transfer, Bills -> satisfies L=3
    df = pd.DataFrame({
        "City": ["Amman"] * 6,
        "Gender": ["M"] * 6,
        "Category": ["Shopping", "Shopping", "Transfer", "Transfer", "Bills", "Bills"]
    })
    res = evaluate_distinct_l_diversity(df, qi_columns=["City", "Gender"], sensitive_column="Category", target_l=3)
    assert res.satisfied is True
    assert res.violating_classes_count == 0
    assert res.min_observed_distinct_values == 3


def test_distinct_l_diversity_violating():
    # Class has only 2 distinct categories: Shopping and Transfer -> fails L=3
    df = pd.DataFrame({
        "City": ["Amman"] * 5,
        "Gender": ["M"] * 5,
        "Category": ["Shopping", "Shopping", "Shopping", "Transfer", "Transfer"]
    })
    res = evaluate_distinct_l_diversity(df, qi_columns=["City", "Gender"], sensitive_column="Category", target_l=3)
    assert res.satisfied is False
    assert res.violating_classes_count == 1
    assert res.violating_records_count == 5
    assert res.min_observed_distinct_values == 2

    # Check violation details
    v_detail = res.violation_details[0]
    assert v_detail.distinct_count == 2
    assert set(v_detail.values_present) == {"Shopping", "Transfer"}
    assert v_detail.frequency_breakdown == {"Shopping": 3, "Transfer": 2}


def test_homogeneity_attack_scenario():
    # Class has only 1 distinct category (all records are "Gambling") -> complete privacy failure for L >= 2
    df = pd.DataFrame({
        "City": ["Amman"] * 10,
        "Category": ["Gambling"] * 10
    })
    res = evaluate_distinct_l_diversity(df, qi_columns=["City"], sensitive_column="Category", target_l=2)
    assert res.satisfied is False
    assert res.min_observed_distinct_values == 1
    assert res.violation_details[0].values_present == ["Gambling"]


def test_boundary_empty_dataset():
    df = pd.DataFrame(columns=["City", "Category"])
    res = evaluate_distinct_l_diversity(df, qi_columns=["City"], sensitive_column="Category", target_l=2)
    assert res.satisfied is True
    assert res.total_classes == 0
    assert res.violating_classes_count == 0
