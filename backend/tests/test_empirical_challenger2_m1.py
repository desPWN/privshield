"""
PrivShield Milestone M1 — Empirical Verification Suite (Challenger 2)
Focus Areas:
1. Universal Sensitive Attribute Detection (`discovery.py`):
   - Adversarial evaluation across noisy, dirty, and perturbed data across Healthcare,
     Finance, Education, HR, Government, and E-commerce.
   - Boundedness of confidence scores in [0.0, 1.0].
   - Strict supersedence of user overrides over automatic classifications.
2. L-Diversity and T-Closeness Mathematical Integrity (`l_diversity.py`, `t_closeness.py`):
   - Extreme distribution skews, identical distributions (T=0), disjoint distributions (T=1),
     zero-variance continuous columns.
   - Mathematical soundness of distances and violation flags.
"""

import math
import random
import numpy as np
import pandas as pd
import pytest

from backend.app.models.schemas import (
    ColumnProfile,
    PiiType,
    SensitivityCategory,
    LDiversityAuditResult,
    TClosenessAuditResult,
)
from backend.app.engine.discovery import (
    discover_column,
    discover_dataset,
    detect_sensitive_attributes,
    calculate_shannon_entropy,
    calculate_uniqueness_ratio,
    score_regex_and_checksum,
    mask_preview_values,
)
from backend.app.engine.l_diversity import (
    evaluate_distinct_l_diversity,
    evaluate_entropy_l_diversity,
    evaluate_recursive_l_diversity,
    evaluate_l_diversity,
)
from backend.app.engine.t_closeness import (
    compute_continuous_wasserstein_distance,
    compute_categorical_tvd,
    evaluate_t_closeness,
)
from backend.app.services.synthetic_data_service import (
    generate_hospital_dataset,
    generate_bank_transactions_dataset,
    generate_university_students_dataset,
    generate_employee_records_dataset,
    generate_customer_database_dataset,
    generate_government_dataset,
)


# ==============================================================================
# Helper to perturb data
# ==============================================================================

def perturb_dataframe(df: pd.DataFrame, seed: int = 12345) -> pd.DataFrame:
    """Injects noise, dirty values, whitespace, mixed types, and casing perturbations."""
    rng = random.Random(seed)
    df_noisy = df.copy()

    # 1. Randomize column name casing (e.g. 'cUsToMeRnAmE', 'pAtIeNt_i_d')
    new_cols = []
    for col in df_noisy.columns:
        c_str = str(col)
        # Randomly toggle case
        chars = [c.upper() if rng.random() > 0.5 else c.lower() for c in c_str]
        new_cols.append("".join(chars))
    df_noisy.columns = new_cols

    n_rows = len(df_noisy)
    for col in df_noisy.columns:
        s = df_noisy[col].copy()

        # If bool or int, convert to object or float to allow NaN injection
        if pd.api.types.is_bool_dtype(s):
            s = s.astype(object)

        # Inject 5% nulls/NaNs
        null_indices = rng.sample(range(n_rows), max(1, int(n_rows * 0.05)))
        s.iloc[null_indices] = np.nan

        # If string/object column, inject whitespace padding, empty strings, and dirty values
        if s.dtype == object or pd.api.types.is_string_dtype(s):
            # Inject leading/trailing whitespace
            ws_indices = rng.sample(range(n_rows), max(1, int(n_rows * 0.05)))
            for idx in ws_indices:
                val = s.iloc[idx]
                if pd.notna(val):
                    s.iloc[idx] = f"   {val}  \t"

            # Inject empty strings
            empty_indices = rng.sample(range(n_rows), max(1, int(n_rows * 0.02)))
            for idx in empty_indices:
                s.iloc[idx] = ""

            # Inject noisy dirty values
            dirty_indices = rng.sample(range(n_rows), max(1, int(n_rows * 0.02)))
            for idx in dirty_indices:
                s.iloc[idx] = rng.choice(["N/A", "UNKNOWN", "NULL", "none", "???", "000000"])

        # If numeric column, inject extreme outliers and non-finite floats
        elif pd.api.types.is_numeric_dtype(s):
            outlier_indices = rng.sample(range(n_rows), max(1, int(n_rows * 0.02)))
            for idx in outlier_indices:
                s.iloc[idx] = rng.choice([0.0, -9999.0, 1e9, 999999.99])

        df_noisy[col] = s

    return df_noisy


# ==============================================================================
# 1. UNIVERSAL SENSITIVE ATTRIBUTE DETECTION ADVERSARIAL TESTS
# ==============================================================================

class TestAdversarialSensitiveDetection:

    @pytest.mark.parametrize("industry, gen_fn", [
        ("Healthcare", generate_hospital_dataset),
        ("Finance", generate_bank_transactions_dataset),
        ("Education", generate_university_students_dataset),
        ("HR", generate_employee_records_dataset),
        ("Customer_Ecommerce", generate_customer_database_dataset),
        ("Government", generate_government_dataset),
    ])
    def test_multi_industry_clean_and_perturbed_confidence_boundedness(self, industry, gen_fn):
        """
        Adversarially evaluate detection across noisy, dirty, and perturbed data across
        Healthcare, Finance, Education, HR, Government, and E-commerce.
        Verify confidence is strictly in [0.0, 1.0] and valid category output.
        """
        # 1. Test clean dataset
        df_clean = gen_fn(n_rows=150, seed=42)
        profiles_clean = discover_dataset(df_clean)
        assert len(profiles_clean) == len(df_clean.columns)

        for prof in profiles_clean:
            assert 0.0 <= prof.confidence <= 1.0, f"Confidence out of bounds: {prof.confidence} for {prof.column_name}"
            assert prof.detected_type in [c.value for c in SensitivityCategory]
            assert isinstance(prof.specific_type, str) and len(prof.specific_type) > 0
            assert isinstance(prof.sample_values_masked, list)
            assert prof.null_count >= 0
            assert prof.unique_count >= 0
            assert prof.is_overridden is False

        # 2. Test perturbed noisy dataset
        df_noisy = perturb_dataframe(df_clean, seed=999)
        profiles_noisy = discover_dataset(df_noisy)
        assert len(profiles_noisy) == len(df_noisy.columns)

        for prof in profiles_noisy:
            assert 0.0 <= prof.confidence <= 1.0, f"Perturbed confidence out of bounds: {prof.confidence} for {prof.column_name}"
            assert prof.detected_type in [c.value for c in SensitivityCategory]
            assert isinstance(prof.sample_values_masked, list)
            assert prof.null_count >= 0
            assert prof.unique_count >= 0

    def test_user_overrides_strictly_supersede_automatic_classifications(self):
        """
        Verify user overrides strictly supersede automatic classifications:
        Confidence must be 1.0, is_overridden True, and user_category properly set.
        """
        df = pd.DataFrame({
            "email": ["user1@domain.com", "user2@domain.com", "user3@domain.com"],
            "salary": [50000.0, 75000.0, 120000.0],
            "record_counter": [1, 2, 3],
            "city": ["Amman", "Zarqa", "Irbid"],
        })

        # Define hostile/counter-intuitive overrides
        overrides = {
            "email": "insensitive",             # Direct ID -> Insensitive
            "record_counter": "direct_identifier",  # Insensitive -> Direct ID
            "salary": "quasi_identifier",       # Sensitive -> Quasi-ID
            "city": "sensitive_attribute",      # Quasi-ID -> Sensitive
        }

        profiles = discover_dataset(df, overrides=overrides)
        profile_map = {p.column_name: p for p in profiles}

        for col, expected_cat in overrides.items():
            prof = profile_map[col]
            assert prof.is_overridden is True, f"Column {col} should be marked overridden"
            assert prof.detected_type == expected_cat, f"Column {col} detected_type {prof.detected_type} != {expected_cat}"
            assert prof.user_category == expected_cat, f"Column {col} user_category {prof.user_category} != {expected_cat}"
            assert prof.confidence == 1.0, f"Column {col} override confidence must be 1.0, got {prof.confidence}"
            assert "User classification override" in prof.explanation

    def test_pathological_and_degenerate_series_inputs(self):
        """
        Test extreme hostile inputs:
        - All-null series
        - All-whitespace series
        - Mixed-type series (ints, floats, dicts, booleans, strings)
        - Extreme floating point values (inf, -inf)
        - Empty dataframe
        """
        # All null
        s_null = pd.Series([None, np.nan, None, np.nan], name="mystery_col")
        p_null = discover_column("mystery_col", s_null)
        assert 0.0 <= p_null.confidence <= 1.0
        assert p_null.detected_type == "insensitive"

        # All whitespace
        s_ws = pd.Series(["   ", "\t\t", " \n "], name="whitespace_col")
        p_ws = discover_column("whitespace_col", s_ws)
        assert 0.0 <= p_ws.confidence <= 1.0

        # Mixed types
        s_mixed = pd.Series([123, "text", 45.67, True, None, "user@test.com"], name="mixed_col")
        p_mixed = discover_column("mixed_col", s_mixed)
        assert 0.0 <= p_mixed.confidence <= 1.0

        # Infinite numbers
        s_inf = pd.Series([np.inf, -np.inf, 1e20, -1e20, np.nan], name="inf_col")
        p_inf = discover_column("inf_col", s_inf)
        assert 0.0 <= p_inf.confidence <= 1.0

        # Empty DataFrame
        df_empty = pd.DataFrame(columns=["empty_col_a", "empty_col_b"])
        p_empty = discover_dataset(df_empty)
        assert len(p_empty) == 2
        for p in p_empty:
            assert 0.0 <= p.confidence <= 1.0


# ==============================================================================
# 2. L-DIVERSITY MATHEMATICAL INTEGRITY TESTS
# ==============================================================================

class TestLDiversityMathematicalIntegrity:

    def test_extreme_distribution_skew_distinct_vs_entropy_vs_recursive(self):
        """
        Adversarial test on severe distribution skew:
        Equivalence class with 10,000 instances of 'Common_Condition' and 1 instance of 'Rare_Condition'.
        - Distinct L-diversity (L=2) passes (2 distinct values).
        - Entropy L-diversity (L=2) MUST FAIL because entropy is ~0.0015 bits, far below log2(2) = 1.0 bit.
        - Recursive (c=2, l=2) MUST FAIL because r1 (10000) >= 2 * r2 (2 * 1 = 2).
        """
        qi_col = ["zip_code", "age"]
        sens_col = "diagnosis"

        rows = []
        # 10000 records of Common_Condition
        for _ in range(10000):
            rows.append({"zip_code": "11100", "age": 30, "diagnosis": "Common_Condition"})
        # 1 record of Rare_Condition
        rows.append({"zip_code": "11100", "age": 30, "diagnosis": "Rare_Condition"})

        df_skew = pd.DataFrame(rows)

        # 1. Distinct L-diversity (L=2) should be satisfied (2 unique values)
        res_distinct_2 = evaluate_distinct_l_diversity(df_skew, qi_col, sens_col, target_l=2)
        assert res_distinct_2.satisfied is True
        assert res_distinct_2.violating_classes_count == 0
        assert res_distinct_2.min_observed_distinct_values == 2

        # Distinct L-diversity (L=3) must fail
        res_distinct_3 = evaluate_distinct_l_diversity(df_skew, qi_col, sens_col, target_l=3)
        assert res_distinct_3.satisfied is False
        assert res_distinct_3.violating_classes_count == 1
        assert res_distinct_3.violating_records_count == 10001

        # 2. Entropy L-diversity (L=2) MUST FAIL despite distinct count == 2
        # Target entropy = log2(2) = 1.0 bit. Observed entropy is ~0.0015 bits.
        res_entropy = evaluate_entropy_l_diversity(df_skew, qi_col, sens_col, target_l=2)
        assert res_entropy.satisfied is False, "Entropy L-diversity must fail on severe distribution skew"
        assert res_entropy.violating_classes_count == 1
        assert res_entropy.violating_records_count == 10001

        # 3. Recursive L-diversity (c=2.0, l=2) MUST FAIL
        # r1 = 10000, tail_sum = r2 = 1. r1 >= c * tail_sum (10000 >= 2 * 1)
        res_recursive = evaluate_recursive_l_diversity(df_skew, qi_col, sens_col, c=2.0, l=2)
        assert res_recursive.satisfied is False, "Recursive L-diversity must fail on severe distribution skew"
        assert res_recursive.violating_classes_count == 1
        assert res_recursive.violating_records_count == 10001

    def test_perfect_uniform_distribution_satisfaction(self):
        """
        Verify that uniform distribution across L distinct values satisfies
        distinct, entropy, and recursive L-diversity.
        """
        qi_col = ["dept"]
        sens_col = "salary_tier"

        # 4 tiers, 25 records each (N=100)
        rows = []
        for tier in ["Tier_1", "Tier_2", "Tier_3", "Tier_4"]:
            for _ in range(25):
                rows.append({"dept": "Engineering", "salary_tier": tier})

        df_uniform = pd.DataFrame(rows)

        # Distinct L=4: should pass
        res_dist = evaluate_distinct_l_diversity(df_uniform, qi_col, sens_col, target_l=4)
        assert res_dist.satisfied is True
        assert res_dist.violating_classes_count == 0

        # Entropy L=4: entropy = -4 * (0.25 * log2(0.25)) = 2.0 = log2(4). Should pass
        res_ent = evaluate_entropy_l_diversity(df_uniform, qi_col, sens_col, target_l=4)
        assert res_ent.satisfied is True
        assert res_ent.violating_classes_count == 0

        # Recursive (c=2, l=4): r1 = 25, tail sum from index 4 is r4 = 25. 25 < 2 * 25 (25 < 50). Should pass
        res_rec = evaluate_recursive_l_diversity(df_uniform, qi_col, sens_col, c=2.0, l=4)
        assert res_rec.satisfied is True
        assert res_rec.violating_classes_count == 0

    def test_complete_homogeneity_attack_all_classes_violate(self):
        """
        Homogeneity attack: 5 equivalence classes where each class has 10 identical values.
        Every class has distinct count = 1.
        For target L=2, 100% of classes must violate.
        """
        rows = []
        for ec_idx in range(5):
            for _ in range(10):
                rows.append({
                    "region": f"Region_{ec_idx}",
                    "disease": f"Disease_{ec_idx}"  # single disease per region
                })
        df_homo = pd.DataFrame(rows)

        res = evaluate_distinct_l_diversity(df_homo, ["region"], "disease", target_l=2)
        assert res.satisfied is False
        assert res.total_classes == 5
        assert res.violating_classes_count == 5
        assert res.violating_records_count == 50
        assert res.min_observed_distinct_values == 1

        # Check violation details structure
        assert len(res.violation_details) == 5
        for v in res.violation_details:
            assert v.distinct_count == 1
            assert v.class_size == 10
            assert len(v.values_present) == 1


# ==============================================================================
# 3. T-CLOSENESS MATHEMATICAL INTEGRITY TESTS
# ==============================================================================

class TestTClosenessMathematicalIntegrity:

    def test_continuous_wasserstein_identical_distribution_t_zero(self):
        """
        Test identical continuous distribution: T distance must be 0.0.
        With target_t = 0.0, satisfied must be True and 0 violations.
        """
        # Equivalence classes have identical sub-samples
        base_vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        rows = []
        for ec in ["EC_1", "EC_2", "EC_3", "EC_4"]:
            for v in base_vals:
                rows.append({"group": ec, "score": v})

        df_ident = pd.DataFrame(rows)

        # Global values and class values are identical
        res = evaluate_t_closeness(df_ident, ["group"], "score", target_t=0.0)
        assert res.satisfied is True, f"Identical distributions must satisfy T=0.0, got {res.max_observed_distance}"
        assert res.violating_classes_count == 0
        assert res.max_observed_distance == 0.0
        assert res.average_distance == 0.0

    def test_categorical_tvd_identical_distribution_t_zero(self):
        """
        Test identical categorical distribution: TVD must be 0.0.
        With target_t = 0.0, satisfied must be True and 0 violations.
        """
        cats = ["Cat_A", "Cat_B", "Cat_C"]
        rows = []
        for ec in ["Group_1", "Group_2", "Group_3"]:
            for c in cats:
                rows.append({"group": ec, "category": c})

        df_ident = pd.DataFrame(rows)

        res = evaluate_t_closeness(df_ident, ["group"], "category", target_t=0.0)
        assert res.satisfied is True
        assert res.violating_classes_count == 0
        assert res.max_observed_distance == 0.0

    def test_categorical_tvd_completely_disjoint_distributions_t_one(self):
        """
        Test completely disjoint distributions: TVD between two disjoint sets must be 1.0.
        """
        class_vals = ["Cancer"] * 50
        global_disjoint = ["Flu"] * 50
        tvd = compute_categorical_tvd(class_vals, global_disjoint)
        assert tvd == 1.0, f"Disjoint TVD must be 1.0, got {tvd}"

    def test_continuous_wasserstein_zero_variance_constant_column(self):
        """
        Test zero-variance continuous column (all global and class values equal, e.g. 500.0):
        val_range == 0, distance must be 0.0, zero divisions by zero, satisfied True.
        """
        rows = []
        for ec in ["EC_A", "EC_B"]:
            for _ in range(20):
                rows.append({"group": ec, "flat_fee": 500.0})

        df_flat = pd.DataFrame(rows)

        # Direct function check
        d_raw = compute_continuous_wasserstein_distance([500.0]*10, [500.0]*40)
        assert d_raw == 0.0

        # Full evaluator check
        res = evaluate_t_closeness(df_flat, ["group"], "flat_fee", target_t=0.05)
        assert res.satisfied is True
        assert res.max_observed_distance == 0.0
        assert res.violating_classes_count == 0

    def test_monotonicity_of_violations_with_respect_to_threshold_t(self):
        """
        Mathematical invariant: as threshold T increases, the number of violating
        classes must be non-increasing (monotonic):
        violations(T1) >= violations(T2) for T1 <= T2.
        """
        # Create dataset with varying degrees of skew
        rows = []
        # Class 1: moderately shifted
        for v in [10.0, 15.0, 20.0, 25.0]:
            rows.append({"group": "EC_1", "val": v})
        # Class 2: severely shifted
        for v in [80.0, 85.0, 90.0, 95.0]:
            rows.append({"group": "EC_2", "val": v})
        # Class 3: balanced
        for v in [10.0, 30.0, 50.0, 70.0, 90.0]:
            rows.append({"group": "EC_3", "val": v})

        df_skew = pd.DataFrame(rows)

        thresholds = [0.01, 0.05, 0.10, 0.20, 0.35, 0.50, 0.80, 1.00]
        prev_viol_count = float("inf")

        for t in thresholds:
            res = evaluate_t_closeness(df_skew, ["group"], "val", target_t=t)
            assert res.violating_classes_count <= prev_viol_count, (
                f"Violation count increased from {prev_viol_count} to {res.violating_classes_count} "
                f"when threshold increased to {t}"
            )
            prev_viol_count = res.violating_classes_count

        # At T=1.00, since max distance <= 1.0, violations must be 0
    def test_continuous_wasserstein_negative_values_and_separation(self):
        """
        Test continuous Wasserstein distance with negative values (e.g., negative balance / debt)
        and separated ranges.
        Global values: [-100.0, -90.0, -80.0, ..., 0.0]
        Class 1: [-100.0, -90.0]
        Class 2: [-10.0, 0.0]
        """
        global_vals = list(np.linspace(-100.0, 0.0, 51))
        class_1 = [-100.0, -90.0]
        class_2 = [-10.0, 0.0]

        d1 = compute_continuous_wasserstein_distance(class_1, global_vals)
        d2 = compute_continuous_wasserstein_distance(class_2, global_vals)

        assert 0.0 <= d1 <= 1.0
        assert 0.0 <= d2 <= 1.0
        assert d1 > 0.35  # Significantly shifted towards negative extreme
        assert d2 > 0.35  # Significantly shifted towards positive extreme

    def test_continuous_wasserstein_approaching_one_extreme_separation(self):
        """
        Verify that continuous Wasserstein distance approaches 1.0 when the class
        is concentrated at the extreme opposite of a concentrated global distribution.
        Global: 999 points at 0.0, 1 point at 1000.0
        Class: 50 points at 1000.0
        Distance should be >= 0.95 (approaching 1.0).
        """
        global_vals = [0.0] * 999 + [1000.0]
        class_vals = [1000.0] * 50

        emd = compute_continuous_wasserstein_distance(class_vals, global_vals)
        assert emd >= 0.95, f"Expected EMD near 1.0, got {emd}"
        assert emd <= 1.0

    def test_nan_handling_in_continuous_and_categorical_t_closeness(self):
        """
        Ensure that NaNs in the sensitive column do not crash T-closeness evaluation.
        """
        df_nan = pd.DataFrame({
            "qi": ["A", "A", "B", "B", "B"],
            "num_sens": [10.0, np.nan, 20.0, np.nan, 30.0],
            "cat_sens": ["Cancer", None, "Flu", np.nan, "Cold"]
        })

        # Numeric T-closeness with NaNs
        res_num = evaluate_t_closeness(df_nan, ["qi"], "num_sens", target_t=0.50, force_numeric=True)
        assert res_num.total_classes == 2
        assert 0.0 <= res_num.max_observed_distance <= 1.0

        # Categorical T-closeness with NaNs
        res_cat = evaluate_t_closeness(df_nan, ["qi"], "cat_sens", target_t=0.50, force_numeric=False)
        assert res_cat.total_classes == 2
        assert 0.0 <= res_cat.max_observed_distance <= 1.0

    def test_multi_dimensional_quasi_identifiers_evaluation(self):
        """
        Verify that multi-dimensional QIs (3+ columns) correctly partition
        and evaluate in both L-diversity and T-closeness.
        """
        df_multi = pd.DataFrame({
            "age": [20, 20, 20, 40, 40, 40],
            "gender": ["M", "M", "M", "F", "F", "F"],
            "city": ["Amman", "Amman", "Amman", "Zarqa", "Zarqa", "Zarqa"],
            "dept": ["Eng", "Eng", "Eng", "HR", "HR", "HR"],
            "salary": [50000.0, 52000.0, 54000.0, 70000.0, 72000.0, 75000.0],
            "condition": ["Flu", "Cold", "Allergy", "Diabetes", "Diabetes", "Hypertension"]
        })

        qi_cols = ["age", "gender", "city", "dept"]

        # L-diversity check
        res_l = evaluate_distinct_l_diversity(df_multi, qi_cols, "condition", target_l=3)
        assert res_l.total_classes == 2
        # Class 1: Flu, Cold, Allergy (3 distinct) -> pass
        # Class 2: Diabetes, Diabetes, Hypertension (2 distinct) -> fails for target_l=3
        assert res_l.satisfied is False
        assert res_l.violating_classes_count == 1
        assert res_l.violating_records_count == 3

        # T-closeness check
        res_t = evaluate_t_closeness(df_multi, qi_cols, "salary", target_t=0.20)
        assert res_t.total_classes == 2
        assert 0.0 <= res_t.max_observed_distance <= 1.0


if __name__ == "__main__":
    pytest.main(["-v", __file__])

