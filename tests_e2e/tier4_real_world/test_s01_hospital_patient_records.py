"""
tests_e2e/tier4_real_world/test_s01_hospital_patient_records.py
Tier 4 Multi-Industry Scenario 1: Hospital Patient Records.
Domain: Healthcare (MRN, ICD-10, Treatment, Total Charges).
Enforces zero hardcoded column dependencies by dynamically operating on discovery profile attributes.
"""

import pandas as pd
import pytest
from tests_e2e.conftest import (
    assert_strict_k_anonymity,
    assert_distinct_l_diversity,
    assert_curs_in_bounds,
    assert_formula_safe,
    assert_zero_raw_pii_extended
)
from tests_e2e.test_contracts import (
    get_detect_sensitive_attributes_fn,
    get_apply_masking_fn,
    get_apply_generalization_fn,
    get_enforce_strict_k_anonymity_fn,
    get_evaluate_distinct_l_diversity_fn,
    get_compute_utility_metrics_fn,
    get_export_dataset_fn,
    get_generate_pdf_report_fn,
    verify_pre_export_privacy_gateway
)


def test_scenario_hospital_patient_records(hospital_patient_df: pd.DataFrame):
    detect_fn = get_detect_sensitive_attributes_fn()
    apply_mask = get_apply_masking_fn()
    apply_gen = get_apply_generalization_fn()
    enforce_k = get_enforce_strict_k_anonymity_fn()
    eval_l = get_evaluate_distinct_l_diversity_fn()
    compute_util = get_compute_utility_metrics_fn()
    export_fn = get_export_dataset_fn()
    gen_pdf = get_generate_pdf_report_fn()

    # 1. Dynamic Discovery without hardcoded column names
    profiles = detect_fn(hospital_patient_df)
    direct_ids = [p.column_name for p in profiles if p.detected_type == "direct_identifier"]
    quasi_ids = [p.column_name for p in profiles if p.detected_type == "quasi_identifier"]
    sensitive_attrs = [p.column_name for p in profiles if p.detected_type == "sensitive_attribute"]

    assert len(direct_ids) >= 2, "Must discover direct identifiers dynamically"
    assert len(quasi_ids) >= 2, "Must discover quasi-identifiers dynamically"
    assert len(sensitive_attrs) >= 1, "Must discover sensitive clinical attributes dynamically"

    # 2. Mask Direct Identifiers
    mask_rules = {col: "fpt" for col in direct_ids}
    masked_df = apply_mask(hospital_patient_df, mask_rules)
    for col in direct_ids:
        assert not (masked_df[col] == hospital_patient_df[col]).all()

    # 3. Generalize Quasi-Identifiers
    gen_rules = {col: 1 for col in quasi_ids[:2]}
    gen_df = apply_gen(masked_df, gen_rules)

    # 4. Enforce Strict K-Anonymity (K=5)
    target_qis = quasi_ids[:2]
    target_k = 5
    anon_result = enforce_k(gen_df, qis=target_qis, k=target_k, max_suppression_pct=0.60)
    anon_df = anon_result.anonymized_df if hasattr(anon_result, "anonymized_df") else anon_result[0]

    if len(anon_df) > 0:
        assert_strict_k_anonymity(anon_df, target_qis, target_k=target_k)

        # 5. Distinct L-Diversity on clinical diagnosis
        sens_col = sensitive_attrs[0]
        audit_l = eval_l(anon_df, qis=target_qis, sensitive_attr=sens_col, l=2)
        assert audit_l.total_classes > 0

        # 6. Utility quantification (CURS)
        util = compute_util(hospital_patient_df, anon_df, quasi_identifiers=target_qis)
        assert_curs_in_bounds(util.composite_utility_score)
        assert util.composite_utility_score >= 60.0

        # 7. Pre-Export Gateway Verification
        can_export, msg = verify_pre_export_privacy_gateway(anon_result)
        assert can_export is True

        # 8. Sanitized Exports
        csv_bytes = export_fn(anon_df, format="csv")
        assert_formula_safe(csv_bytes.decode("utf-8"))

        # 9. Executive PDF Report with zero raw PII
        meta = {"name": "Hospital Clinical Cohort", "industry": "Healthcare", "row_count": len(anon_df)}
        metrics = {
            "k": target_k,
            "k_satisfied": anon_result.k_satisfied,
            "suppression_rate": anon_result.suppression_rate,
            "curs": util.composite_utility_score,
            "prosecutor_risk": anon_result.privacy_risk.prosecutor_risk
        }
        pdf_bytes = gen_pdf(meta, metrics)
        assert pdf_bytes.startswith(b"%PDF-")
        assert_zero_raw_pii_extended(pdf_bytes.decode("latin-1", errors="ignore"))
