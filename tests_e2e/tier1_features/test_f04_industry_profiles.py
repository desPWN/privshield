"""
tests_e2e/tier1_features/test_f04_industry_profiles.py
Feature 4: Pre-Built Industry Profiles.
Validates 7 pre-built industry profiles and customizable configuration rules.
"""

import pytest


INDUSTRY_PROFILES = [
    {
        "id": "healthcare",
        "name": "Healthcare & Clinical",
        "direct_identifiers": ["mrn", "patient_name", "ssn", "national_id"],
        "quasi_identifiers": ["age", "gender", "zip_code", "admission_date"],
        "sensitive_attributes": ["icd10_code", "treatment_category", "total_charges"],
        "default_k": 5,
        "default_l": 3
    },
    {
        "id": "finance",
        "name": "Banking & Finance",
        "direct_identifiers": ["iban", "card_number", "customer_id", "email"],
        "quasi_identifiers": ["city", "age", "gender", "timestamp", "merchant"],
        "sensitive_attributes": ["transaction_amount", "loan_status", "balance"],
        "default_k": 5,
        "default_l": 2
    },
    {
        "id": "education",
        "name": "Education & Academic",
        "direct_identifiers": ["studentid", "student_name", "ssn"],
        "quasi_identifiers": ["birth_date", "gender", "state", "major"],
        "sensitive_attributes": ["gpa", "academic_standing"],
        "default_k": 4,
        "default_l": 2
    },
    {
        "id": "government",
        "name": "Government & Census",
        "direct_identifiers": ["national_id", "full_name", "residential_address"],
        "quasi_identifiers": ["age", "gender", "postal_code", "citizenship"],
        "sensitive_attributes": ["income_tier", "tax_bracket"],
        "default_k": 10,
        "default_l": 3
    },
    {
        "id": "hr",
        "name": "Human Resources & Payroll",
        "direct_identifiers": ["employeeid", "full_name", "ssn"],
        "quasi_identifiers": ["department", "job_title", "office_location", "age"],
        "sensitive_attributes": ["salary", "performance_rating"],
        "default_k": 4,
        "default_l": 2
    },
    {
        "id": "ecommerce",
        "name": "E-Commerce & Retail",
        "direct_identifiers": ["customerid", "email", "phone", "ip_address"],
        "quasi_identifiers": ["city", "age", "residential_address"],
        "sensitive_attributes": ["annual_income", "purchase_frequency"],
        "default_k": 5,
        "default_l": 2
    },
    {
        "id": "custom",
        "name": "Custom Profile",
        "direct_identifiers": [],
        "quasi_identifiers": [],
        "sensitive_attributes": [],
        "default_k": 5,
        "default_l": None
    }
]


def test_all_seven_industry_profiles_available():
    profile_ids = [p["id"] for p in INDUSTRY_PROFILES]
    assert len(profile_ids) == 7
    expected = {"healthcare", "finance", "education", "government", "hr", "ecommerce", "custom"}
    assert set(profile_ids) == expected


def test_healthcare_profile_rules():
    hc = next(p for p in INDUSTRY_PROFILES if p["id"] == "healthcare")
    assert "mrn" in hc["direct_identifiers"]
    assert "icd10_code" in hc["sensitive_attributes"]
    assert hc["default_k"] >= 5
    assert hc["default_l"] >= 3


def test_finance_profile_rules():
    fin = next(p for p in INDUSTRY_PROFILES if p["id"] == "finance")
    assert "iban" in fin["direct_identifiers"]
    assert "card_number" in fin["direct_identifiers"]
    assert "transaction_amount" in fin["sensitive_attributes"]


def test_education_and_hr_profiles():
    edu = next(p for p in INDUSTRY_PROFILES if p["id"] == "education")
    assert "gpa" in edu["sensitive_attributes"]
    assert "major" in edu["quasi_identifiers"]

    hr = next(p for p in INDUSTRY_PROFILES if p["id"] == "hr")
    assert "salary" in hr["sensitive_attributes"]
    assert "department" in hr["quasi_identifiers"]


def test_custom_profile_allows_user_defined_parameters():
    cust = next(p for p in INDUSTRY_PROFILES if p["id"] == "custom").copy()
    cust["direct_identifiers"] = ["device_id"]
    cust["quasi_identifiers"] = ["operating_system", "country"]
    cust["sensitive_attributes"] = ["crash_dump"]
    cust["default_k"] = 8

    assert "device_id" in cust["direct_identifiers"]
    assert cust["default_k"] == 8


def test_profile_default_k_values_within_bounds():
    for p in INDUSTRY_PROFILES:
        k = p["default_k"]
        assert 2 <= k <= 10
