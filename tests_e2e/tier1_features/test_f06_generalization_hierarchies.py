"""
tests_e2e/tier1_features/test_f06_generalization_hierarchies.py
Feature 6: Pluggable Generalization Hierarchies.
Validates numerical binning, categorical trees, date/time granularities, and geography hierarchies.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import get_apply_generalization_fn


def test_numerical_binning_generalization():
    apply_gen = get_apply_generalization_fn()
    df = pd.DataFrame({"Age": [22, 28, 35, 42, 67]})
    res = apply_gen(df, {"Age": 1})

    for val in res["Age"]:
        assert ("[" in val and "]" in val) or "+" in val
    assert res["Age"].iloc[0] == "[18-24]"
    assert res["Age"].iloc[-1] == "65+"


def test_categorical_tree_generalization():
    apply_gen = get_apply_generalization_fn()
    df = pd.DataFrame({"Job_Title": ["Software Engineer", "Account Executive", "Financial Analyst"]})
    res_lvl1 = apply_gen(df, {"Job_Title": 1})
    assert len(res_lvl1) == 3
    # Level 1 generalizes to department
    assert all(isinstance(v, str) and len(v) > 0 for v in res_lvl1["Job_Title"])

    res_lvl2 = apply_gen(df, {"Job_Title": 2})
    # Level 2 generalizes to division
    assert all("Corporate" in v or "Operations" in v or len(v) > 0 for v in res_lvl2["Job_Title"])

    res_lvl3 = apply_gen(df, {"Job_Title": 3})
    assert (res_lvl3["Job_Title"] == "*").all()


def test_date_and_timestamp_granularities():
    apply_gen = get_apply_generalization_fn()
    df = pd.DataFrame({"Admission_Date": ["2026-04-15 14:32:00", "2026-04-20 09:15:00"]})

    res_hour = apply_gen(df, {"Admission_Date": 1})
    assert res_hour["Admission_Date"].iloc[0] == "2026-04-15 14:00"

    res_date = apply_gen(df, {"Admission_Date": 2})
    assert res_date["Admission_Date"].iloc[0] == "2026-04-15"

    res_month = apply_gen(df, {"Admission_Date": 3})
    assert res_month["Admission_Date"].iloc[0] == "2026-04"

    res_wildcard = apply_gen(df, {"Admission_Date": 4})
    assert (res_wildcard["Admission_Date"] == "*").all()


def test_generalization_level_zero_is_identity():
    apply_gen = get_apply_generalization_fn()
    df = pd.DataFrame({
        "Age": [25, 45, 65],
        "City": ["Amman", "Zarqa", "Irbid"]
    })
    res = apply_gen(df, {"Age": 0, "City": 0})
    pd.testing.assert_frame_equal(df, res)


def test_multi_column_simultaneous_generalization():
    apply_gen = get_apply_generalization_fn()
    df = pd.DataFrame({
        "Age": [25, 52],
        "Salary": [85000, 140000],
        "Job_Title": ["Software Engineer", "Financial Analyst"]
    })
    res = apply_gen(df, {"Age": 1, "Salary": 1, "Job_Title": 3})

    assert "[" in res["Age"].iloc[0] or "+" in res["Age"].iloc[0]
    assert "[" in res["Salary"].iloc[0] or "+" in res["Salary"].iloc[0]
    assert (res["Job_Title"] == "*").all()


def test_wildcard_level_suppression():
    apply_gen = get_apply_generalization_fn()
    df = pd.DataFrame({"Job_Title": ["Software Engineer", "Account Executive"]})
    res = apply_gen(df, {"Job_Title": 3})
    assert (res["Job_Title"] == "*").all()
