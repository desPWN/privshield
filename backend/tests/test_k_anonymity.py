"""
Unit tests for FinGuard Strict K-Anonymity Engine.
Verifies strict K invariant, equivalence class partitioning, violation suppression,
and hostile boundary conditions.
"""

import pandas as pd

from backend.app.engine.k_anonymity import (
    enforce_strict_k_anonymity,
    partition_equivalence_classes,
)


def test_strict_k_satisfaction_with_suppression():
    # 10 records: 6 in class A, 4 in class B. With target_k=5, class B (size 4) must be suppressed!
    data = {
        "City": ["Amman"] * 6 + ["Zarqa"] * 4,
        "Gender": ["M"] * 6 + ["F"] * 4,
        "Amount": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    }
    df = pd.DataFrame(data)
    anon_df, metrics = enforce_strict_k_anonymity(
        df,
        qi_columns=["City", "Gender"],
        target_k=5,
        suppression_strategy="record"
    )

    assert metrics["k_satisfied"] is True
    assert metrics["achieved_k"] >= 5
    assert len(anon_df) == 6
    assert metrics["suppressed_records"] == 4
    assert metrics["min_equivalence_class_size"] >= 5

    # Verify that NO retained equivalence class has size < 5
    final_ec = partition_equivalence_classes(anon_df, ["City", "Gender"])
    for qi, indices in final_ec.items():
        assert len(indices) >= 5, f"Class {qi} has size {len(indices)} < 5"


def test_cell_suppression_strategy():
    # 10 records: 6 in class A, 4 in class B. Under cell suppression, if violating records >= K,
    # they get masked to (*, *). But 4 < 5, so even wildcard class is smaller than 5, leading to record suppression!
    data = {
        "City": ["Amman"] * 6 + ["Zarqa"] * 4,
        "Amount": [10.0] * 10
    }
    df = pd.DataFrame(data)
    anon_df, metrics = enforce_strict_k_anonymity(
        df,
        qi_columns=["City"],
        target_k=5,
        suppression_strategy="cell"
    )
    assert metrics["k_satisfied"] is True
    assert metrics["achieved_k"] >= 5
    assert len(anon_df) == 6


def test_boundary_empty_dataset():
    df = pd.DataFrame(columns=["City", "Gender", "Amount"])
    anon_df, metrics = enforce_strict_k_anonymity(df, qi_columns=["City", "Gender"], target_k=5)
    assert len(anon_df) == 0
    assert metrics["k_satisfied"] is True
    assert metrics["achieved_k"] == 0
    assert metrics["total_records"] == 0


def test_boundary_single_row():
    # 1 record cannot satisfy K=2 -> must be 100% suppressed
    df = pd.DataFrame({"City": ["Amman"], "Gender": ["M"], "Amount": [50.0]})
    anon_df, metrics = enforce_strict_k_anonymity(df, qi_columns=["City", "Gender"], target_k=2)
    assert len(anon_df) == 0
    assert metrics["suppressed_records"] == 1
    assert metrics["k_satisfied"] is True
    assert metrics["achieved_k"] == 0


def test_boundary_population_smaller_than_k():
    # 3 records with target_k=5 -> 100% suppressed
    df = pd.DataFrame({"City": ["Amman", "Zarqa", "Irbid"], "Gender": ["M", "F", "M"]})
    anon_df, metrics = enforce_strict_k_anonymity(df, qi_columns=["City", "Gender"], target_k=5)
    assert len(anon_df) == 0
    assert metrics["suppressed_records"] == 3
    assert metrics["k_satisfied"] is True


def test_boundary_all_identical_rows():
    # 10 identical rows form 1 equivalence class of size 10 -> satisfies K=5 trivially without suppression
    df = pd.DataFrame({"City": ["Amman"] * 10, "Gender": ["M"] * 10})
    anon_df, metrics = enforce_strict_k_anonymity(df, qi_columns=["City", "Gender"], target_k=5)
    assert len(anon_df) == 10
    assert metrics["suppressed_records"] == 0
    assert metrics["num_equivalence_classes"] == 1
    assert metrics["min_equivalence_class_size"] == 10
    assert metrics["achieved_k"] == 10
    assert metrics["k_satisfied"] is True


def test_boundary_all_unique_rows_with_generalization():
    # 8 unique cities, generalized to Region (all Central Region) -> forms class of size 8, satisfying K=5
    cities = ["Amman", "Zarqa", "Salt", "Madaba", "Amman", "Zarqa", "Salt", "Madaba"]
    df = pd.DataFrame({"City": cities, "Gender": ["M"] * 8})
    anon_df, metrics = enforce_strict_k_anonymity(
        df,
        qi_columns=["City", "Gender"],
        target_k=5,
        generalization_levels={"City": 2}  # Level 2 = Region (Central Region)
    )
    assert metrics["k_satisfied"] is True
    assert len(anon_df) == 8
    assert metrics["suppressed_records"] == 0
    assert (anon_df["City"] == "Central Region").all()
