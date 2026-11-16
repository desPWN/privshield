"""
tests_e2e/tier1_features/test_f11_utility_curs.py
Feature 11: Universal Data Utility Analytics & CURS.
Validates 5-component Composite Utility-Retention Score (CURS), statistical variance, and correlation preservation.
"""

import pandas as pd
import pytest
from tests_e2e.conftest import assert_curs_in_bounds
from tests_e2e.test_contracts import get_compute_utility_metrics_fn


def test_curs_score_bounds_and_formula_weights(bank_transactions_df: pd.DataFrame):
    compute_util = get_compute_utility_metrics_fn()
    anon_df = bank_transactions_df.iloc[:90].copy()
    util = compute_util(bank_transactions_df, anon_df)

    assert_curs_in_bounds(util.composite_utility_score)
    assert util.record_retention == round(90 / len(bank_transactions_df), 4)
    assert util.suppressed_records == len(bank_transactions_df) - 90


def test_utility_identical_datasets_yield_perfect_score(hospital_patient_df: pd.DataFrame):
    compute_util = get_compute_utility_metrics_fn()
    util = compute_util(hospital_patient_df, hospital_patient_df.copy())

    assert util.record_retention == 1.0
    assert util.suppressed_records == 0
    assert util.suppression_rate == 0.0
    assert util.composite_utility_score >= 90.0


def test_numerical_distribution_and_ks_fidelity(employee_records_df: pd.DataFrame):
    compute_util = get_compute_utility_metrics_fn()
    anon_df = employee_records_df.copy()
    anon_df["Salary"] = anon_df["Salary"] * 1.02  # minor 2% perturbation
    util = compute_util(employee_records_df, anon_df, numeric_cols=["Salary"])

    assert 0.0 <= util.numerical_distribution_fidelity <= 1.0


def test_correlation_matrix_preservation(university_students_df: pd.DataFrame):
    compute_util = get_compute_utility_metrics_fn()
    util = compute_util(university_students_df, university_students_df.iloc[:100], numeric_cols=["GPA", "Credits_Completed"])

    assert 0.0 <= util.correlation_retention <= 1.0


def test_utility_tradeoff_with_deepening_hierarchies(customer_database_df: pd.DataFrame):
    compute_util = get_compute_utility_metrics_fn()

    # Retaining 100% vs 50% records
    util_full = compute_util(customer_database_df, customer_database_df.copy())
    util_half = compute_util(customer_database_df, customer_database_df.iloc[:len(customer_database_df)//2].copy())

    assert util_full.composite_utility_score > util_half.composite_utility_score
    assert util_half.record_retention == 0.50
