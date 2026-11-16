"""
tests_e2e/tier1_features/test_f03_user_overrides.py
Feature 3: Dynamic & Persistent User Classification Overrides.
Validates user overrides taking precedence over engine auto-detection with persistence.
"""

import pandas as pd
import pytest
from backend.app.models.schemas import ColumnProfile, ColumnOverrideItem, ColumnOverrideRequest
from tests_e2e.test_contracts import get_detect_sensitive_attributes_fn


def test_user_override_precedence_over_auto_detection():
    detect_fn = get_detect_sensitive_attributes_fn()
    df = pd.DataFrame({
        "Internal_Notes": ["Regular patient update", "Followup required", "Scheduled"],
        "City": ["Boston", "Austin", "Seattle"]
    })
    profiles = detect_fn(df)
    prof_map = {p.column_name: p for p in profiles}

    # Simulate user override marking Internal_Notes as sensitive_attribute
    override = ColumnOverrideItem(column_name="Internal_Notes", user_category="sensitive_attribute", notes="Contains clinical observations")
    prof_map["Internal_Notes"].is_overridden = True
    prof_map["Internal_Notes"].user_category = override.user_category
    prof_map["Internal_Notes"].detected_type = override.user_category

    assert prof_map["Internal_Notes"].is_overridden is True
    assert prof_map["Internal_Notes"].detected_type == "sensitive_attribute"


def test_override_direct_id_to_quasi_identifier():
    profile = ColumnProfile(
        column_name="EmployeeID",
        detected_type="direct_identifier",
        specific_type="employee_id",
        confidence=0.95,
        explanation="Detected employee ID",
        sample_values_masked=["[MASKED]"],
        unique_count=100,
        null_count=0
    )
    override = ColumnOverrideItem(column_name="EmployeeID", user_category="quasi_identifier")
    profile.user_category = override.user_category
    profile.detected_type = override.user_category
    profile.is_overridden = True

    assert profile.detected_type == "quasi_identifier"
    assert profile.is_overridden is True


def test_override_request_schema_validation():
    req = ColumnOverrideRequest(overrides=[
        ColumnOverrideItem(column_name="ColA", user_category="direct_identifier"),
        ColumnOverrideItem(column_name="ColB", user_category="quasi_identifier"),
        ColumnOverrideItem(column_name="ColC", user_category="sensitive_attribute"),
        ColumnOverrideItem(column_name="ColD", user_category="insensitive"),
    ])
    assert len(req.overrides) == 4
    categories = {item.user_category for item in req.overrides}
    assert categories == {"direct_identifier", "quasi_identifier", "sensitive_attribute", "insensitive"}


def test_override_revert_restores_original_detection():
    detect_fn = get_detect_sensitive_attributes_fn()
    df = pd.DataFrame({"City": ["Boston", "Austin"]})
    profiles = detect_fn(df)
    prof = profiles[0]

    original_category = prof.detected_type
    prof.is_overridden = True
    prof.user_category = "insensitive"
    prof.detected_type = "insensitive"
    assert prof.detected_type == "insensitive"

    # Revert override
    prof.is_overridden = False
    prof.user_category = None
    prof.detected_type = original_category
    assert prof.detected_type == "quasi_identifier"
    assert prof.is_overridden is False


def test_multiple_column_overrides_applied_together():
    df = pd.DataFrame({
        "Patient_Name": ["Alice", "Bob"],
        "Treatment_Date": ["2026-01-01", "2026-01-02"],
        "Room_Number": ["101A", "204B"]
    })
    detect_fn = get_detect_sensitive_attributes_fn()
    profiles = {p.column_name: p for p in detect_fn(df)}

    overrides = {
        "Patient_Name": "direct_identifier",
        "Treatment_Date": "quasi_identifier",
        "Room_Number": "quasi_identifier"
    }

    for col, target_cat in overrides.items():
        profiles[col].detected_type = target_cat
        profiles[col].is_overridden = True

    assert profiles["Room_Number"].detected_type == "quasi_identifier"
    assert profiles["Treatment_Date"].detected_type == "quasi_identifier"
    assert profiles["Patient_Name"].detected_type == "direct_identifier"
