"""
Unit tests for FinGuard Domain Generalization Hierarchies.
Tests Jordanian geographic hierarchy, demographic age bins, amount tiers, and timestamp truncation.
"""

import pandas as pd

from backend.app.engine.hierarchies import (
    HierarchyRegistry,
    generalize_age,
    generalize_amount,
    generalize_category,
    generalize_city,
    generalize_timestamp,
)


def test_jordan_city_hierarchy():
    # Level 0 (Raw)
    assert generalize_city("Amman", level=0) == "Amman"
    assert generalize_city("Irbid", level=0) == "Irbid"

    # Level 1 (Governorate)
    assert generalize_city("Amman", level=1) == "Capital Governorate"
    assert generalize_city("Zarqa", level=1) == "Zarqa Governorate"
    assert generalize_city("Salt", level=1) == "Balqa Governorate"
    assert generalize_city("Irbid", level=1) == "Irbid Governorate"
    assert generalize_city("Aqaba", level=1) == "Aqaba Governorate"

    # Level 2 (Region)
    assert generalize_city("Amman", level=2) == "Central Region"
    assert generalize_city("Zarqa", level=2) == "Central Region"
    assert generalize_city("Salt", level=2) == "Central Region"
    assert generalize_city("Irbid", level=2) == "Northern Region"
    assert generalize_city("Jerash", level=2) == "Northern Region"
    assert generalize_city("Aqaba", level=2) == "Southern Region"
    assert generalize_city("Karak", level=2) == "Southern Region"

    # Level 3 (National)
    assert generalize_city("Amman", level=3) == "Jordan"
    assert generalize_city("Aqaba", level=3) == "Jordan"

    # Level 4 (Wildcard)
    assert generalize_city("Amman", level=4) == "*"
    assert generalize_city(None, level=1) == "*"


def test_age_generalization_10_year_bins():
    assert generalize_age(23, level=1, bin_size=10) == "[18-24]"
    assert generalize_age(34, level=1, bin_size=10) == "[25-34]"
    assert generalize_age(42, level=1, bin_size=10) == "[35-44]"
    assert generalize_age(51, level=1, bin_size=10) == "[45-54]"
    assert generalize_age(70, level=1, bin_size=10) == "65+"
    assert generalize_age(16, level=1, bin_size=10) == "< 18"


def test_age_generalization_5_year_bins():
    assert generalize_age(26, level=1, bin_size=5) == "[25-29]"
    assert generalize_age(33, level=1, bin_size=5) == "[30-34]"
    assert generalize_age(68, level=1, bin_size=5) == "65+"


def test_age_life_stages():
    assert generalize_age(22, level=2) == "Young Adult [18-29]"
    assert generalize_age(41, level=2) == "Adult [30-54]"
    assert generalize_age(62, level=2) == "Senior [55+]"
    assert generalize_age(None, level=1) == "*"


def test_amount_generalization():
    # Level 1 Financial Tiers
    assert generalize_amount(24.50, level=1) == "[0 - 50] JOD"
    assert generalize_amount(150.00, level=1) == "[50 - 200] JOD"
    assert generalize_amount(750.00, level=1) == "[200 - 1000] JOD"
    assert generalize_amount(2500.00, level=1) == "[1000 - 5000] JOD"
    assert generalize_amount(6000.00, level=1) == "[5000+] JOD"

    # Level 2 Macro Tiers
    assert generalize_amount(80.00, level=2) == "Micro [< 200 JOD]"
    assert generalize_amount(500.00, level=2) == "Commercial [200 - 1000 JOD]"
    assert generalize_amount(1500.00, level=2) == "Wholesale [> 1000 JOD]"


def test_timestamp_truncation():
    ts = "2025-11-14T14:32:10"
    assert generalize_timestamp(ts, level=0) == "2025-11-14T14:32:10"
    assert generalize_timestamp(ts, level=1) == "2025-11-14 14:00"
    assert generalize_timestamp(ts, level=2) == "2025-11-14"
    assert generalize_timestamp(ts, level=3) == "2025-11"
    assert generalize_timestamp(ts, level=4) == "*"


def test_hierarchy_registry():
    df = pd.DataFrame({
        "City": ["Amman", "Irbid", "Aqaba"],
        "Age": [25, 45, 65]
    })
    gen_city = HierarchyRegistry.generalize_series("City", df["City"], level=2)
    assert list(gen_city) == ["Central Region", "Northern Region", "Southern Region"]

    gen_age = HierarchyRegistry.generalize_series("Age", df["Age"], level=1)
    assert list(gen_age) == ["[25-34]", "[45-54]", "65+"]


def test_category_generalization():
    assert generalize_category("Shopping", level=1) == "Retail & Living"
    assert generalize_category("Shopping", level=2) == "Consumer Discretionary"
    assert generalize_category("Shopping", level=3) == "*"
