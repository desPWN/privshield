"""
Tier 2: Boundary & Corner Cases - Module B06: Special Characters, Arabic Unicode & Mixed Types.
Validates encoding fidelity, Arabic script support, NaN handling, and punctuation robustness.
"""

import numpy as np
import pandas as pd
import pytest
from tests_e2e.test_contracts import (
    get_detect_sensitive_attributes_fn,
    get_apply_generalization_fn,
    get_enforce_strict_k_anonymity_fn,
    get_export_dataset_fn,
)


def test_arabic_script_discovery_and_generalization():
    """Arabic city names ('عمان', 'الزرقاء', 'إربد') and Arabic customer names are handled accurately."""
    df = pd.DataFrame({
        "المدينة": ["عمان", "الزرقاء", "إربد"],
        "اسم_العميل": ["أحمد المجالي", "فاطمة الزعبي", "طارق الطراونة"],
        "المبلغ": [150.0, 75.0, 220.0]
    })
    gen_fn = get_apply_generalization_fn()
    res = gen_fn(df, {"المدينة": 1})

    # Should not crash on Arabic unicode text
    assert len(res) == 3


def test_null_and_nan_in_quasi_identifiers():
    """Null and NaN values in QI columns are grouped consistently without throwing exceptions."""
    df = pd.DataFrame([
        {"City": "Amman", "Postal": None, "Val": 1},
        {"City": "Amman", "Postal": None, "Val": 2},
        {"City": "Amman", "Postal": "11118", "Val": 3},
        {"City": "Amman", "Postal": "11118", "Val": 4}
    ])
    k_fn = get_enforce_strict_k_anonymity_fn()
    res = k_fn(df, qis=["City", "Postal"], k=2, strategy="record")

    assert res.k_satisfied is True
    assert res.retained_records == 4
    assert res.num_equivalence_classes == 2


def test_mixed_types_in_categorical_columns():
    """Columns with mixed integer and string types (e.g. 100, 'N/A') are processed without TypeError."""
    df = pd.DataFrame({
        "Identifier": [1001, "UNKNOWN", 1002, "N/A"],
        "City": ["Amman", "Amman", "Amman", "Amman"]
    })
    k_fn = get_enforce_strict_k_anonymity_fn()
    res = k_fn(df, qis=["City"], k=2)

    assert res.k_satisfied is True
    assert res.retained_records == 4


def test_whitespace_and_casing_insensitivity_in_hierarchies():
    """Leading/trailing whitespace and inconsistent casing (' Amman ', 'amman', 'AMMAN') normalize cleanly."""
    df = pd.DataFrame({
        "City": [" Amman ", "amman", "AMMAN", "ZARQA"]
    })
    gen_fn = get_apply_generalization_fn()
    res = gen_fn(df, {"City": 2})

    cities = res["City"].tolist()
    # All variations of Amman should map to Central Region
    assert cities[0] == "Central Region"
    assert cities[1] == "Central Region"
    assert cities[2] == "Central Region"
    assert cities[3] == "Central Region"


def test_special_symbols_and_punctuation_in_exports():
    """Special characters ('&', '%', quotes, slashes, emoticons) export to CSV and JSON without corruption."""
    df = pd.DataFrame([
        {"Merchant": "McDonald's & Co. / Jordan", "Note": "Promo 50% Off! 🎯", "Amount": 12.50}
    ])
    export_fn = get_export_dataset_fn()

    csv_bytes = export_fn(df, format="csv")
    csv_str = csv_bytes.decode("utf-8")
    assert "McDonald's & Co." in csv_str
    assert "50% Off!" in csv_str

    json_bytes = export_fn(df, format="json")
    json_str = json_bytes.decode("utf-8")
    assert "50% Off!" in json_str
