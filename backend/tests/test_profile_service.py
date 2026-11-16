"""
Unit tests for PrivShield ProfileService.
Verifies loading 7 pre-built profiles (Healthcare, Finance, Education,
Government, HR, E-commerce, Custom) and applying profiles to dataset column headers.
"""

from backend.app.services.profile_service import ProfileService


def test_list_all_seven_profiles():
    profiles = ProfileService.list_profiles()
    profile_ids = {p.id for p in profiles}

    expected_ids = {"healthcare", "finance", "education", "government", "hr", "ecommerce", "custom"}
    assert expected_ids.issubset(profile_ids), f"Missing profiles: {expected_ids - profile_ids}"
    assert len(profiles) >= 7


def test_get_individual_profiles():
    hc = ProfileService.get_profile("healthcare")
    assert hc is not None
    assert hc.name.startswith("Healthcare")
    assert hc.suggested_rules["k_metric"] == 5
    assert hc.suggested_rules["l_metric"] == 3
    assert hc.suggested_rules["t_metric"] == 0.15

    fin = ProfileService.get_profile("finance")
    assert fin is not None
    assert fin.suggested_rules["k_metric"] == 5

    edu = ProfileService.get_profile("education")
    assert edu is not None
    assert edu.suggested_rules["k_metric"] == 4

    hr = ProfileService.get_profile("hr")
    assert hr is not None
    assert hr.suggested_rules["k_metric"] == 4

    ecom = ProfileService.get_profile("ecommerce")
    assert ecom is not None
    assert ecom.suggested_rules["k_metric"] == 3


def test_apply_profile_to_dataset_columns():
    hospital_cols = [
        "PatientID", "PatientName", "MRN", "SSN", "Phone", "Email",
        "StreetAddress", "Age", "Gender", "City", "PostalCode",
        "AdmissionDate", "DiagnosisCode", "DiagnosisDescription",
        "HospitalCharge"
    ]
    applied = ProfileService.apply_profile_to_dataset("healthcare", hospital_cols)

    assert applied["k_metric"] == 5
    assert applied["l_metric"] == 3
    assert "PatientName" in applied["masking_rules"]
    assert "Age" in applied["quasi_identifiers"]
    assert "City" in applied["quasi_identifiers"]
    assert "DiagnosisCode" in applied["sensitive_attributes"]
    assert "HospitalCharge" in applied["sensitive_attributes"]
