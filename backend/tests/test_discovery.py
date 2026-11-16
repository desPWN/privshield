"""
Unit tests for FinGuard Sensitive Data Discovery Engine.
Verifies column heuristics, regex/checksum validators, confidence calculation, and overrides.
"""

import pandas as pd

from backend.app.engine.discovery import (
    calculate_shannon_entropy,
    calculate_uniqueness_ratio,
    discover_column,
    discover_dataset,
    validate_iban_mod97,
    validate_luhn,
)


def test_iban_mod97_validator():
    # Valid Jordanian IBANs
    assert validate_iban_mod97("JO53ARAB1302930989111742989417") is True
    # Invalid check digits
    assert validate_iban_mod97("JO00ARAB1302930989111742989417") is False
    assert validate_iban_mod97("INVALID_IBAN") is False
    assert validate_iban_mod97("") is False


def test_luhn_validator():
    # Valid Luhn card numbers
    assert validate_luhn("4123 1338 9083 8637") is True
    assert validate_luhn("4123133890838637") is True
    # Invalid Luhn card number
    assert validate_luhn("4123 1338 9083 8638") is False
    assert validate_luhn("12345") is False
    assert validate_luhn("") is False


def test_shannon_entropy_and_uniqueness():
    s_unique = pd.Series([f"val_{i}" for i in range(100)])
    assert calculate_uniqueness_ratio(s_unique) == 1.0
    assert calculate_shannon_entropy(s_unique) > 6.0

    s_constant = pd.Series(["constant"] * 100)
    assert calculate_uniqueness_ratio(s_constant) == 0.01
    assert calculate_shannon_entropy(s_constant) == 0.0

    s_empty = pd.Series([], dtype=str)
    assert calculate_uniqueness_ratio(s_empty) == 0.0
    assert calculate_shannon_entropy(s_empty) == 0.0


def test_discover_dataset_classification():
    data = {
        "FullName": ["Ahmad Al-Majali", "Rania Haddad", "Omar Al-Zubi"],
        "NationalID": ["9981240192", "2001849102", "9840194821"],
        "Email": ["ahmad@gmail.com", "rania@orange.jo", "omar@yahoo.com"],
        "Phone": ["+962 79 123 4567", "+962 78 234 5678", "+962 77 345 6789"],
        "IBAN": ["JO53ARAB1302930989111742989417", "JO66BJOR1420717258441666044838", "JO53ARAB1302930989111742989417"],
        "Age": [34, 25, 42],
        "Gender": ["M", "F", "M"],
        "City": ["Amman", "Zarqa", "Irbid"],
        "TransactionAmount": [45.50, 120.00, 310.25],
        "TransactionCategory": ["Shopping", "Bills & Utilities", "Restaurant"],
        "IsSynthetic": [True, True, True]
    }
    df = pd.DataFrame(data)
    profiles = discover_dataset(df)
    prof_dict = {p.column_name: p for p in profiles}

    # Direct Identifiers
    assert prof_dict["FullName"].detected_type == "direct_identifier"
    assert prof_dict["NationalID"].detected_type == "direct_identifier"
    assert prof_dict["Email"].detected_type == "direct_identifier"
    assert prof_dict["Phone"].detected_type == "direct_identifier"
    assert prof_dict["IBAN"].detected_type == "direct_identifier"

    # Quasi-Identifiers
    assert prof_dict["Age"].detected_type == "quasi_identifier"
    assert prof_dict["Gender"].detected_type == "quasi_identifier"
    assert prof_dict["City"].detected_type == "quasi_identifier"

    # Sensitive Attributes
    assert prof_dict["TransactionAmount"].detected_type == "sensitive_attribute"
    assert prof_dict["TransactionCategory"].detected_type == "sensitive_attribute"

    # Masked previews check
    assert "****" in prof_dict["NationalID"].sample_values_masked[0]
    assert "@" in prof_dict["Email"].sample_values_masked[0]
    assert "*" in prof_dict["Email"].sample_values_masked[0]


def test_discover_dataset_user_overrides():
    df = pd.DataFrame({
        "TransactionAmount": [10.0, 20.0, 30.0],
        "Age": [20, 30, 40]
    })
    overrides = {"TransactionAmount": "quasi_identifier"}
    profiles = discover_dataset(df, overrides=overrides)
    prof_dict = {p.column_name: p for p in profiles}

    assert prof_dict["TransactionAmount"].detected_type == "quasi_identifier"
    assert prof_dict["TransactionAmount"].is_overridden is True
    assert prof_dict["TransactionAmount"].user_category == "quasi_identifier"
    assert prof_dict["Age"].is_overridden is False


def test_discover_column_individual():
    s = pd.Series(["jafar@arab-bank.jo", "nour@gmail.com"])
    profile = discover_column("Email", s)
    assert profile.detected_type == "direct_identifier"
    assert profile.specific_type == "email"
    assert profile.confidence >= 0.80
