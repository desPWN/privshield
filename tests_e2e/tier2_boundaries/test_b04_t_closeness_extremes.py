"""
Tier 2: Boundary & Corner Cases - Module B04: T-Closeness Boundary Extremes.
Validates behavior at extreme thresholds (T=0.0 and T=1.0), zero-spread continuous distributions,
and maximum divergence configurations.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import get_evaluate_t_closeness_fn


def test_t_closeness_boundary_t_one_is_maximally_permissive():
    """At threshold T=1.0, any distribution divergence is accommodated; all classes must satisfy."""
    df = pd.DataFrame([
        {"City": "Amman", "Amount": 10.0},
        {"City": "Zarqa", "Amount": 10000.0}
    ])
    t_fn = get_evaluate_t_closeness_fn()
    res = t_fn(df, qis=["City"], sensitive_attr="Amount", t_threshold=1.0, metric="numeric")

    assert res.satisfied is True
    assert res.violating_classes_count == 0


def test_t_closeness_boundary_t_zero_requires_exact_distribution_match():
    """At threshold T=0.0, even a microscopic distribution difference causes a violation."""
    df = pd.DataFrame([
        {"City": "Amman", "Cat": "A"},
        {"City": "Amman", "Cat": "B"},
        {"City": "Zarqa", "Cat": "A"},
        {"City": "Zarqa", "Cat": "A"}  # 100% A vs 50% A in Amman -> divergence > 0
    ])
    t_fn = get_evaluate_t_closeness_fn()
    res = t_fn(df, qis=["City"], sensitive_attr="Cat", t_threshold=0.0, metric="categorical")

    assert res.satisfied is False
    assert res.violating_classes_count >= 1


def test_t_closeness_zero_variance_continuous_attribute():
    """When continuous values have zero spread (max == min, e.g. all 150.0), avoids ZeroDivisionError and distance is 0.0."""
    df = pd.DataFrame([
        {"City": "Amman", "Amount": 150.0},
        {"City": "Amman", "Amount": 150.0},
        {"City": "Zarqa", "Amount": 150.0},
        {"City": "Zarqa", "Amount": 150.0}
    ])
    t_fn = get_evaluate_t_closeness_fn()
    res = t_fn(df, qis=["City"], sensitive_attr="Amount", t_threshold=0.05, metric="numeric")

    assert res.satisfied is True
    assert res.max_observed_distance == 0.0


def test_t_closeness_single_equivalence_class_has_zero_distance():
    """When all records belong to 1 equivalence class, local distribution == global distribution (distance = 0.0)."""
    df = pd.DataFrame([
        {"City": "Amman", "Amount": 10.0},
        {"City": "Amman", "Amount": 50.0},
        {"City": "Amman", "Amount": 200.0}
    ])
    t_fn = get_evaluate_t_closeness_fn()
    res = t_fn(df, qis=["City"], sensitive_attr="Amount", t_threshold=0.01, metric="numeric")

    assert res.satisfied is True
    assert res.max_observed_distance == 0.0


def test_t_closeness_disjoint_categories_yields_maximum_distance_one():
    """When classes have mutually disjoint categories, distance (0.50) exceeds strict threshold T=0.20."""
    df = pd.DataFrame([
        {"City": "Amman", "Cat": "OnlyAmmanCategory"},
        {"City": "Zarqa", "Cat": "OnlyZarqaCategory"}
    ])
    t_fn = get_evaluate_t_closeness_fn()
    res = t_fn(df, qis=["City"], sensitive_attr="Cat", t_threshold=0.20, metric="categorical")

    assert res.satisfied is False
    assert res.max_observed_distance == 0.50
