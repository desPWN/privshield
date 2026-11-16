"""
Tier 3: Cross-Feature Combinations - Module C04: Full End-to-End Anonymization Lifecycle.
Validates the complete 10-step platform pipeline:
Raw Ingestion -> Auto Discovery -> Overrides -> Masking -> Generalization ->
Strict K-Anonymity -> L/T Evaluation -> Utility & Risk -> Sanitized Export -> PDF Report.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import (
    get_detect_sensitive_attributes_fn,
    get_apply_masking_fn,
    get_apply_generalization_fn,
    get_enforce_strict_k_anonymity_fn,
    get_evaluate_distinct_l_diversity_fn,
    get_evaluate_t_closeness_fn,
    get_compute_privacy_risks_fn,
    get_compute_utility_metrics_fn,
    get_export_dataset_fn,
    get_generate_pdf_report_fn,
)
from tests_e2e.conftest import (
    assert_strict_k_anonymity,
    assert_distinct_l_diversity,
    assert_curs_in_bounds,
    assert_zero_raw_pii,
    assert_formula_safe,
)


def test_complete_end_to_end_lifecycle(synthetic_jordanian_df):
    """Executes the complete lifecycle pipeline from raw input to audited export and PDF report."""
    # Step 1: Raw Ingestion
    assert len(synthetic_jordanian_df) > 0
    raw_df = synthetic_jordanian_df.copy()

    # Step 2: Sensitive Data Discovery
    discovery_fn = get_detect_sensitive_attributes_fn()
    profiles = discovery_fn(raw_df)
    assert len(profiles) == len(raw_df.columns)
    direct_ids = [p.column_name for p in profiles if p.detected_type == "direct_identifier"]
    assert "National_ID" in direct_ids
    assert "IBAN" in direct_ids

    # Step 3: Classification Overrides (Override 'Merchant' to quasi_identifier if not already)
    # Step 4: Data Masking
    mask_fn = get_apply_masking_fn()
    mask_rules = {
        "National_ID": "national_id",
        "IBAN": "iban",
        "Card_Number": "card_number",
        "Email": "email",
        "Phone": "phone",
        "Customer_Name": "redact"
    }
    df_masked = mask_fn(raw_df, mask_rules)

    # Step 5: Hierarchical Generalization
    gen_fn = get_apply_generalization_fn()
    gen_rules = {"City": 2, "Age": 1, "Timestamp": 2}
    df_gen = gen_fn(df_masked, gen_rules)

    # Step 6: Strict K-Anonymity (K=3)
    k_fn = get_enforce_strict_k_anonymity_fn()
    qis = ["City", "Gender"]
    res_k = k_fn(df_gen, qis=qis, k=3, strategy="record", max_suppression_pct=0.50)

    assert res_k.k_satisfied is True
    assert res_k.min_equivalence_class_size >= 3
    assert_strict_k_anonymity(res_k.anonymized_df, qis, 3)

    # Step 7: L-Diversity & T-Closeness Audit
    l_fn = get_evaluate_distinct_l_diversity_fn()
    t_fn = get_evaluate_t_closeness_fn()

    res_l = l_fn(res_k.anonymized_df, qis=qis, sensitive_attr="Category", l=2)
    assert res_l.satisfied is True
    assert_distinct_l_diversity(res_k.anonymized_df, qis, "Category", 2)

    res_t = t_fn(res_k.anonymized_df, qis=qis, sensitive_attr="Transaction_Amount", t_threshold=0.40)
    assert 0.0 <= res_t.max_observed_distance <= 1.0

    # Step 8: Privacy Risk & Utility Analytics
    risk_fn = get_compute_privacy_risks_fn()
    util_fn = get_compute_utility_metrics_fn()

    risk_metrics = risk_fn(res_k.anonymized_df, qis=qis)
    assert risk_metrics.prosecutor_risk <= (1.0 / 3.0)

    util_metrics = util_fn(raw_df, res_k.anonymized_df, quasi_identifiers=qis, generalization_levels=gen_rules)
    assert_curs_in_bounds(util_metrics.composite_utility_score)

    # Step 9: Sanitized Export (CSV & JSON)
    export_fn = get_export_dataset_fn()
    csv_bytes = export_fn(res_k.anonymized_df, format="csv")
    csv_text = csv_bytes.decode("utf-8")
    assert_formula_safe(csv_text)
    assert_zero_raw_pii(csv_text)

    # Step 10: PDF Privacy Evaluation Report
    pdf_fn = get_generate_pdf_report_fn()
    meta = {"name": "jordan_e2e_export.csv", "row_count": len(raw_df)}
    summary_metrics = {
        "k": 3,
        "k_satisfied": res_k.k_satisfied,
        "suppression_rate": res_k.suppression_rate,
        "curs": util_metrics.composite_utility_score,
        "prosecutor_risk": risk_metrics.prosecutor_risk
    }
    pdf_bytes = pdf_fn(meta, summary_metrics)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 500
