"""
Unit tests for FinGuard Privacy Risk and Data Utility Analytics.
Verifies Prosecutor, Journalist, Marketer risk models, 5-component CURS formula,
relative errors, and boundary conditions.
"""

import pandas as pd
import pytest

from backend.app.engine.risk import compute_privacy_risk_metrics
from backend.app.engine.utility import compute_ks_fidelity, compute_utility_metrics


def test_privacy_risk_metrics():
    # 3 classes: sizes 5, 10, 20. Total records = 35
    ec_sizes = [5, 10, 20]
    total_records = 35
    metrics = compute_privacy_risk_metrics(ec_sizes, total_records)

    # Prosecutor risk: 1 / min(|EC|) = 1 / 5 = 0.20
    assert metrics.prosecutor_risk == pytest.approx(0.20, abs=1e-4)
    # Marketer risk: M / N = 3 / 35 = 0.0857
    assert metrics.marketer_risk == pytest.approx(3 / 35, abs=1e-4)
    assert metrics.smallest_class_size == 5
    assert metrics.largest_class_size == 20
    assert metrics.average_class_size == pytest.approx(35 / 3, abs=0.1)
    assert metrics.k_achieved == 5


def test_privacy_risk_boundary_empty():
    metrics = compute_privacy_risk_metrics([], 0)
    assert metrics.prosecutor_risk == 0.0
    assert metrics.journalist_risk == 0.0
    assert metrics.k_achieved == 0


def test_curs_identical_datasets():
    # If original and anonymized datasets are identical and no generalization was applied:
    # CURS must be 100%
    data = {
        "Age": [25, 30, 35, 40, 45],
        "Amount": [10.0, 20.0, 30.0, 40.0, 50.0],
        "Category": ["Shopping", "Bills", "Dining", "Shopping", "Bills"]
    }
    df = pd.DataFrame(data)
    util = compute_utility_metrics(df, df, quasi_identifiers=["Age"])

    assert util.record_retention == 1.0
    assert util.numerical_distribution_fidelity == 1.0
    assert util.categorical_distribution_fidelity == 1.0
    assert util.correlation_retention == 1.0
    assert util.granularity_retention == 1.0
    assert util.composite_utility_score == pytest.approx(100.0, abs=0.01)
    assert util.suppressed_records == 0
    assert util.suppression_rate == 0.0


def test_curs_with_generalization_and_suppression():
    orig_data = {
        "Age": [20, 25, 30, 35, 40, 45, 50, 55, 60, 65],
        "Amount": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
        "Category": ["Shopping"] * 5 + ["Bills"] * 5
    }
    orig_df = pd.DataFrame(orig_data)

    # Anonymized data has 2 records suppressed (8 records retained) and Age generalized by 1 level
    anon_df = orig_df.iloc[:8].copy()
    util = compute_utility_metrics(
        orig_df,
        anon_df,
        quasi_identifiers=["Age"],
        generalization_levels={"Age": 1},
        max_hierarchy_depth=3
    )

    assert util.record_retention == 0.80
    assert util.suppressed_records == 2
    assert util.suppression_rate == 0.20
    # CURS should be strictly bounded between 0 and 100
    assert 0.0 <= util.composite_utility_score <= 100.0
    # Granularity retention for level 1 of 3: 1 - 1/3 = 0.67
    assert util.granularity_retention == pytest.approx(0.6667, abs=1e-3)


def test_curs_complete_suppression():
    # 100% suppression -> CURS must be 0%
    orig_df = pd.DataFrame({"Amount": [10.0, 20.0, 30.0]})
    empty_df = orig_df.iloc[0:0].copy()
    util = compute_utility_metrics(orig_df, empty_df)

    assert util.record_retention == 0.0
    assert util.composite_utility_score == 0.0
    assert util.suppressed_records == 3
    assert util.suppression_rate == 1.0


def test_ks_fidelity():
    s1 = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    s2 = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    fidelity = compute_ks_fidelity(s1, s2)
    assert fidelity == pytest.approx(1.0, abs=1e-6)
