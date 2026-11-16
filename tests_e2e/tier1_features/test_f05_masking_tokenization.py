"""
tests_e2e/tier1_features/test_f05_masking_tokenization.py
Feature 5: Universal Data Masking & Tokenization.
Validates email, phone, card, IBAN, SSN, IP, residential address masking and tokenization.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import get_apply_masking_fn, format_preserving_token


def test_email_and_phone_masking():
    apply_mask = get_apply_masking_fn()
    df = pd.DataFrame({
        "Email": ["alice.smith@hospital.org", "bob@bank.com"],
        "Phone": ["+1-555-123-4567", "+962 79 123 4567"]
    })
    res = apply_mask(df, {"Email": "email", "Phone": "phone"})

    for val in res["Email"]:
        assert "@" in val
        assert not val.startswith("alice.smith@")
        assert "*" in val

    for val in res["Phone"]:
        assert "****" in val
        assert val.endswith("567")


def test_card_and_iban_masking():
    apply_mask = get_apply_masking_fn()
    df = pd.DataFrame({
        "Card_Number": ["4111222233334444", "5500111122223333"],
        "IBAN": ["GB29NWBK60161331926819", "JO94ARAB00000000000012345678"]
    })
    res = apply_mask(df, {"Card_Number": "card", "IBAN": "iban"})

    for val in res["Card_Number"]:
        assert val.endswith("4444") or val.endswith("3333")
        assert "••••" in val or "****" in val

    for val in res["IBAN"]:
        assert val.startswith("GB29") or val.startswith("JO94")
        assert "****" in val


def test_ssn_and_ip_address_masking():
    apply_mask = get_apply_masking_fn()
    df = pd.DataFrame({
        "SSN": ["123-45-6789", "987-65-4321"],
        "IP_Address": ["192.168.1.105", "10.0.4.25"]
    })
    res = apply_mask(df, {"SSN": "ssn", "IP_Address": "ip"})

    for val in res["SSN"]:
        assert "*" in val
        assert val.endswith("6789") or val.endswith("4321")

    for val in res["IP_Address"]:
        assert "***" in val
        assert "192.168." in val or "10.0." in val


def test_residential_address_and_generic_redaction():
    apply_mask = get_apply_masking_fn()
    df = pd.DataFrame({
        "Address": ["742 Evergreen Terrace", "221B Baker Street"],
        "Sensitive_Notes": ["Confidential patient note", "Secret memo"]
    })
    res = apply_mask(df, {"Address": "address", "Sensitive_Notes": "redact"})

    for val in res["Address"]:
        assert "***" in val

    for val in res["Sensitive_Notes"]:
        assert val == "[REDACTED]"


def test_format_preserving_tokenization_fpt():
    val1 = "Patient-MRN-9092"
    val2 = "Patient-MRN-9092"
    val3 = "Patient-MRN-1011"

    tok1 = format_preserving_token(val1, prefix="TOK")
    tok2 = format_preserving_token(val2, prefix="TOK")
    tok3 = format_preserving_token(val3, prefix="TOK")

    assert tok1 == tok2, "Deterministic FPT must produce identical tokens for identical input"
    assert tok1 != tok3, "Distinct inputs must yield distinct format-preserving tokens"
    assert tok1.startswith("TOK-")


def test_masking_preserves_unspecified_columns():
    apply_mask = get_apply_masking_fn()
    df = pd.DataFrame({
        "Email": ["user@test.org"],
        "Age": [34],
        "City": ["Boston"]
    })
    res = apply_mask(df, {"Email": "email"})
    assert res["Age"].iloc[0] == 34
    assert res["City"].iloc[0] == "Boston"
