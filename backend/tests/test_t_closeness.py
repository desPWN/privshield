"""
Unit tests for FinGuard T-Closeness Evaluator.
Verifies continuous 1D Earth Mover's Distance (Wasserstein-1) and categorical
Total Variation Distance (TVD), violation detection, and mathematical edge cases.
"""

import pandas as pd
import pytest

from backend.app.engine.t_closeness import (
    compute_categorical_tvd,
    compute_continuous_wasserstein_distance,
    evaluate_t_closeness,
)


def test_wasserstein_continuous_identical_distributions():
    vals = [10.0, 20.0, 30.0, 40.0, 50.0]
    dist = compute_continuous_wasserstein_distance(vals, vals)
    assert dist == pytest.approx(0.0, abs=1e-6)


def test_wasserstein_continuous_constant_attribute():
    # Constant values have zero variance -> distance is 0.0
    vals = [100.0, 100.0, 100.0]
    dist = compute_continuous_wasserstein_distance(vals, vals)
    assert dist == 0.0


def test_wasserstein_continuous_shift():
    # Global distribution: [0, 100]
    # Class values at extreme upper end [90, 100] vs global uniform
    global_vals = [0.0, 25.0, 50.0, 75.0, 100.0]
    class_vals = [90.0, 100.0]
    dist = compute_continuous_wasserstein_distance(class_vals, global_vals)
    assert 0.0 < dist <= 1.0


def test_categorical_tvd_identical():
    cats = ["Shopping", "Transfer", "Bills"]
    tvd = compute_categorical_tvd(cats, cats)
    assert tvd == pytest.approx(0.0, abs=1e-6)


def test_categorical_tvd_disjoint():
    # Completely disjoint category sets -> TVD = 1.0
    class_cats = ["Gambling"]
    global_cats = ["Shopping", "Transfer"]
    tvd = compute_categorical_tvd(class_cats, global_cats)
    assert tvd == pytest.approx(1.0, abs=1e-6)


def test_evaluate_t_closeness_numeric_and_categorical():
    data = {
        "City": ["Amman"] * 5 + ["Zarqa"] * 5,
        "Amount": [10.0, 20.0, 30.0, 40.0, 50.0, 15.0, 25.0, 35.0, 45.0, 55.0],
        "Category": ["Shopping", "Shopping", "Transfer", "Bills", "Bills",
                     "Shopping", "Bills", "Transfer", "Shopping", "Bills"]
    }
    df = pd.DataFrame(data)

    # Numeric evaluation
    res_num = evaluate_t_closeness(df, qi_columns=["City"], sensitive_column="Amount", target_t=0.30)
    assert res_num.attribute_type == "numeric"
    assert res_num.total_classes == 2
    assert res_num.average_distance >= 0.0

    # Categorical evaluation
    res_cat = evaluate_t_closeness(df, qi_columns=["City"], sensitive_column="Category", target_t=0.30)
    assert res_cat.attribute_type == "categorical"
    assert res_cat.total_classes == 2


def test_boundary_empty_dataset():
    df = pd.DataFrame(columns=["City", "Amount"])
    res = evaluate_t_closeness(df, qi_columns=["City"], sensitive_column="Amount", target_t=0.20)
    assert res.satisfied is True
    assert res.total_classes == 0
    assert res.violating_classes_count == 0
