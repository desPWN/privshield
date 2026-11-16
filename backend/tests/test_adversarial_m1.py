"""
FinGuard Milestone M1 — Adversarial Stress Test Suite
Empirical challenger tests for mathematical engines:
1. Strict K-Anonymity (N % K != 0, N < K, 5+ QI dimensions, N=1, N=0, strict invariant assertion)
2. Distinct L-Diversity (severe homogeneity attack, 100% detection rate)
3. T-Closeness (identical distributions = 0.0, disjoint = max, metric shift sensitivity)
4. Hostile Edge Cases (duplicate index sensitivity in DataFrame)
"""

import pytest
import random
import numpy as np
import pandas as pd

from backend.app.engine.k_anonymity import (
    enforce_strict_k_anonymity,
    partition_equivalence_classes
)
from backend.app.engine.l_diversity import evaluate_distinct_l_diversity
from backend.app.engine.t_closeness import (
    compute_continuous_wasserstein_distance,
    compute_categorical_tvd,
    evaluate_t_closeness
)


# ==============================================================================
# CHALLENGE 1: Strict K-Anonymity
# ==============================================================================

@pytest.mark.parametrize("n,k,strat", [
    (13, 5, "record"),
    (13, 5, "cell"),
    (7, 4, "record"),
    (7, 4, "cell"),
    (99, 7, "record"),
    (99, 7, "cell"),
    (101, 4, "record"),
    (101, 4, "cell"),
    (17, 3, "record"),
    (17, 3, "cell"),
])
def test_strict_k_all_distinct_rows_n_mod_k_nonzero(n: int, k: int, strat: str):
    """
    Construct hostile datasets where every row has a distinct QI signature and N % K != 0.
    Verify that NEVER does any retained equivalence class have size < target_k.
    """
    df = pd.DataFrame({
        "city": [f"City_{i}" for i in range(n)],
        "age": [18 + i for i in range(n)],
        "sensitive": [f"Val_{i}" for i in range(n)]
    })

    anon_df, metrics = enforce_strict_k_anonymity(
        df, qi_columns=["city", "age"], target_k=k, suppression_strategy=strat
    )

    if len(anon_df) > 0:
        ec_map = partition_equivalence_classes(anon_df, ["city", "age"])
        for ec_tuple, members in ec_map.items():
            assert len(members) >= k, f"Equivalence class {ec_tuple} has size {len(members)} < {k}"
        assert metrics["min_equivalence_class_size"] >= k
        assert metrics["k_satisfied"] is True
    else:
        assert metrics["retained_records"] == 0
        assert metrics["suppressed_records"] == n


@pytest.mark.parametrize("n,k", [
    (1, 2),
    (2, 5),
    (4, 10),
    (7, 8),
    (9, 10),
])
def test_strict_k_population_strictly_smaller_than_k(n: int, k: int):
    """
    Construct hostile datasets where N < K.
    Verify that 100% of records are suppressed and 0 classes are retained.
    """
    df = pd.DataFrame({
        "city": [f"City_{i}" for i in range(n)],
        "age": [20 + i * 5 for i in range(n)]
    })

    # Test record suppression
    anon_rec, m_rec = enforce_strict_k_anonymity(df, ["city", "age"], target_k=k, suppression_strategy="record")
    assert len(anon_rec) == 0
    assert m_rec["retained_records"] == 0
    assert m_rec["suppressed_records"] == n
    assert m_rec["suppression_rate"] == 1.0

    # Test cell suppression
    anon_cell, m_cell = enforce_strict_k_anonymity(df, ["city", "age"], target_k=k, suppression_strategy="cell")
    assert len(anon_cell) == 0
    assert m_cell["retained_records"] == 0
    assert m_cell["suppressed_records"] == n
    assert m_cell["suppression_rate"] == 1.0


def test_strict_k_high_dimensional_quasi_identifiers():
    """
    Construct 7-dimensional quasi-identifier space (age, gender, city, merchant, timestamp,
    postal_code, account_type) with sparse combinations.
    Assert that zero retained equivalence classes have size < target_k.
    """
    random.seed(42)
    n = 300
    qis = ["age", "gender", "city", "merchant", "timestamp", "postal_code", "account_type"]
    data = {
        "age": [random.randint(18, 75) for _ in range(n)],
        "gender": [random.choice(["M", "F"]) for _ in range(n)],
        "city": [random.choice(["Amman", "Zarqa", "Irbid", "Aqaba", "Salt"]) for _ in range(n)],
        "merchant": [f"Merch_{random.randint(1, 30)}" for _ in range(n)],
        "timestamp": [f"2026-03-{random.randint(1, 28):02d}T12:00:00" for _ in range(n)],
        "postal_code": [f"11{random.randint(100, 999)}" for _ in range(n)],
        "account_type": [random.choice(["Checking", "Savings", "Payroll"]) for _ in range(n)],
    }
    df = pd.DataFrame(data)

    for target_k in [3, 5, 8]:
        for strat in ["record", "cell"]:
            anon_df, metrics = enforce_strict_k_anonymity(
                df, qi_columns=qis, target_k=target_k, suppression_strategy=strat
            )
            if len(anon_df) > 0:
                ec_map = partition_equivalence_classes(anon_df, qis)
                for ec_tuple, members in ec_map.items():
                    assert len(members) >= target_k, (
                        f"Violation in high-dim {strat} k={target_k}: class size {len(members)}"
                    )
            else:
                assert metrics["retained_records"] == 0


def test_strict_k_single_record_dataset():
    """
    Hostile edge case: Single record dataset (N=1).
    Must suppress the record for all K in 2..10.
    """
    df = pd.DataFrame([{"city": "Amman", "age": 30, "amount": 100.0}])
    for k in range(2, 11):
        anon_df, metrics = enforce_strict_k_anonymity(df, ["city", "age"], target_k=k)
        assert len(anon_df) == 0
        assert metrics["retained_records"] == 0
        assert metrics["suppressed_records"] == 1


def test_strict_k_zero_record_empty_dataframe():
    """
    Hostile edge case: 0-record empty dataframe.
    Must return empty dataframe cleanly with zero divisions or errors.
    """
    df = pd.DataFrame(columns=["city", "age", "amount"])
    for k in range(2, 11):
        anon_df, metrics = enforce_strict_k_anonymity(df, ["city", "age"], target_k=k)
        assert len(anon_df) == 0
        assert metrics["total_records"] == 0
        assert metrics["num_equivalence_classes"] == 0
        assert metrics["k_satisfied"] is True


def test_strict_k_mixed_compliant_and_violating_classes():
    """
    Test dataset where some classes comply with K, and multiple violating classes exist.
    Ensure violators are deterministically resolved and never leak into retained output.
    """
    data = []
    # Class 1: 6 records (compliant for K=5)
    for _ in range(6):
        data.append({"city": "Amman", "age": 25, "id": "c1"})
    # Class 2: 4 records (violating for K=5)
    for _ in range(4):
        data.append({"city": "Zarqa", "age": 30, "id": "c2"})
    # Class 3: 2 records (violating for K=5)
    for _ in range(2):
        data.append({"city": "Irbid", "age": 35, "id": "c3"})
    # Class 4: 1 record (violating for K=5)
    data.append({"city": "Aqaba", "age": 40, "id": "c4"})

    df = pd.DataFrame(data)

    # In record suppression: only Class 1 (6 records) should survive
    anon_rec, m_rec = enforce_strict_k_anonymity(df, ["city", "age"], target_k=5, suppression_strategy="record")
    assert len(anon_rec) == 6
    assert all(anon_rec["city"] == "Amman")
    assert m_rec["num_equivalence_classes"] == 1

    # In cell suppression: violators sum to 4 + 2 + 1 = 7 records.
    # Since 7 >= 5, they form a valid wildcard '*' equivalence class of size 7.
    # Total retained = 6 + 7 = 13.
    anon_cell, m_cell = enforce_strict_k_anonymity(df, ["city", "age"], target_k=5, suppression_strategy="cell")
    assert len(anon_cell) == 13
    assert m_cell["num_equivalence_classes"] == 2
    ec_map = partition_equivalence_classes(anon_cell, ["city", "age"])
    for ec_tuple, members in ec_map.items():
        assert len(members) >= 5


# ==============================================================================
# CHALLENGE 2: Distinct L-Diversity
# ==============================================================================

def test_distinct_l_diversity_severe_homogeneity_attack():
    """
    Construct equivalence class with severe homogeneity: 10 records with the exact
    same sensitive value.
    Verify that evaluate_distinct_l_diversity flags this class 100% of the time.
    """
    for sensitive_val in ["Severe Diagnosis: Cancer", "High Risk Loan Default", "Gambling Activity"]:
        df = pd.DataFrame({
            "qi_city": ["Amman"] * 10,
            "qi_age": [30] * 10,
            "sensitive": [sensitive_val] * 10
        })

        for target_l in [2, 3, 5]:
            audit = evaluate_distinct_l_diversity(
                df, qi_columns=["qi_city", "qi_age"], sensitive_column="sensitive", target_l=target_l
            )
            assert audit.satisfied is False, f"Failed to flag homogeneous class for target_l={target_l}"
            assert audit.violating_classes_count == 1
            assert audit.min_observed_distinct_values == 1
            detail = audit.violation_details[0]
            assert detail.distinct_count == 1
            assert detail.class_size == 10
            assert detail.values_present == [sensitive_val]
            assert detail.frequency_breakdown == {sensitive_val: 10}


def test_distinct_l_diversity_large_scale_homogeneity():
    """
    Construct large equivalence class (1,000 records) with identical sensitive attribute.
    Must flag 100% of the time.
    """
    df = pd.DataFrame({
        "group": ["Cluster_A"] * 1000,
        "sensitive": ["Identical_Value"] * 1000
    })
    audit = evaluate_distinct_l_diversity(df, ["group"], "sensitive", target_l=2)
    assert audit.satisfied is False
    assert audit.violating_classes_count == 1
    assert audit.min_observed_distinct_values == 1
    assert audit.violating_records_count == 1000


def test_distinct_l_diversity_multiple_classes_mixed_homogeneity():
    """
    Construct multi-class dataset:
    - Class 1: 10 records, 5 distinct values (compliant with L=3)
    - Class 2: 10 records, 1 distinct value (severe homogeneity, violating)
    - Class 3: 10 records, 2 distinct values (violating for L=3)
    """
    data = []
    # Class 1
    for i in range(10):
        data.append({"qi": "C1", "sensitive": f"Val_{i % 5}"})
    # Class 2
    for _ in range(10):
        data.append({"qi": "C2", "sensitive": "Homogeneous"})
    # Class 3
    for i in range(10):
        data.append({"qi": "C3", "sensitive": f"Binary_{i % 2}"})

    df = pd.DataFrame(data)
    audit = evaluate_distinct_l_diversity(df, ["qi"], "sensitive", target_l=3)
    assert audit.satisfied is False
    assert audit.total_classes == 3
    assert audit.violating_classes_count == 2
    assert audit.min_observed_distinct_values == 1

    violating_qis = [d.qi_values["qi"] for d in audit.violation_details]
    assert "C1" not in violating_qis
    assert "C2" in violating_qis
    assert "C3" in violating_qis


def test_distinct_l_diversity_all_nulls_homogeneity():
    """
    Construct equivalence class where all sensitive values are NaN/None.
    Should be treated as 1 single category ('[NULL]') and flagged as homogeneous.
    """
    df = pd.DataFrame({
        "qi": ["Group1"] * 8,
        "sensitive": [np.nan] * 8
    })
    audit = evaluate_distinct_l_diversity(df, ["qi"], "sensitive", target_l=2)
    assert audit.satisfied is False
    assert audit.violating_classes_count == 1
    assert audit.min_observed_distinct_values == 1
    assert audit.violation_details[0].values_present == ["[NULL]"]


# ==============================================================================
# CHALLENGE 3: T-Closeness
# ==============================================================================

def test_t_closeness_identical_distributions_zero_distance():
    """
    Identical distributions:
    - Continuous: class distribution identical to global distribution -> EMD == 0.0
    - Categorical: class distribution identical to global distribution -> TVD == 0.0
    """
    # Continuous
    vals = [10.0, 20.0, 30.0, 40.0, 50.0] * 5
    emd = compute_continuous_wasserstein_distance(vals, vals)
    assert emd == 0.0, f"Expected continuous EMD = 0.0, got {emd}"

    # Categorical
    cats = ["Shopping", "Dining", "Transfer", "Bills"] * 5
    tvd = compute_categorical_tvd(cats, cats)
    assert tvd == 0.0, f"Expected categorical TVD = 0.0, got {tvd}"

    # End-to-end evaluation
    df = pd.DataFrame({
        "qi": ["C1"] * 20 + ["C2"] * 20,
        "category": ["A", "B", "C", "D"] * 10,
        "amount": [10.0, 20.0, 30.0, 40.0] * 10
    })
    res_cat = evaluate_t_closeness(df, ["qi"], "category", target_t=0.05)
    assert res_cat.satisfied is True
    assert res_cat.max_observed_distance == 0.0

    res_num = evaluate_t_closeness(df, ["qi"], "amount", target_t=0.05)
    assert res_num.satisfied is True
    assert res_num.max_observed_distance == 0.0


def test_t_closeness_disjoint_distributions_theoretical_maximum():
    """
    Completely disjoint distributions:
    - Categorical TVD reaches theoretical maximum of 1.0.
    - Continuous normalized EMD reaches near 1.0 when mass is concentrated at opposite extremes.
    """
    # Categorical TVD
    class_vals = ["Category_A"] * 50
    global_vals = ["Category_B"] * 50
    tvd = compute_categorical_tvd(class_vals, global_vals)
    assert tvd == 1.0, f"Expected categorical TVD = 1.0 (theoretical maximum), got {tvd}"

    # Continuous normalized EMD
    # 1 item at 0.0 and 999 items at 1000.0. Range is 1000.0.
    # Class values is the single item at 0.0.
    c_vals = [0.0]
    g_vals = [0.0] + [1000.0] * 999
    emd = compute_continuous_wasserstein_distance(c_vals, g_vals)
    assert emd > 0.99, f"Expected continuous EMD to approach 1.0, got {emd}"


def test_t_closeness_wasserstein_metric_distance_shift_sensitivity():
    """
    Verify that Wasserstein-1 distance accurately captures metric distance shifts on R.
    Given a uniform global distribution on [0, 100], classes shifted progressively farther
    from the global center must exhibit strictly monotonic distance growth.
    """
    global_vals = list(range(0, 101))  # Uniform [0, 100]

    # Shifted classes
    class_center = list(range(45, 56))  # Center [45, 55], shift delta = 0
    class_shift1 = list(range(65, 76))  # Shift +20
    class_shift2 = list(range(85, 96))  # Shift +40

    emd_center = compute_continuous_wasserstein_distance(class_center, global_vals)
    emd_shift1 = compute_continuous_wasserstein_distance(class_shift1, global_vals)
    emd_shift2 = compute_continuous_wasserstein_distance(class_shift2, global_vals)

    assert emd_center < emd_shift1 < emd_shift2, (
        f"Wasserstein distance failed monotonicity: {emd_center} < {emd_shift1} < {emd_shift2}"
    )


def test_t_closeness_zero_variance_continuous_distribution():
    """
    Zero-variance distribution where all global values are identical.
    Must gracefully return 0.0 without ZeroDivisionError.
    """
    const_vals = [100.0] * 50
    emd = compute_continuous_wasserstein_distance(const_vals, const_vals)
    assert emd == 0.0


# ==============================================================================
# CHALLENGE 4: Non-Unique / Duplicate Index Edge Case Investigation
# ==============================================================================

def test_k_anonymity_non_unique_index_vulnerability():
    """
    Examines DataFrame with duplicate index labels (e.g., from concatenation or slice).
    Verifies that the engine cleanly handles duplicate indices via positional reset without
    leaking violating rows or raising index collision assertion errors.
    """
    df = pd.DataFrame([
        {"name": "Alice", "city": "Amman", "age": 25},     # idx 0, QI ('Amman', 25)
        {"name": "Eve", "city": "UniqueCity", "age": 99},  # idx 0, QI ('UniqueCity', 99) - VIOLATOR!
        {"name": "Bob", "city": "Amman", "age": 25},       # idx 1, QI ('Amman', 25)
        {"name": "Charlie", "city": "Amman", "age": 25},   # idx 2, QI ('Amman', 25)
    ], index=[0, 0, 1, 2])

    res_df, metrics = enforce_strict_k_anonymity(df, ["city", "age"], target_k=3, suppression_strategy="record")
    assert metrics["k_satisfied"] is True
    assert len(res_df) == 3
    assert "Eve" not in res_df["name"].values
    assert list(res_df["name"].values) == ["Alice", "Bob", "Charlie"]
