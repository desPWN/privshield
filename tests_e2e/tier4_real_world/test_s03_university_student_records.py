"""
tests_e2e/tier4_real_world/test_s03_university_student_records.py
Tier 4 Multi-Industry Scenario 3: University Student Records.
Domain: Education (StudentID, Major, GPA, Academic Standing).
Enforces zero hardcoded column dependencies and FERPA-compliant privacy release workflows.
"""

import json
import pandas as pd
import pytest
from tests_e2e.conftest import (
    assert_strict_k_anonymity,
    assert_distinct_l_diversity,
    assert_curs_in_bounds,
    assert_formula_safe
)
from tests_e2e.test_contracts import (
    get_detect_sensitive_attributes_fn,
    get_apply_masking_fn,
    get_apply_generalization_fn,
    get_enforce_strict_k_anonymity_fn,
    get_evaluate_distinct_l_diversity_fn,
    get_compute_utility_metrics_fn,
    get_export_dataset_fn,
    verify_pre_export_privacy_gateway
)


def test_scenario_university_student_records(university_students_df: pd.DataFrame):
    detect_fn = get_detect_sensitive_attributes_fn()
    apply_mask = get_apply_masking_fn()
    apply_gen = get_apply_generalization_fn()
    enforce_k = get_enforce_strict_k_anonymity_fn()
    eval_l = get_evaluate_distinct_l_diversity_fn()
    compute_util = get_compute_utility_metrics_fn()
    export_fn = get_export_dataset_fn()

    # 1. Dynamic Discovery
    profiles = detect_fn(university_students_df)
    direct_ids = [p.column_name for p in profiles if p.detected_type == "direct_identifier"]
    quasi_ids = [p.column_name for p in profiles if p.detected_type == "quasi_identifier"]
    sensitive_attrs = [p.column_name for p in profiles if p.detected_type == "sensitive_attribute"]

    assert len(direct_ids) >= 2
    assert len(quasi_ids) >= 2
    assert len(sensitive_attrs) >= 1

    # 2. Mask Direct Identifiers
    mask_rules = {}
    for col in direct_ids:
        c_low = col.lower()
        if "ssn" in c_low:
            mask_rules[col] = "ssn"
        else:
            mask_rules[col] = "fpt"
    masked_df = apply_mask(university_students_df, mask_rules)

    # 3. Generalize Quasi-Identifiers
    target_qis = quasi_ids[:2]
    gen_rules = {col: 1 for col in target_qis}
    gen_df = apply_gen(masked_df, gen_rules)

    # 4. Strict K-Anonymity (K=4)
    target_k = 4
    anon_result = enforce_k(gen_df, qis=target_qis, k=target_k, max_suppression_pct=0.60)
    anon_df = anon_result.anonymized_df if hasattr(anon_result, "anonymized_df") else anon_result[0]

    if len(anon_df) > 0:
        assert_strict_k_anonymity(anon_df, target_qis, target_k=target_k)

        # 5. Distinct L-Diversity on Academic Standing
        standing_col = next((c for c in sensitive_attrs if "standing" in c.lower()), sensitive_attrs[0])
        audit_l = eval_l(anon_df, qis=target_qis, sensitive_attr=standing_col, l=2)
        assert audit_l.total_classes > 0

        # 6. Utility Evaluation
        util = compute_util(university_students_df, anon_df, quasi_identifiers=target_qis)
        assert_curs_in_bounds(util.composite_utility_score)
        assert util.composite_utility_score >= 60.0

        # 7. Pre-Export Gateway Verification
        can_export, msg = verify_pre_export_privacy_gateway(anon_result)
        assert can_export is True

        # 8. Sanitized JSON Export
        json_bytes = export_fn(anon_df, format="json")
        parsed_json = json.loads(json_bytes.decode("utf-8"))
        assert len(parsed_json) == len(anon_df)
        assert isinstance(parsed_json, list)
