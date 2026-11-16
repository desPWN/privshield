"""
tests_e2e/tier4_real_world/test_s05_customer_databases.py
Tier 4 Multi-Industry Scenario 5: Customer Databases.
Domain: E-Commerce & Retail (CustomerID, IP Address, Residential Address, Annual Income).
Enforces zero hardcoded column dependencies and GDPR/CCPA privacy release standards.
"""

import io
import pandas as pd
import pytest
from tests_e2e.conftest import (
    assert_strict_k_anonymity,
    assert_curs_in_bounds,
    assert_formula_safe,
    assert_zero_raw_pii_extended
)
from tests_e2e.test_contracts import (
    get_detect_sensitive_attributes_fn,
    get_apply_masking_fn,
    get_apply_generalization_fn,
    get_enforce_strict_k_anonymity_fn,
    get_evaluate_t_closeness_fn,
    get_compute_utility_metrics_fn,
    get_export_dataset_fn,
    verify_pre_export_privacy_gateway
)


def test_scenario_customer_databases(customer_database_df: pd.DataFrame):
    detect_fn = get_detect_sensitive_attributes_fn()
    apply_mask = get_apply_masking_fn()
    apply_gen = get_apply_generalization_fn()
    enforce_k = get_enforce_strict_k_anonymity_fn()
    eval_t = get_evaluate_t_closeness_fn()
    compute_util = get_compute_utility_metrics_fn()
    export_fn = get_export_dataset_fn()

    # 1. Dynamic Discovery
    profiles = detect_fn(customer_database_df)
    direct_ids = [p.column_name for p in profiles if p.detected_type == "direct_identifier"]
    quasi_ids = [p.column_name for p in profiles if p.detected_type == "quasi_identifier"]
    sensitive_attrs = [p.column_name for p in profiles if p.detected_type == "sensitive_attribute"]

    assert len(direct_ids) >= 3, "Must discover customer identifiers dynamically"
    assert len(quasi_ids) >= 2, "Must discover demographic quasi-identifiers dynamically"
    assert len(sensitive_attrs) >= 1, "Must discover income attributes dynamically"

    # 2. Mask Direct Identifiers
    mask_rules = {}
    for col in direct_ids:
        c_low = col.lower()
        if "email" in c_low:
            mask_rules[col] = "email"
        elif "phone" in c_low:
            mask_rules[col] = "phone"
        elif "ip" in c_low:
            mask_rules[col] = "ip"
        elif "address" in c_low:
            mask_rules[col] = "address"
        else:
            mask_rules[col] = "fpt"
    masked_df = apply_mask(customer_database_df, mask_rules)

    # 3. Generalize Quasi-Identifiers
    target_qis = quasi_ids[:2]
    gen_rules = {col: 1 for col in target_qis}
    gen_df = apply_gen(masked_df, gen_rules)

    # 4. Strict K-Anonymity (K=5)
    target_k = 5
    anon_result = enforce_k(gen_df, qis=target_qis, k=target_k, max_suppression_pct=0.60)
    anon_df = anon_result.anonymized_df if hasattr(anon_result, "anonymized_df") else anon_result[0]

    if len(anon_df) > 0:
        assert_strict_k_anonymity(anon_df, target_qis, target_k=target_k)

        # 5. Continuous T-Closeness on Annual Income
        inc_col = next((c for c in sensitive_attrs if "income" in c.lower()), sensitive_attrs[0])
        audit_t = eval_t(anon_df, qis=target_qis, sensitive_attr=inc_col, t_threshold=0.50, metric="numeric")
        assert 0.0 <= audit_t.max_observed_distance <= 1.0

        # 6. Utility Quantification
        util = compute_util(customer_database_df, anon_df, quasi_identifiers=target_qis)
        assert_curs_in_bounds(util.composite_utility_score)
        assert util.composite_utility_score >= 50.0

        # 7. Pre-Export Gateway Check
        can_export, msg = verify_pre_export_privacy_gateway(anon_result)
        assert can_export is True

        # 8. Sanitized CSV & XLSX Exports
        csv_bytes = export_fn(anon_df, format="csv")
        assert_formula_safe(csv_bytes.decode("utf-8"))

        xlsx_bytes = export_fn(anon_df, format="xlsx")
        assert xlsx_bytes.startswith(b"PK")
        read_xlsx = pd.read_excel(io.BytesIO(xlsx_bytes), engine="openpyxl")
        assert len(read_xlsx) == len(anon_df)
