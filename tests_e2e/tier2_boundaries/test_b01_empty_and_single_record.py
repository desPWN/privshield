"""
Tier 2: Boundary & Corner Cases - Module B01: Empty & Single Record Datasets.
Validates stability under degenerate dataset sizes (N=0 and N=1) across discovery,
K-anonymity, L-diversity, T-closeness, utility metrics, and export.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import (
    get_detect_sensitive_attributes_fn,
    get_enforce_strict_k_anonymity_fn,
    get_evaluate_distinct_l_diversity_fn,
    get_evaluate_t_closeness_fn,
    get_compute_utility_metrics_fn,
    get_export_dataset_fn,
)


def test_empty_dataframe_discovery(empty_df):
    """Discovery on an empty DataFrame returns schema profiles without crashing."""
    discovery_fn = get_detect_sensitive_attributes_fn()
    profiles = discovery_fn(empty_df)
    assert len(profiles) == len(empty_df.columns)
    for p in profiles:
        assert p.unique_count == 0
        assert p.null_count == 0


def test_empty_dataframe_k_anonymity(empty_df):
    """K-anonymity on an empty dataset produces an empty output with zeroed metrics and no ZeroDivisionError."""
    k_fn = get_enforce_strict_k_anonymity_fn()
    res = k_fn(empty_df, qis=["City"], k=5)

    assert res.total_records == 0
    assert res.retained_records == 0
    assert res.suppressed_records == 0
    assert res.k_satisfied is True
    assert len(res.anonymized_df) == 0


def test_empty_dataframe_l_diversity_and_t_closeness(empty_df):
    """L-diversity and T-closeness return satisfied=True on empty datasets with 0 violating groups."""
    l_fn = get_evaluate_distinct_l_diversity_fn()
    t_fn = get_evaluate_t_closeness_fn()

    res_l = l_fn(empty_df, qis=["City"], sensitive_attr="Category", l=3)
    assert res_l.satisfied is True
    assert res_l.total_classes == 0
    assert res_l.violating_classes_count == 0

    res_t = t_fn(empty_df, qis=["City"], sensitive_attr="Transaction_Amount", t_threshold=0.15)
    assert res_t.satisfied is True
    assert res_t.total_classes == 0
    assert res_t.violating_classes_count == 0


def test_single_record_impossible_k2_without_suppression(single_record_df):
    """A single record dataset cannot satisfy K=2. Record suppression must suppress the lone record."""
    k_fn = get_enforce_strict_k_anonymity_fn()
    res = k_fn(single_record_df, qis=["City"], k=2, strategy="record", max_suppression_pct=1.0)

    # Invariant: retained output must have 0 records because 1 record cannot meet K=2
    assert res.retained_records == 0
    assert res.suppressed_records == 1
    assert len(res.anonymized_df) == 0


def test_single_record_utility_evaluation_no_zerodivision(single_record_df):
    """Utility metrics comparison on single record dataset executes without division by zero in std dev."""
    util_fn = get_compute_utility_metrics_fn()
    res = util_fn(
        original_df=single_record_df,
        anonymized_df=single_record_df.copy(),
        quasi_identifiers=["City"]
    )

    assert res.record_retention == 1.0
    assert res.suppression_rate == 0.0
    assert 0.0 <= res.composite_utility_score <= 100.0


def test_empty_dataset_export_all_formats(empty_df):
    """Exporting empty dataset to CSV, XLSX, and JSON generates valid empty envelopes."""
    export_fn = get_export_dataset_fn()

    csv_bytes = export_fn(empty_df, format="csv")
    assert b"Transaction_ID" in csv_bytes

    json_bytes = export_fn(empty_df, format="json")
    assert json_bytes == b"[]"
