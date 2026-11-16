import pytest
import numpy as np
import pandas as pd
from backend.app.engine.k_anonymity import (
    enforce_strict_k_anonymity,
    partition_equivalence_classes,
)


def test_k_anonymity_all_identical_scalar_index():
    n_compliant = 10
    n_violating = 3
    target_k = 5

    compliant_rows = [
        {"id": f"C_{i}", "city": "Amman", "age": 30, "salary": 1000 + i * 10}
        for i in range(n_compliant)
    ]
    violating_rows = [
        {"id": f"V_{i}", "city": "Zarqa", "age": 45, "salary": 2000 + i * 10}
        for i in range(n_violating)
    ]

    total_rows = compliant_rows + violating_rows
    # Every single row has index label 999
    df = pd.DataFrame(total_rows, index=[999] * len(total_rows))

    res_rec, m_rec = enforce_strict_k_anonymity(
        df, ["city", "age"], target_k=target_k, suppression_strategy="record"
    )

    assert m_rec["k_satisfied"] is True
    assert len(res_rec) == n_compliant
    assert set(res_rec["id"]) == {f"C_{i}" for i in range(n_compliant)}
    assert not any(vid in res_rec["id"].values for vid in ["V_0", "V_1", "V_2"])
    assert res_rec.index.is_unique
    assert list(res_rec.index) == list(range(n_compliant))


def test_k_anonymity_scrambled_negative_and_duplicate_integers():
    df = pd.DataFrame([
        {"id": "A1", "city": "Amman", "age": 25},
        {"id": "V1", "city": "Unique1", "age": 90},
        {"id": "A2", "city": "Amman", "age": 25},
        {"id": "V2", "city": "Unique2", "age": 91},
        {"id": "A3", "city": "Amman", "age": 25},
        {"id": "A4", "city": "Amman", "age": 25},
        {"id": "V3", "city": "Unique3", "age": 92},
    ], index=[-50, 100, -50, 0, 100, -50, 999999])

    res, m = enforce_strict_k_anonymity(
        df, ["city", "age"], target_k=4, suppression_strategy="record"
    )

    assert m["k_satisfied"] is True
    assert len(res) == 4
    assert set(res["id"]) == {"A1", "A2", "A3", "A4"}
    assert not any(v in res["id"].values for v in ["V1", "V2", "V3"])
    assert res.index.is_unique
    assert list(res.index) == [0, 1, 2, 3]


def test_k_anonymity_string_and_special_character_indices():
    df = pd.DataFrame([
        {"id": "G1_1", "city": "Irbid", "age": 22},
        {"id": "G1_2", "city": "Irbid", "age": 22},
        {"id": "G1_3", "city": "Irbid", "age": 22},
        {"id": "V1", "city": "Aqaba", "age": 60},
        {"id": "G2_1", "city": "Amman", "age": 40},
        {"id": "G2_2", "city": "Amman", "age": 40},
        {"id": "G2_3", "city": "Amman", "age": 40},
    ], index=["row_dup", "row_dup", "special_!#$", "row_dup", "special_!#$", "xyz", "xyz"])

    res, m = enforce_strict_k_anonymity(
        df, ["city", "age"], target_k=3, suppression_strategy="record"
    )

    assert m["k_satisfied"] is True
    assert len(res) == 6
    assert set(res["id"]) == {"G1_1", "G1_2", "G1_3", "G2_1", "G2_2", "G2_3"}
    assert "V1" not in res["id"].values
    assert res.index.is_unique


def test_k_anonymity_multiindex_with_collisions():
    multi_idx = pd.MultiIndex.from_tuples([
        ("North", 10),
        ("North", 10),
        ("South", 20),
        ("North", 10),
        ("South", 20),
        ("South", 20),
        ("East", 99),
    ], names=["region", "code"])

    df = pd.DataFrame([
        {"id": "C1", "city": "Amman", "age": 30},
        {"id": "C2", "city": "Amman", "age": 30},
        {"id": "C3", "city": "Amman", "age": 30},
        {"id": "C4", "city": "Amman", "age": 30},
        {"id": "C5", "city": "Amman", "age": 30},
        {"id": "C6", "city": "Amman", "age": 30},
        {"id": "V1", "city": "Salt", "age": 80},
    ], index=multi_idx)

    res, m = enforce_strict_k_anonymity(
        df, ["city", "age"], target_k=5, suppression_strategy="record"
    )

    assert m["k_satisfied"] is True
    assert len(res) == 6
    assert set(res["id"]) == {"C1", "C2", "C3", "C4", "C5", "C6"}
    assert "V1" not in res["id"].values
    assert res.index.is_unique
    # Verify no accidental columns from index reset
    assert "region" not in res.columns
    assert "code" not in res.columns


def test_k_anonymity_float_and_nan_indices():
    df = pd.DataFrame([
        {"id": "K1", "city": "Amman", "age": 20},
        {"id": "K2", "city": "Amman", "age": 20},
        {"id": "K3", "city": "Amman", "age": 20},
        {"id": "BAD", "city": "Mafraq", "age": 70},
    ], index=[1.5, np.nan, 1.5, np.nan])

    res, m = enforce_strict_k_anonymity(
        df, ["city", "age"], target_k=3, suppression_strategy="record"
    )

    assert m["k_satisfied"] is True
    assert len(res) == 3
    assert set(res["id"]) == {"K1", "K2", "K3"}
    assert "BAD" not in res["id"].values
    assert res.index.is_unique


def test_k_anonymity_generalization_with_duplicate_indices():
    # 2 rows Amman, 2 rows Zarqa. With city level 2 (Region), both map to "Central Region"
    # Target K = 4. Without generalization they violate K=4. With generalization they merge to 4.
    df = pd.DataFrame([
        {"id": "R1", "city": "Amman", "age": 25},
        {"id": "R2", "city": "Amman", "age": 25},
        {"id": "R3", "city": "Zarqa", "age": 25},
        {"id": "R4", "city": "Zarqa", "age": 25},
        {"id": "V1", "city": "Aqaba", "age": 90},
    ], index=[42, 42, 42, 42, 42])

    res, m = enforce_strict_k_anonymity(
        df,
        qi_columns=["city", "age"],
        target_k=4,
        generalization_levels={"city": 2},
        suppression_strategy="record",
    )

    assert m["k_satisfied"] is True
    assert len(res) == 4
    assert set(res["id"]) == {"R1", "R2", "R3", "R4"}
    assert "V1" not in res["id"].values
    assert (res["city"] == "Central Region").all()
    assert res.index.is_unique


def test_k_anonymity_cell_suppression_with_hostile_duplicate_index():
    # 4 compliant, 4 violators. Target K = 3.
    # In cell suppression, 4 violators are >= target_k -> generalized to '*' wildcard class.
    df = pd.DataFrame([
        {"id": "C1", "city": "Amman", "age": 25},
        {"id": "C2", "city": "Amman", "age": 25},
        {"id": "C3", "city": "Amman", "age": 25},
        {"id": "C4", "city": "Amman", "age": 25},
        {"id": "V1", "city": "CityA", "age": 10},
        {"id": "V2", "city": "CityB", "age": 20},
        {"id": "V3", "city": "CityC", "age": 30},
        {"id": "V4", "city": "CityD", "age": 40},
    ], index=[1, 1, 1, 1, 1, 1, 1, 1])

    res, m = enforce_strict_k_anonymity(
        df, ["city", "age"], target_k=3, suppression_strategy="cell"
    )

    assert m["k_satisfied"] is True
    assert len(res) == 8
    assert res.index.is_unique
    assert list(res.index) == list(range(8))

    # Check that compliant class retained original QIs
    c_part = res[res["id"].isin(["C1", "C2", "C3", "C4"])]
    assert (c_part["city"] == "Amman").all()
    assert (c_part["age"] == 25).all()

    # Check that violators are masked with '*'
    v_part = res[res["id"].isin(["V1", "V2", "V3", "V4"])]
    assert (v_part["city"] == "*").all()
    assert (v_part["age"] == "*").all()


def test_k_anonymity_cell_suppression_insufficient_wildcard_under_duplicate_index():
    # 3 compliant, 2 violators. Target K = 3.
    # Violators count = 2 < 3, so even wildcard class is suppressed.
    df = pd.DataFrame([
        {"id": "C1", "city": "Amman", "age": 25},
        {"id": "C2", "city": "Amman", "age": 25},
        {"id": "C3", "city": "Amman", "age": 25},
        {"id": "V1", "city": "CityA", "age": 10},
        {"id": "V2", "city": "CityB", "age": 20},
    ], index=[7, 7, 7, 7, 7])

    res, m = enforce_strict_k_anonymity(
        df, ["city", "age"], target_k=3, suppression_strategy="cell"
    )

    assert m["k_satisfied"] is True
    assert len(res) == 3
    assert set(res["id"]) == {"C1", "C2", "C3"}
    assert not any(v in res["id"].values for v in ["V1", "V2"])
    assert res.index.is_unique


@pytest.mark.parametrize("strat", ["record", "cell"])
def test_k_anonymity_large_scale_severe_duplicate_index(strat: str):
    rng = np.random.default_rng(42)
    target_k = 6

    # 4 distinct classes:
    # Class 1: 300 rows (Amman, 30) -> Compliant
    # Class 2: 150 rows (Irbid, 40) -> Compliant
    # Class 3: 4 rows (Zarqa, 50) -> Violating
    # Class 4: 1 row (Aqaba, 60) -> Violating
    rows = []
    for i in range(300):
        rows.append({"id": f"A_{i}", "city": "Amman", "age": 30, "cat": "C1"})
    for i in range(150):
        rows.append({"id": f"B_{i}", "city": "Irbid", "age": 40, "cat": "C2"})
    for i in range(4):
        rows.append({"id": f"V1_{i}", "city": "Zarqa", "age": 50, "cat": "V1"})
    rows.append({"id": "V2_0", "city": "Aqaba", "age": 60, "cat": "V2"})

    # Intentionally scramble order
    rng.shuffle(rows)

    # Use only 3 repeated index values across all 455 rows
    indices = [0, 1, 2] * (len(rows) // 3) + [0] * (len(rows) % 3)
    df = pd.DataFrame(rows, index=indices)

    res, m = enforce_strict_k_anonymity(
        df, ["city", "age"], target_k=target_k, suppression_strategy=strat
    )

    assert m["k_satisfied"] is True
    assert res.index.is_unique
    assert len(res) == len(res["id"].unique()), "Duplicate rows detected in output!"

    # In record suppression: 450 compliant rows retained, 5 violating rows dropped.
    # In cell suppression: 5 violators < target_k=6, so wildcard cannot meet K -> also dropped!
    assert len(res) == 450
    assert not any("V" in id_val for id_val in res["id"].values)

    ec_map = partition_equivalence_classes(res, ["city", "age"])
    for ec_tuple, members in ec_map.items():
        assert len(members) >= target_k
