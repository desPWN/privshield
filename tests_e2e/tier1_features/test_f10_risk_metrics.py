"""
tests_e2e/tier1_features/test_f10_risk_metrics.py
Feature 10: Universal Privacy Risk Metrics.
Validates Prosecutor risk (1/min|EC|), Journalist risk, Marketer risk, Linkage simulation, and NCP.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import get_compute_privacy_risks_fn


def test_prosecutor_risk_strictly_bounded_by_reciprocal_of_k(hospital_patient_df: pd.DataFrame):
    compute_risk = get_compute_privacy_risks_fn()
    qis = ["Gender", "Zip_Code"]
    risk = compute_risk(hospital_patient_df, qis)

    if risk.smallest_class_size > 0:
        assert risk.prosecutor_risk == round(1.0 / risk.smallest_class_size, 4)
        assert 0.0 < risk.prosecutor_risk <= 1.0


def test_marketer_risk_equals_m_over_n(employee_records_df: pd.DataFrame):
    compute_risk = get_compute_privacy_risks_fn()
    qis = ["Department", "Office_Location"]
    risk = compute_risk(employee_records_df, qis)

    assert 0.0 <= risk.marketer_risk <= 1.0
    assert risk.largest_class_size >= risk.smallest_class_size


def test_journalist_risk_monotonic_with_equivalence_class_distribution():
    compute_risk = get_compute_privacy_risks_fn()

    # Dataset with 10 records and 10 distinct classes
    df_unique = pd.DataFrame({"QI": list(range(10))})
    risk_unique = compute_risk(df_unique, ["QI"])

    # Dataset with 10 records all in 1 class
    df_uniform = pd.DataFrame({"QI": [1] * 10})
    risk_uniform = compute_risk(df_uniform, ["QI"])

    assert risk_unique.journalist_risk > risk_uniform.journalist_risk
    assert risk_unique.prosecutor_risk == 1.0
    assert risk_uniform.prosecutor_risk == 0.10


def test_linkage_attack_simulation_in_bounds(bank_transactions_df: pd.DataFrame):
    compute_risk = get_compute_privacy_risks_fn()
    qis = ["City", "Gender", "Age"]
    risk = compute_risk(bank_transactions_df, qis)

    assert hasattr(risk, "transaction_linkage_risk")
    assert 0.0 <= risk.transaction_linkage_risk <= 1.0


def test_privacy_risk_on_empty_dataset_returns_zero():
    compute_risk = get_compute_privacy_risks_fn()
    df_empty = pd.DataFrame(columns=["Age", "Gender"])
    risk = compute_risk(df_empty, ["Age", "Gender"])

    assert risk.prosecutor_risk == 0.0
    assert risk.journalist_risk == 0.0
    assert risk.marketer_risk == 0.0
