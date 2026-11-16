"""
tests_e2e/tier1_features/test_f02_detection_engine.py
Feature 2: Universal Sensitive Attribute Detection Engine.
Validates 4-tier detection across Direct IDs, Quasi-IDs, Sensitive Attributes, and Insensitive columns.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import get_detect_sensitive_attributes_fn


def test_detection_identifies_direct_identifiers(hospital_patient_df: pd.DataFrame):
    detect_fn = get_detect_sensitive_attributes_fn()
    profiles = detect_fn(hospital_patient_df)
    prof_map = {p.column_name: p for p in profiles}

    assert prof_map["Patient_Name"].detected_type == "direct_identifier"
    assert prof_map["MRN"].detected_type == "direct_identifier"
    assert prof_map["National_ID"].detected_type == "direct_identifier"
    assert prof_map["Patient_Name"].confidence >= 0.40


def test_detection_identifies_quasi_identifiers(bank_transactions_df: pd.DataFrame):
    detect_fn = get_detect_sensitive_attributes_fn()
    profiles = detect_fn(bank_transactions_df)
    prof_map = {p.column_name: p for p in profiles}

    assert prof_map["City"].detected_type == "quasi_identifier"
    assert prof_map["Age"].detected_type == "quasi_identifier"
    assert prof_map["Gender"].detected_type == "quasi_identifier"
    assert prof_map["Timestamp"].detected_type == "quasi_identifier"


def test_detection_identifies_sensitive_attributes_multi_industry(
    hospital_patient_df: pd.DataFrame,
    employee_records_df: pd.DataFrame,
    university_students_df: pd.DataFrame
):
    detect_fn = get_detect_sensitive_attributes_fn()

    h_profiles = {p.column_name: p for p in detect_fn(hospital_patient_df)}
    assert h_profiles["ICD10_Code"].detected_type == "sensitive_attribute"
    assert h_profiles["Total_Charges"].detected_type == "sensitive_attribute"

    e_profiles = {p.column_name: p for p in detect_fn(employee_records_df)}
    assert e_profiles["Salary"].detected_type == "sensitive_attribute"

    u_profiles = {p.column_name: p for p in detect_fn(university_students_df)}
    assert u_profiles["GPA"].detected_type == "sensitive_attribute"


def test_detection_preview_masks_direct_identifiers(customer_database_df: pd.DataFrame):
    detect_fn = get_detect_sensitive_attributes_fn()
    profiles = detect_fn(customer_database_df)
    prof_map = {p.column_name: p for p in profiles}

    email_profile = prof_map["Email"]
    assert len(email_profile.sample_values_masked) > 0
    for sample in email_profile.sample_values_masked:
        assert "@customerhub.io" not in sample or "***" in sample or "[MASKED]" in sample


def test_detection_confidence_scores_and_cardinality(employee_records_df: pd.DataFrame):
    detect_fn = get_detect_sensitive_attributes_fn()
    profiles = detect_fn(employee_records_df)

    for p in profiles:
        assert 0.0 <= p.confidence <= 1.0
        assert p.unique_count >= 1
        assert p.null_count == 0
        assert len(p.explanation) > 0


def test_detection_insensitive_attribute_classification():
    detect_fn = get_detect_sensitive_attributes_fn()
    df = pd.DataFrame({
        "System_Version": ["1.0", "1.1", "1.2"],
        "Batch_Status": ["OK", "OK", "OK"],
        "Is_Active": [True, True, False]
    })
    profiles = detect_fn(df)
    for p in profiles:
        assert p.detected_type in ("insensitive", "quasi_identifier")
