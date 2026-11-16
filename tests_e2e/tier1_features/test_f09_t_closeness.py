"""
tests_e2e/tier1_features/test_f09_t_closeness.py
Feature 9: Continuous EMD & Categorical TVD T-Closeness.
Validates 1D Wasserstein-1 distance for numerical attributes and Total Variation Distance for categorical attributes.
"""

import pandas as pd
import pytest
from tests_e2e.conftest import oracle_wasserstein_1d, oracle_total_variation_distance
from tests_e2e.test_contracts import get_evaluate_t_closeness_fn


def test_continuous_wasserstein_emd_calculation(bank_transactions_df: pd.DataFrame):
    evaluate_t = get_evaluate_t_closeness_fn()
    qis = ["City"]
    audit = evaluate_t(
        bank_transactions_df,
        qis=qis,
        sensitive_attr="Transaction_Amount",
        t_threshold=0.50,
        metric="numeric"
    )
    assert audit.attribute_type == "numeric"
    assert audit.max_observed_distance <= 1.0
    assert audit.average_distance >= 0.0


def test_categorical_total_variation_distance(hospital_patient_df: pd.DataFrame):
    evaluate_t = get_evaluate_t_closeness_fn()
    qis = ["Zip_Code"]
    audit = evaluate_t(
        hospital_patient_df,
        qis=qis,
        sensitive_attr="ICD10_Code",
        t_threshold=0.60,
        metric="categorical"
    )
    assert audit.attribute_type == "categorical"
    assert 0.0 <= audit.max_observed_distance <= 1.0


def test_t_closeness_detects_distributional_skewness():
    df = pd.DataFrame({
        "City": ["Boston"] * 10 + ["Austin"] * 10,
        "Income": [20000] * 10 + [250000] * 10
    })
    evaluate_t = get_evaluate_t_closeness_fn()
    # Global distribution has extreme spread. Boston class is heavily skewed to lower tail.
    audit = evaluate_t(df, qis=["City"], sensitive_attr="Income", t_threshold=0.10, metric="numeric")

    assert audit.satisfied is False
    assert audit.violating_classes_count >= 1
    assert audit.max_observed_distance > 0.10


def test_t_closeness_distances_strictly_bounded_unit_interval():
    class_vals = [10.0, 20.0, 30.0]
    global_vals = [100.0, 200.0, 300.0]
    dist_num = oracle_wasserstein_1d(class_vals, global_vals)
    assert 0.0 <= dist_num <= 1.0

    cat_class = ["A", "A", "B"]
    cat_global = ["C", "D", "E"]
    dist_cat = oracle_total_variation_distance(cat_class, cat_global)
    assert 0.0 <= dist_cat <= 1.0


def test_t_closeness_identical_distributions_yield_zero_distance():
    vals = [10.0, 20.0, 30.0, 40.0]
    dist_num = oracle_wasserstein_1d(vals, vals)
    assert dist_num == 0.0

    cats = ["X", "Y", "Z"]
    dist_cat = oracle_total_variation_distance(cats, cats)
    assert dist_cat == 0.0
