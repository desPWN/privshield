"""
Tier 5: White-Box Adversarial Hardening & Engine Stress Test Suite.
Empirical challenger tests verifying core mathematical invariants, extreme sparsity,
null-dominant distributions, multimodal/Pareto distributions, large batch execution stability,
and zero false-compliance guarantees for FinGuard.
"""

import io
import math
import random
import time
import uuid
from typing import Any, Dict, List
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.schemas import AnonymizationConfig
from backend.app.engine.k_anonymity import (
    enforce_strict_k_anonymity,
    partition_equivalence_classes,
)
from backend.app.engine.l_diversity import evaluate_distinct_l_diversity
from backend.app.engine.t_closeness import (
    compute_continuous_wasserstein_distance,
    compute_categorical_tvd,
    evaluate_t_closeness,
)
from backend.app.engine.utility import compute_utility_metrics
from backend.app.services.anonymization_service import AnonymizationService


# ==============================================================================
# SUITE 1: Multi-Column K-Anonymity with Extreme Sparsity
# ==============================================================================

class TestMultiColumnSparsityKAnonymity:
    """Stress tests K-anonymity partitioning and suppression under extreme dimensional sparsity."""

    def test_k_anonymity_extreme_sparsity_ten_columns_unique_singletons_record_suppression(self):
        """
        Adversarial scenario: 10 Quasi-Identifiers with 1,000 unique rows (each row is distinct).
        Under record suppression, every class has size 1 < target_k (e.g., k=5).
        Expected behavior: 100% of records are suppressed, 0 records retained, achieved_k=0,
        and vacuously satisfied (no sub-K class exists in output).
        """
        n = 1000
        k = 5
        data = {f"qi_{i}": [str(uuid.uuid4()) for _ in range(n)] for i in range(10)}
        df = pd.DataFrame(data)

        anon_df, metrics = enforce_strict_k_anonymity(
            df=df,
            qi_columns=list(df.columns),
            target_k=k,
            suppression_strategy="record",
        )

        assert len(anon_df) == 0, f"Expected 0 retained records under extreme sparsity, got {len(anon_df)}"
        assert metrics["retained_records"] == 0
        assert metrics["suppressed_records"] == n
        assert metrics["suppression_rate"] == 1.0
        assert metrics["num_equivalence_classes"] == 0
        assert metrics["k_satisfied"] is True
        assert metrics["min_equivalence_class_size"] == 0

    def test_k_anonymity_extreme_sparsity_sparse_with_dense_islands(self):
        """
        Adversarial scenario: 10 QIs across 500 rows, containing:
        - Island 1: 10 identical rows
        - Island 2: 10 identical rows
        - Sea of noise: 480 unique singleton rows
        With target_k=5 and record suppression:
        Must retain exactly the 20 rows from the 2 dense islands and suppress all 480 singletons.
        Every retained class must have size >= 5.
        """
        k = 5
        qi_cols = [f"qi_{i}" for i in range(10)]

        # Island 1: 10 rows
        island_1 = {col: [f"island1_val_{col}"] * 10 for col in qi_cols}
        # Island 2: 10 rows
        island_2 = {col: [f"island2_val_{col}"] * 10 for col in qi_cols}
        # 480 unique singletons
        singletons = {col: [f"sparse_{col}_{j}" for j in range(480)] for col in qi_cols}

        df_1 = pd.DataFrame(island_1)
        df_2 = pd.DataFrame(island_2)
        df_noise = pd.DataFrame(singletons)
        df = pd.concat([df_1, df_2, df_noise], ignore_index=True)

        anon_df, metrics = enforce_strict_k_anonymity(
            df=df,
            qi_columns=qi_cols,
            target_k=k,
            suppression_strategy="record",
        )

        assert len(anon_df) == 20, f"Expected exactly 20 retained records from the 2 islands, got {len(anon_df)}"
        assert metrics["retained_records"] == 20
        assert metrics["suppressed_records"] == 480
        assert metrics["num_equivalence_classes"] == 2

        # Verify every retained equivalence class has size >= k
        ec_map = partition_equivalence_classes(anon_df, qi_cols)
        for ec_tuple, members in ec_map.items():
            assert len(members) >= k, f"Class {ec_tuple} has size {len(members)} < {k}"
        assert metrics["min_equivalence_class_size"] == 10
        assert metrics["k_satisfied"] is True

    def test_k_anonymity_extreme_sparsity_cell_suppression_wildcard_merging(self):
        """
        Adversarial scenario: 5 QIs, 100 rows where 90 are singletons and 10 form a compliant cluster.
        Under cell suppression, the 90 singletons are masked with wildcard '*' across all 5 QIs.
        Because 90 >= target_k (5), the wildcard group forms a compliant equivalence class.
        Expected behavior: 100 retained records across 2 equivalence classes, achieved_k >= 5.
        """
        k = 5
        qi_cols = [f"qi_{i}" for i in range(5)]

        # Compliant cluster of 10 rows
        cluster = {col: [f"cluster_{col}"] * 10 for col in qi_cols}
        # 90 singletons
        singletons = {col: [f"sparse_{col}_{j}" for j in range(90)] for col in qi_cols}

        df = pd.concat([pd.DataFrame(cluster), pd.DataFrame(singletons)], ignore_index=True)

        anon_df, metrics = enforce_strict_k_anonymity(
            df=df,
            qi_columns=qi_cols,
            target_k=k,
            suppression_strategy="cell",
        )

        assert len(anon_df) == 100
        assert metrics["retained_records"] == 100
        assert metrics["suppressed_records"] == 0
        assert metrics["num_equivalence_classes"] == 2

        ec_map = partition_equivalence_classes(anon_df, qi_cols)
        wildcard_key = tuple(["*"] * 5)
        assert wildcard_key in ec_map
        assert len(ec_map[wildcard_key]) == 90
        assert metrics["min_equivalence_class_size"] == 10
        assert metrics["k_satisfied"] is True

    def test_k_anonymity_extreme_sparsity_cell_suppression_insufficient_wildcards_fallback(self):
        """
        Adversarial scenario: Cell suppression with insufficient violators to form a wildcard class.
        10 compliant rows (cluster of 10) + 3 singletons (total 13 rows), target_k = 5.
        The 3 singletons masked with '*' only form a class of size 3 < 5.
        Expected behavior: Cell suppression must fall back to record-suppressing the 3 violators,
        retaining only the 10 compliant records and strictly maintaining min EC size >= 5.
        """
        k = 5
        qi_cols = ["city", "age"]

        cluster = pd.DataFrame({"city": ["Amman"] * 10, "age": [30] * 10})
        violators = pd.DataFrame({"city": ["Zarqa", "Irbid", "Aqaba"], "age": [21, 22, 23]})
        df = pd.concat([cluster, violators], ignore_index=True)

        anon_df, metrics = enforce_strict_k_anonymity(
            df=df,
            qi_columns=qi_cols,
            target_k=k,
            suppression_strategy="cell",
        )

        assert len(anon_df) == 10
        assert metrics["retained_records"] == 10
        assert metrics["suppressed_records"] == 3
        assert metrics["num_equivalence_classes"] == 1
        assert metrics["min_equivalence_class_size"] == 10
        assert metrics["k_satisfied"] is True

    def test_k_anonymity_sparsity_with_mixed_nulls_and_unicode_tokens(self):
        """
        Adversarial scenario: 4 QIs containing None, NaN, Arabic tokens, English strings, and integers.
        Verifies string serialization in equivalence class tuples handles mixed types and nulls without failure.
        """
        k = 3
        qi_cols = ["city", "age", "status", "arabic_desc"]

        df = pd.DataFrame({
            "city": ["عمان", "عمان", "عمان", None, None, None, np.nan, np.nan, np.nan],
            "age": [25, 25, 25, 40, 40, 40, 50, 50, 50],
            "status": ["active", "active", "active", "pending", "pending", "pending", None, None, None],
            "arabic_desc": ["معاملة", "معاملة", "معاملة", "تحويل", "تحويل", "تحويل", "بطاقة", "بطاقة", "بطاقة"]
        })

        anon_df, metrics = enforce_strict_k_anonymity(
            df=df,
            qi_columns=qi_cols,
            target_k=k,
            suppression_strategy="record",
        )

        assert len(anon_df) == 9
        assert metrics["retained_records"] == 9
        assert metrics["num_equivalence_classes"] == 3
        assert metrics["min_equivalence_class_size"] == 3
        assert metrics["k_satisfied"] is True


# ==============================================================================
# SUITE 2: Distinct L-Diversity with Empty & Null-Dominant Sensitive Attributes
# ==============================================================================

class TestNullDominantLDiversity:
    """Stress tests L-diversity auditing under 100% null, 90% null, and homogeneity attacks."""

    def test_l_diversity_100_percent_null_sensitive_attribute(self):
        """
        Adversarial scenario: Sensitive attribute is 100% null (NaN / None) across all records.
        All values map to '[NULL]', giving distinct count = 1.
        Under target_l=2, all classes must be flagged as violating, satisfied=False.
        """
        df = pd.DataFrame({
            "city": ["Amman"] * 5 + ["Zarqa"] * 5,
            "sensitive": [np.nan] * 10
        })

        res = evaluate_distinct_l_diversity(
            df=df,
            qi_columns=["city"],
            sensitive_column="sensitive",
            target_l=2,
        )

        assert res.satisfied is False
        assert res.total_classes == 2
        assert res.violating_classes_count == 2
        assert res.violating_records_count == 10
        assert res.min_observed_distinct_values == 1
        for v in res.violation_details:
            assert v.distinct_count == 1
            assert v.values_present == ["[NULL]"]

    def test_l_diversity_90_percent_null_dominant_sensitive_attribute(self):
        """
        Adversarial scenario: Sensitive attribute has 9 nulls and 1 actual category in an equivalence class of size 10.
        Distinct count is 2: ['[NULL]', 'Transfer'].
        Under target_l=3, this class must be flagged as a violation (2 < 3).
        """
        df = pd.DataFrame({
            "city": ["Amman"] * 10,
            "category": [np.nan] * 9 + ["Transfer"]
        })

        res = evaluate_distinct_l_diversity(
            df=df,
            qi_columns=["city"],
            sensitive_column="category",
            target_l=3,
        )

        assert res.satisfied is False
        assert res.total_classes == 1
        assert res.violating_classes_count == 1
        assert res.violating_records_count == 10
        assert res.min_observed_distinct_values == 2
        v = res.violation_details[0]
        assert v.distinct_count == 2
        assert set(v.values_present) == {"[NULL]", "Transfer"}
        assert v.frequency_breakdown["[NULL]"] == 9
        assert v.frequency_breakdown["Transfer"] == 1

    def test_l_diversity_homogeneity_attack_identical_sensitive_values(self):
        """
        Adversarial scenario: Severe homogeneity attack where every class contains identical sensitive values.
        Class 1 (Amman, 5 records): all 'Shopping'
        Class 2 (Zarqa, 5 records): all 'Salary'
        Each class has distinct count = 1.
        Under target_l=2, both classes must violate L-diversity.
        """
        df = pd.DataFrame({
            "city": ["Amman"] * 5 + ["Zarqa"] * 5,
            "category": ["Shopping"] * 5 + ["Salary"] * 5
        })

        res = evaluate_distinct_l_diversity(
            df=df,
            qi_columns=["city"],
            sensitive_column="category",
            target_l=2,
        )

        assert res.satisfied is False
        assert res.total_classes == 2
        assert res.violating_classes_count == 2
        assert res.min_observed_distinct_values == 1

    def test_l_diversity_empty_dataframe_handled_safely(self):
        """
        Adversarial scenario: Passing an empty DataFrame to evaluate_distinct_l_diversity.
        Must return satisfied=True, 0 classes, 0 violating records, without KeyError or ZeroDivisionError.
        """
        df = pd.DataFrame(columns=["city", "sensitive"])

        res = evaluate_distinct_l_diversity(
            df=df,
            qi_columns=["city"],
            sensitive_column="sensitive",
            target_l=2,
        )

        assert res.satisfied is True
        assert res.total_classes == 0
        assert res.violating_classes_count == 0
        assert res.violating_records_count == 0
        assert res.min_observed_distinct_values == 0
        assert res.violation_details == []

    def test_l_diversity_multi_sensitive_attribute_isolation(self):
        """
        Adversarial scenario: Testing multi-attribute evaluation where one attribute is homogeneous
        and fails L-diversity, while the second attribute is diverse and satisfies it.
        """
        df = pd.DataFrame({
            "city": ["Amman"] * 6,
            "category": ["Shopping"] * 6,  # 1 distinct -> fails target_l=2
            "amount_tier": ["T1", "T2", "T3", "T4", "T5", "T6"]  # 6 distinct -> passes target_l=2
        })

        res_cat = evaluate_distinct_l_diversity(df, ["city"], "category", target_l=2)
        res_amt = evaluate_distinct_l_diversity(df, ["city"], "amount_tier", target_l=2)

        assert res_cat.satisfied is False
        assert res_cat.min_observed_distinct_values == 1
        assert res_amt.satisfied is True
        assert res_amt.min_observed_distinct_values == 6


# ==============================================================================
# SUITE 3: T-Closeness with Multimodal, Skewed Pareto & Zero-Variance Distributions
# ==============================================================================

class TestDistributionExtremesTCloseness:
    """Stress tests 1D Wasserstein-1 (EMD) and TVD under hostile distribution topologies."""

    def test_t_closeness_near_zero_variance_constant_continuous_values(self):
        """
        Adversarial scenario: Continuous values with zero variance (spread <= 1e-12).
        For example: all amounts in the dataset are identical (150.00 JOD).
        Must calculate distance = 0.0 without ZeroDivisionError and report satisfied=True.
        """
        df = pd.DataFrame({
            "city": ["Amman"] * 5 + ["Zarqa"] * 5,
            "amount": [150.0] * 10
        })

        res = evaluate_t_closeness(
            df=df,
            qi_columns=["city"],
            sensitive_column="amount",
            target_t=0.10,
        )

        assert res.satisfied is True
        assert res.max_observed_distance == 0.0
        assert res.average_distance == 0.0
        assert res.violating_classes_count == 0

    def test_t_closeness_multimodal_bimodal_distribution_unimodal_class_violates(self):
        """
        Adversarial scenario: Global distribution is sharply bimodal:
        - 500 transactions at 10.0 JOD
        - 500 transactions at 10,000.0 JOD
        Equivalence Class 1 (Amman, 50 rows): all 10.0 JOD (unimodal local distribution).
        Equivalence Class 2 (Zarqa, 50 rows): exactly 25 at 10.0 JOD and 25 at 10,000.0 JOD (balanced).

        Mathematical truth:
        - Class 1 distance to global is exactly 0.50 (violates target_t = 0.20).
        - Class 2 distance to global is exactly 0.00 (satisfies target_t = 0.20).
        """
        g_class1 = [10.0] * 50
        g_class2 = [10.0] * 25 + [10000.0] * 25
        g_other = [10.0] * 425 + [10000.0] * 475

        df = pd.DataFrame({
            "city": ["Amman"] * len(g_class1) + ["Zarqa"] * len(g_class2) + ["Other"] * len(g_other),
            "amount": g_class1 + g_class2 + g_other
        })

        res = evaluate_t_closeness(
            df=df,
            qi_columns=["city"],
            sensitive_column="amount",
            target_t=0.20,
        )

        assert res.satisfied is False
        assert res.total_classes == 3

        # Locate details for Class 1 (Amman) and Class 2 (Zarqa)
        details_by_city = {d.qi_values["city"]: d for d in res.violation_details}
        amman_detail = details_by_city["Amman"]
        zarqa_detail = details_by_city["Zarqa"]

        # Amman unimodal class must have distance ~0.50 and be flagged as a violation
        assert abs(amman_detail.distance - 0.50) < 0.02
        assert amman_detail.is_violation is True

        # Zarqa balanced class must have distance 0.00 and be non-violating
        assert abs(zarqa_detail.distance - 0.00) < 0.01
        assert zarqa_detail.is_violation is False

    def test_t_closeness_highly_skewed_pareto_whale_class_violates(self):
        """
        Adversarial scenario: Highly skewed Pareto power-law distribution (typical of financial wealth/transactions).
        990 records: small transactions (mean ~25 JOD, Pareto a=1.5)
        10 records: extreme whale transactions (> 150,000 JOD, max 2,000,000 JOD)
        Class 'Whales' (10 rows): contains only the 10 whale transactions.
        Class 'Normal' (50 rows): contains normal retail transactions.
        Expected behavior:
        - Class 'Whales' has large Wasserstein distance (> 0.40) and is flagged as a violation.
        - Class 'Normal' has small Wasserstein distance (< 0.10) and is non-violating.
        """
        np.random.seed(42)
        n_small = 990
        small_amts = (np.random.pareto(a=1.5, size=n_small) * 20.0 + 5.0).tolist()
        whale_amts = [150000.0, 200000.0, 350000.0, 500000.0, 750000.0, 1000000.0, 1200000.0, 1500000.0, 1800000.0, 2000000.0]

        df_whales = pd.DataFrame({"group": ["Whales"] * len(whale_amts), "amount": whale_amts})
        df_normal = pd.DataFrame({"group": ["Normal"] * 50, "amount": small_amts[:50]})
        df_rest = pd.DataFrame({"group": ["Rest"] * (n_small - 50), "amount": small_amts[50:]})
        df = pd.concat([df_whales, df_normal, df_rest], ignore_index=True)

        res = evaluate_t_closeness(
            df=df,
            qi_columns=["group"],
            sensitive_column="amount",
            target_t=0.20,
        )

        assert res.satisfied is False
        details = {d.qi_values["group"]: d for d in res.violation_details}

        # Whales class must be flagged as a severe violation
        assert details["Whales"].is_violation is True
        assert details["Whales"].distance > 0.40

        # Normal class represents bulk distribution and must not violate
        assert details["Normal"].is_violation is False
        assert details["Normal"].distance < 0.10

    def test_t_closeness_extreme_numerical_outliers_bounded_interval(self):
        """
        Adversarial scenario: Extreme numerical outliers (1e12 and -1e6) in continuous values.
        Verifies that Wasserstein distance remains strictly within [0.0, 1.0] without numerical overflow.
        """
        df = pd.DataFrame({
            "city": ["Amman"] * 4 + ["Zarqa"] * 4,
            "amount": [-1e6, 0.0, 100.0, 1e12, -1e6, 0.0, 100.0, 1e12]
        })

        res = evaluate_t_closeness(
            df=df,
            qi_columns=["city"],
            sensitive_column="amount",
            target_t=0.20,
        )

        assert res.satisfied is True  # Both classes have identical distributions
        assert 0.0 <= res.max_observed_distance <= 1.0
        assert res.max_observed_distance == 0.0

    def test_t_closeness_extreme_categorical_skew(self):
        """
        Adversarial scenario: Categorical attribute with extreme skew (99.9% 'Bills', 0.1% 'Transfer').
        An equivalence class containing 100% 'Transfer' must have TVD ~0.999, violating T=0.20.
        """
        bills_count = 999
        df_bills = pd.DataFrame({"city": ["Amman"] * bills_count, "category": ["Bills"] * bills_count})
        df_transfer = pd.DataFrame({"city": ["Zarqa"], "category": ["Transfer"]})
        df = pd.concat([df_bills, df_transfer], ignore_index=True)

        res = evaluate_t_closeness(
            df=df,
            qi_columns=["city"],
            sensitive_column="category",
            target_t=0.20,
        )

        assert res.satisfied is False
        details = {d.qi_values["city"]: d for d in res.violation_details}
        assert details["Zarqa"].is_violation is True
        assert details["Zarqa"].distance > 0.90


# ==============================================================================
# SUITE 4: Large Batch Anonymization Runs (Memory & Stability Stress)
# ==============================================================================

class TestLargeBatchStress:
    """Stress tests execution stability, runtime scalability, and memory handling on large batches."""

    def test_large_batch_engine_direct_5k_records(self):
        """
        Stress test: 5,000 records processed directly through K-anonymity, L-diversity, T-closeness,
        and statistical utility evaluation.
        Verifies sub-5 second execution and strict invariant satisfaction.
        """
        np.random.seed(42)
        n = 5000
        cities = ["Amman", "Zarqa", "Irbid", "Aqaba", "Salt", "Madaba"]
        categories = ["Shopping", "Bills & Utilities", "Restaurant", "ATM Withdrawal", "Transfer"]

        df = pd.DataFrame({
            "city": np.random.choice(cities, size=n),
            "age": np.random.randint(18, 75, size=n),
            "amount": np.random.uniform(5.0, 1500.0, size=n),
            "category": np.random.choice(categories, size=n)
        })

        t0 = time.perf_counter()
        anon_df, k_metrics = enforce_strict_k_anonymity(df, ["city", "age"], target_k=5)
        l_res = evaluate_distinct_l_diversity(anon_df, ["city", "age"], "category", target_l=2)
        t_res = evaluate_t_closeness(anon_df, ["city", "age"], "amount", target_t=0.20)
        u_res = compute_utility_metrics(df, anon_df, ["city", "age"])
        total_time = time.perf_counter() - t0

        assert total_time < 5.0, f"Engine pipeline took {total_time:.2f}s, exceeding 5.0s budget"
        assert len(anon_df) > 0
        assert k_metrics["k_satisfied"] is True
        assert k_metrics["min_equivalence_class_size"] >= 5
        assert u_res.composite_utility_score > 0.0

    def test_large_batch_service_pipeline_3k_records_end_to_end(self):
        """
        Stress test: 3,000 records through full AnonymizationService and FastAPI endpoints:
        - Upload dataset via HTTP
        - Execute full anonymization pipeline
        - Verify storage in storage/anonymized/{run_id}.csv
        - Slice paginated diff records
        """
        client = TestClient(app)
        np.random.seed(42)
        n = 3000
        cities = ["Amman", "Zarqa", "Irbid", "Aqaba"]

        df = pd.DataFrame({
            "customer_name": [f"Cust_{i}" for i in range(n)],
            "email": [f"user_{i}@bank.jo" for i in range(n)],
            "city": np.random.choice(cities, size=n),
            "age": np.random.randint(20, 65, size=n),
            "amount": np.random.uniform(10.0, 500.0, size=n),
            "category": np.random.choice(["Shopping", "Transfer", "Bills"], size=n)
        })

        csv_buf = io.BytesIO()
        df.to_csv(csv_buf, index=False)

        # 1. Upload
        upload_res = client.post(
            "/api/datasets/upload",
            files={"file": ("stress_3k.csv", csv_buf.getvalue(), "text/csv")}
        )
        assert upload_res.status_code == 201, upload_res.text
        ds_id = upload_res.json()["dataset_id"]

        # 2. Anonymize
        anon_payload = {
            "quasi_identifiers": ["city", "age"],
            "sensitive_attributes": ["amount", "category"],
            "k_metric": 5,
            "l_metric": 2,
            "t_metric": 0.20,
            "suppression_strategy": "record",
            "max_suppression_pct": 0.50,
            "masking_rules": {"customer_name": "redact", "email": "email"},
            "generalization_levels": {"city": 1, "age": 1}
        }
        anon_res = client.post(f"/api/datasets/{ds_id}/anonymize", json=anon_payload)
        assert anon_res.status_code == 200, anon_res.text
        res_data = anon_res.json()
        run_id = res_data["run_id"]

        assert res_data["k_satisfied"] is True
        assert res_data["min_equivalence_class_size"] >= 5
        assert res_data["retained_records"] > 0

        # 3. Query diff
        diff_res = client.get(f"/api/runs/{run_id}/diff?page=1&size=50")
        assert diff_res.status_code == 200
        diff_data = diff_res.json()
        assert len(diff_data["diff"]) == 50

    def test_large_batch_scalability_10k_records_partitioning(self):
        """
        Stress test: 10,000 records partitioned into equivalence classes.
        Verifies execution speed and linear scaling without memory bottlenecks.
        """
        np.random.seed(42)
        n = 10000
        cities = ["Amman", "Zarqa", "Irbid", "Aqaba", "Salt", "Madaba", "Jerash", "Ajloun"]

        df = pd.DataFrame({
            "city": np.random.choice(cities, size=n),
            "age": np.random.randint(18, 70, size=n),
            "gender": np.random.choice(["M", "F"], size=n)
        })

        t0 = time.perf_counter()
        ec_map = partition_equivalence_classes(df, ["city", "age", "gender"])
        elapsed = time.perf_counter() - t0

        assert elapsed < 2.0, f"10k partitioning took {elapsed:.2f}s, expected < 2.0s"
        assert sum(len(v) for v in ec_map.values()) == n


# ==============================================================================
# SUITE 5: Invariant Verification Matrix (Strict Zero False-Compliance)
# ==============================================================================

class TestStrictKAnonymityInvariantMatrix:
    """
    Exhaustive invariant verification:
    Validates that NO combination of parameters, cluster topologies, corrupt indices,
    or column injections can ever cause a sub-K equivalence class to slip into the output.
    """

    @pytest.mark.parametrize("k", [2, 3, 5, 8, 10])
    @pytest.mark.parametrize("strat", ["record", "cell"])
    def test_invariant_population_smaller_than_k_always_zero_leakage(self, k: int, strat: str):
        """
        Boundary invariant: N = k - 1 records.
        No equivalence class can ever satisfy K.
        Strict invariant mandates 100% suppression and 0 retained records.
        """
        n = k - 1
        df = pd.DataFrame({
            "city": [f"City_{i}" for i in range(n)],
            "age": [20 + i for i in range(n)]
        })

        anon_df, metrics = enforce_strict_k_anonymity(
            df=df,
            qi_columns=["city", "age"],
            target_k=k,
            suppression_strategy=strat,
        )

        assert len(anon_df) == 0, f"Expected 0 retained rows for N={n} < K={k}, got {len(anon_df)}"
        assert metrics["retained_records"] == 0
        assert metrics["suppressed_records"] == n
        assert metrics["suppression_rate"] == 1.0
        assert metrics["num_equivalence_classes"] == 0
        assert metrics["min_equivalence_class_size"] == 0

    def test_invariant_random_fuzzing_matrix_100_configurations(self):
        """
        Fuzzes 100 random parameter combinations across various K, cluster shapes,
        dataset sizes, and suppression strategies.
        Guarantees that min(EC size) >= target_k is strictly maintained in 100% of cases.
        """
        random.seed(1337)
        for iteration in range(100):
            k = random.choice([2, 3, 4, 5, 7, 10])
            strat = random.choice(["record", "cell"])
            n = random.randint(0, 100)
            num_qis = random.randint(1, 4)
            qi_names = [f"qi_{i}" for i in range(num_qis)]

            # Generate hostile mixture of values
            records = []
            for _ in range(n):
                row = {}
                for qi in qi_names:
                    r_val = random.random()
                    if r_val < 0.2:
                        row[qi] = None
                    elif r_val < 0.4:
                        row[qi] = "*"
                    elif r_val < 0.7:
                        row[qi] = random.choice(["Amman", "Zarqa", "Irbid"])
                    else:
                        row[qi] = random.randint(1, 500)
                records.append(row)

            df = pd.DataFrame(records) if records else pd.DataFrame(columns=qi_names)

            anon_df, metrics = enforce_strict_k_anonymity(
                df=df,
                qi_columns=qi_names,
                target_k=k,
                suppression_strategy=strat,
            )

            # Invariant check
            if len(anon_df) > 0:
                ec_map = partition_equivalence_classes(anon_df, qi_names)
                sizes = [len(members) for members in ec_map.values()]
                min_sz = min(sizes)
                assert min_sz >= k, (
                    f"INVARIANT VIOLATION in iteration {iteration}: "
                    f"k={k}, strat={strat}, min_sz={min_sz} < {k}"
                )
                assert metrics["min_equivalence_class_size"] >= k
                assert metrics["k_satisfied"] is True
            else:
                assert metrics["retained_records"] == 0
                assert metrics["num_equivalence_classes"] == 0

    def test_invariant_hostile_dataframe_duplicate_and_corrupt_indices(self):
        """
        Adversarial scenario: DataFrame with duplicated, non-monotonic, and negative indices.
        Verifies that row indexing in K-anonymity does not corrupt row selection or leak records.
        """
        k = 4
        # Hostile duplicated indices: [99, 99, 99, -5, -5, -5, 0, 0]
        data = {
            "city": ["Amman", "Amman", "Amman", "Amman", "Zarqa", "Zarqa", "Zarqa", "Irbid"],
            "age": [30, 30, 30, 30, 45, 45, 45, 60]
        }
        df = pd.DataFrame(data, index=[99, 99, 99, -5, -5, -5, 0, 0])

        anon_df, metrics = enforce_strict_k_anonymity(
            df=df,
            qi_columns=["city", "age"],
            target_k=k,
            suppression_strategy="record",
        )

        # 'Amman', 30 has 4 records -> retained
        # 'Zarqa', 45 has 3 records -> suppressed
        # 'Irbid', 60 has 1 record -> suppressed
        assert len(anon_df) == 4
        assert metrics["retained_records"] == 4
        assert metrics["suppressed_records"] == 4
        assert metrics["min_equivalence_class_size"] == 4
        assert metrics["k_satisfied"] is True

    def test_invariant_hostile_column_names_sql_and_special_chars(self):
        """
        Adversarial scenario: Quasi-identifier column names containing SQL injection tokens,
        whitespace, and punctuation (e.g. `' DROP TABLE; --`, `city/town`, `cust.age`).
        Verifies safe partitioning without syntax errors or injection side-effects.
        """
        k = 3
        hostile_cols = ["' DROP TABLE users; --", "city/town", "cust.age (yrs)"]
        df = pd.DataFrame({
            "' DROP TABLE users; --": ["A", "A", "A", "B", "B"],
            "city/town": ["Amman", "Amman", "Amman", "Zarqa", "Zarqa"],
            "cust.age (yrs)": [25, 25, 25, 30, 30]
        })

        anon_df, metrics = enforce_strict_k_anonymity(
            df=df,
            qi_columns=hostile_cols,
            target_k=k,
            suppression_strategy="record",
        )

        # 'A', 'Amman', 25 has 3 records -> retained
        # 'B', 'Zarqa', 30 has 2 records -> suppressed
        assert len(anon_df) == 3
        assert metrics["retained_records"] == 3
        assert metrics["suppressed_records"] == 2
        assert metrics["min_equivalence_class_size"] == 3
        assert metrics["k_satisfied"] is True
