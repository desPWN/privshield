"""
Tier 2: Boundary & Corner Cases - Module B05: Extreme Values & Outliers.
Validates numerical stability under Pareto outliers, multi-million dinar transactions,
negative refunds, and boundary ages.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import (
    get_apply_generalization_fn,
    get_evaluate_t_closeness_fn,
    get_compute_utility_metrics_fn,
)


def test_extreme_amounts_pareto_and_corporate_outliers():
    """Validates multi-million JOD amounts (e.g. 5,000,000.00 JOD) without integer or float overflow."""
    df = pd.DataFrame({
        "Amount": [15.50, 42.00, 150.00, 5000000.00, 25000000.00]
    })
    gen_fn = get_apply_generalization_fn()
    res = gen_fn(df, {"Amount": 1})

    amts = res["Amount"].astype(str).tolist()
    assert "[5000+]" in amts[3] or "5000" in amts[3]
    assert "[5000+]" in amts[4] or "5000" in amts[4]


def test_zero_and_negative_amounts_chargebacks_and_refunds():
    """Negative amounts (-250.50 JOD) representing refunds or reversals are handled without errors."""
    df = pd.DataFrame([
        {"City": "Amman", "Amount": -250.50},
        {"City": "Amman", "Amount": 0.0},
        {"City": "Zarqa", "Amount": 100.0},
        {"City": "Zarqa", "Amount": 200.0}
    ])
    t_fn = get_evaluate_t_closeness_fn()
    res = t_fn(df, qis=["City"], sensitive_attr="Amount", t_threshold=0.50, metric="numeric")

    assert res.total_classes == 2
    assert 0.0 <= res.max_observed_distance <= 1.0


def test_extreme_age_boundaries_youth_and_centenarians():
    """Validates minimum legal banking age (18) and extreme centenarian ages (105)."""
    df = pd.DataFrame({
        "Age": [18, 19, 100, 105]
    })
    gen_fn = get_apply_generalization_fn()
    res_l1 = gen_fn(df, {"Age": 1})

    ages_l1 = res_l1["Age"].astype(str).tolist()
    assert any(c in ages_l1[0] for c in ["18", "20", "24"])
    assert any(c in ages_l1[3] for c in ["65", "100", "+", "Senior"])


def test_utility_analytics_on_skewed_pareto_distributions():
    """Utility metrics maintain stability when comparing heavily skewed financial distributions."""
    df_orig = pd.DataFrame({"Amount": [10.0, 12.0, 15.0, 1000000.0]})
    df_anon = pd.DataFrame({"Amount": [10.0, 12.0, 15.0, 1000000.0]})

    util_fn = get_compute_utility_metrics_fn()
    res = util_fn(original_df=df_orig, anonymized_df=df_anon)

    assert res.numerical_distribution_fidelity == 1.0
    assert res.composite_utility_score == 100.0


def test_t_closeness_resilience_to_near_zero_spread():
    """When difference between max and min is tiny (1e-6), normalizes without floating point explosion."""
    df = pd.DataFrame([
        {"City": "Amman", "Amount": 100.000001},
        {"City": "Amman", "Amount": 100.000002},
        {"City": "Zarqa", "Amount": 100.000001},
        {"City": "Zarqa", "Amount": 100.000002}
    ])
    t_fn = get_evaluate_t_closeness_fn()
    res = t_fn(df, qis=["City"], sensitive_attr="Amount", t_threshold=0.05, metric="numeric")

    assert res.satisfied is True
    assert 0.0 <= res.max_observed_distance <= 1.0
