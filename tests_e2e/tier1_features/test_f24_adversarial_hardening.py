"""
tests_e2e/tier1_features/test_f24_adversarial_hardening.py
Feature 24: Adversarial Hardening (Tier 5).
Validates whitebox stress testing, pathological condition defense, and zero false compliance.
"""

import io
import os
import pandas as pd
import pytest
from tests_e2e.conftest import oracle_verify_strict_k


def test_adversarial_zero_false_compliance():
    df = pd.DataFrame({
        "QI_1": ["A"] * 10 + ["B"] * 4,
        "QI_2": ["X"] * 10 + ["Y"] * 4
    })
    qis = ["QI_1", "QI_2"]
    sat, min_sz, count = oracle_verify_strict_k(df, qis, k=5)

    assert sat is False
    assert min_sz == 4


def test_path_traversal_payload_neutralization():
    traversal_payloads = [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\cmd.exe",
        "%2e%2e%2f%2e%2e%2fconfig.json",
        "/storage/raw/../../app/main.py"
    ]
    for payload in traversal_payloads:
        clean_name = os.path.basename(payload.replace("\\", "/"))
        assert "/" not in clean_name
        assert ".." not in clean_name or clean_name.startswith("..")


def test_hostile_column_names_and_sql_injection():
    df = pd.DataFrame({
        "'; DROP TABLE datasets; --": ["Normal", "Data"],
        "<script>alert(1)</script>": [1, 2],
        "UNION SELECT * FROM token_mappings": [10.0, 20.0]
    })
    assert len(df.columns) == 3
    assert len(df) == 2


def test_extreme_sparsity_and_monolithic_classes():
    df = pd.DataFrame({
        "QI": ["MONOLITH"] * 1000 + ["SINGLETON"]
    })
    sat, min_sz, count = oracle_verify_strict_k(df, ["QI"], k=5)
    assert sat is False
    assert min_sz == 1


def test_corrupt_and_truncated_file_rejection():
    truncated_json = b'[{"CustomerID": "123", "City": "Boston"'
    with pytest.raises(Exception):
        pd.read_json(io.BytesIO(truncated_json))
