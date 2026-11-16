"""
Empirical Adversarial Challenge Suite 2 for Milestone M1
Tests Discovery, Masking, and Utility analytics engines under hostile inputs,
boundary conditions, corrupted checksums, zero-variance columns, and edge cases.
"""

import math
import numpy as np
import pandas as pd
import pytest

from backend.app.models.schemas import PiiType, SensitivityCategory
from backend.app.engine.discovery import (
    discover_column,
    calculate_shannon_entropy,
    validate_iban_mod97,
    validate_luhn,
    score_regex_and_checksum,
    mask_preview_values,
)
from backend.app.engine.masking import (
    mask_email,
    mask_phone,
    mask_national_id,
    mask_iban,
    mask_card_number,
    mask_full,
    mask_partial,
    mask_hash,
)
from backend.app.engine.utility import (
    compute_utility_metrics,
    compute_ks_fidelity,
    compute_categorical_tvd,
)


# =====================================================================
# 1. DISCOVERY ENGINE ADVERSARIAL ATTACKS
# =====================================================================

class TestDiscoveryAdversarial:

    def test_obfuscated_column_names_with_valid_data(self):
        """
        Test that obfuscated column names (e.g., c_nat_ident, cust_mobile_no,
        x_iban_code) are correctly detected via regex/content heuristics
        even when the column name is non-standard or obfuscated.
        """
        # cust_mobile_no with Jordanian phone numbers
        mobile_series = pd.Series([f"079{1000000 + i}" for i in range(100)])
        prof_mobile = discover_column("cust_mobile_no", mobile_series)
        assert prof_mobile.detected_type in (
            SensitivityCategory.DIRECT_IDENTIFIER.value,
            SensitivityCategory.DIRECT_IDENTIFIER,
        )
        assert prof_mobile.specific_type == PiiType.PHONE_NUMBER.value
        assert prof_mobile.confidence >= 0.70

        # x_iban_code with valid Jordanian IBANs
        valid_ibans = [f"JO94ARAB000000000000{100000 + i:06d}" for i in range(100)]
        iban_series = pd.Series(valid_ibans)
        prof_iban = discover_column("x_iban_code", iban_series)
        assert prof_iban.detected_type in (
            SensitivityCategory.DIRECT_IDENTIFIER.value,
            SensitivityCategory.DIRECT_IDENTIFIER,
        )
        assert prof_iban.specific_type == PiiType.IBAN.value
        assert prof_iban.confidence >= 0.70

        # c_nat_ident with 10-digit Jordanian National IDs
        nat_id_series = pd.Series([f"99{10000000 + i}" for i in range(100)])
        prof_nat = discover_column("c_nat_ident", nat_id_series)
        assert prof_nat.detected_type in (
            SensitivityCategory.DIRECT_IDENTIFIER.value,
            SensitivityCategory.DIRECT_IDENTIFIER,
        )
        assert prof_nat.specific_type == PiiType.NATIONAL_ID.value
        assert prof_nat.confidence >= 0.60

    def test_vulnerability_obfuscated_amount_name_misclassification(self):
        """
        Verify obfuscated amount column names ('tr_amt', 'tx_amt', 'amt'):
        1. 2-decimal amounts are classified as sensitive attributes (amount).
        2. High-precision unrounded floats are NOT misclassified as card_number.
        """
        # Case 1: Standard 2-decimal floats correctly classified as amount
        amt_series_2dec = pd.Series([25.50, 100.25, 45.00, 12.00, 99.99] * 20)
        prof_2dec = discover_column("tr_amt", amt_series_2dec)
        assert prof_2dec.detected_type in (
            SensitivityCategory.SENSITIVE_ATTRIBUTE.value,
            SensitivityCategory.SENSITIVE_ATTRIBUTE,
        )
        assert prof_2dec.specific_type == PiiType.AMOUNT.value
        assert prof_2dec.confidence >= 0.50

        # Case 2: Unrounded floats correctly classified as amount, never as card_number
        np.random.seed(42)
        amt_series_float = pd.Series(np.random.uniform(10.0, 500.0, size=100))
        prof_float = discover_column("tr_amt", amt_series_float)
        assert prof_float.specific_type != PiiType.CARD_NUMBER.value
        assert prof_float.specific_type == PiiType.AMOUNT.value

    def test_corrupted_iban_checksum_rejected_no_false_positive_1_confidence(self):
        """
        Corrupted checksums: Test that invalid Jordanian IBANs fail ISO 7064 Mod 97-10
        and DO NOT receive false-positive 1.0 confidence.
        """
        invalid_ibans = [f"JO00ARAB000000000000{100000 + i:06d}" for i in range(100)]
        for s in invalid_ibans[:10]:
            assert not validate_iban_mod97(s), f"IBAN {s} should fail Mod 97"

        series = pd.Series(invalid_ibans)
        score, expl = score_regex_and_checksum(series, PiiType.IBAN)
        assert score < 1.0, f"Expected score < 1.0 for invalid checksums, got {score}"

        prof = discover_column("opaque_code", series)
        assert prof.confidence < 1.0

    def test_corrupted_credit_card_luhn_rejected_no_false_positive_1_confidence(self):
        """
        Corrupted Luhn: 16-digit numbers with invalid Luhn check digits must fail
        and NOT receive 1.0 confidence.
        """
        invalid_cards = []
        for i in range(100):
            cand = f"400000000000{i:04d}"
            if not validate_luhn(cand):
                invalid_cards.append(cand)

        assert len(invalid_cards) >= 80
        series = pd.Series(invalid_cards)
        score, expl = score_regex_and_checksum(series, PiiType.CARD_NUMBER)
        assert score < 1.0, f"Expected score < 1.0 for Luhn-failing cards, got {score}"

        prof = discover_column("mystery_token", series)
        assert prof.confidence < 1.0

    def test_shannon_entropy_extremes(self):
        """
        Verify Shannon entropy under boundary conditions:
        - 1000 identical values -> 0.0 bits
        - 1000 distinct values -> log2(1000) ~ 9.9658 bits
        - 2 equal classes (500 'A', 500 'B') -> 1.0 bit
        - Empty series / All NaN -> 0.0 bits
        """
        s_const = pd.Series(["CONSTANT_VAL"] * 1000)
        assert calculate_shannon_entropy(s_const) == 0.0

        s_distinct = pd.Series([f"VAL_{i}" for i in range(1024)])
        ent_distinct = calculate_shannon_entropy(s_distinct)
        assert math.isclose(ent_distinct, 10.0, abs_tol=0.01)

        s_binary = pd.Series(["A"] * 500 + ["B"] * 500)
        ent_binary = calculate_shannon_entropy(s_binary)
        assert math.isclose(ent_binary, 1.0, abs_tol=0.001)

        assert calculate_shannon_entropy(pd.Series([])) == 0.0
        assert calculate_shannon_entropy(pd.Series([None, np.nan, None])) == 0.0

    def test_mixed_type_columns_graceful_handling(self):
        """
        Mixed-type columns (int, float, str, None, bool, dict) must not crash
        the discovery engine or preview masking.
        """
        mixed_data = [123, "amman", None, 45.67, True, "zarqa", np.nan, "9981021234"]
        s_mixed = pd.Series(mixed_data)
        prof = discover_column("mixed_col", s_mixed)
        assert prof.null_count == 2
        assert prof.unique_count == 6
        assert isinstance(prof.confidence, float)
        assert len(prof.sample_values_masked) > 0

    def test_all_null_and_all_whitespace_columns(self):
        """
        All-null or all-whitespace columns must produce clean profiles without exceptions.
        """
        s_null = pd.Series([None, np.nan, None, None])
        prof_null = discover_column("empty_col", s_null)
        assert prof_null.null_count == 4
        assert prof_null.unique_count == 0
        assert prof_null.detected_type in (
            SensitivityCategory.INSENSITIVE.value,
            SensitivityCategory.INSENSITIVE,
        )

        s_ws = pd.Series(["   ", "\t", "\n\n", "  \t  "])
        prof_ws = discover_column("ws_col", s_ws)
        assert isinstance(prof_ws.confidence, float)
        assert prof_ws.unique_count <= 4

    def test_preview_masking_short_and_degenerate_names(self):
        """
        Test preview masking for degenerate customer name inputs
        (empty string, single char, single word, whitespace only).
        """
        degenerate_names = pd.Series(["", " ", "A", "Al", "Ali", "Ali Ahmad", "Mohammad Bin Zayed Al Nahyan"])
        masked = mask_preview_values(degenerate_names, "customer_name", n_samples=10)
        assert len(masked) == 7
        for m in masked:
            assert isinstance(m, str)
        assert "A*** A***" in masked[5]


# =====================================================================
# 2. MASKING ENGINE INVARIANTS & VULNERABILITY AUDIT
# =====================================================================

class TestMaskingEngineInvariants:

    def test_trailing_digit_preservation(self):
        """
        Verify trailing digit/character preservation across identifiers:
        - Email: preserves first char, char before @, domain
        - Phone: preserves trailing 3 digits
        - National ID: preserves trailing 4 digits
        - IBAN: preserves trailing 4 digits
        - Card number: preserves trailing 4 digits
        """
        email = "ahmad.khalil@finguard.jo"
        m_email = mask_email(email)
        assert m_email.endswith("@finguard.jo")
        assert m_email.startswith("a")
        assert m_email.split("@")[0].endswith("l")
        assert "*" in m_email

        phone_int = "+962 79 501 9283"
        m_phone_int = mask_phone(phone_int)
        assert m_phone_int.endswith("283")

        phone_local = "0795019283"
        m_phone_local = mask_phone(phone_local)
        assert m_phone_local.endswith("283")
        assert m_phone_local.startswith("079")

        nat_id = "9981021234"
        m_nat = mask_national_id(nat_id)
        assert m_nat.endswith("1234")
        assert m_nat.startswith("99")
        assert m_nat == "99****1234"

        iban = "JO94ARAB00000000000012345678"
        m_iban = mask_iban(iban)
        assert m_iban.startswith("JO94")
        assert m_iban.endswith("5678")
        assert len(m_iban) == len(iban)

        card = "4111222233334444"
        m_card_dots = mask_card_number(card, format_style="dots")
        assert m_card_dots.endswith("4444")
        assert "••••" in m_card_dots

        m_card_bin = mask_card_number(card, format_style="bin")
        assert m_card_bin.endswith("4444")
        assert m_card_bin.startswith("4111")

    def test_vulnerability_mask_email_empty_local_part_indexerror(self):
        """
        Verify mask_email with empty local part (e.g. '@domain.com' or '@')
        is safely handled without IndexError by delegating to full masking.
        """
        assert mask_email("@domain.com") == mask_full("@domain.com")
        assert mask_email("@") == mask_full("@")

    def test_safe_short_inputs_on_non_crashing_maskers(self):
        """
        Verify no crashes on non-email masking functions with degenerate inputs.
        """
        short_inputs = [None, "", " ", "a", "1", "ab", "12", "abc", "123"]

        for val in short_inputs:
            res_p = mask_phone(val)
            assert isinstance(res_p, str)

            res_n = mask_national_id(val)
            assert isinstance(res_n, str)

            res_i = mask_iban(val)
            assert isinstance(res_i, str)

            res_c1 = mask_card_number(val, format_style="dots")
            assert isinstance(res_c1, str)
            res_c2 = mask_card_number(val, format_style="bin")
            assert isinstance(res_c2, str)

            res_f = mask_full(val)
            assert isinstance(res_f, str)

            res_part = mask_partial(val, preserve_prefix=2, preserve_suffix=2)
            assert isinstance(res_part, str)

            res_h = mask_hash(val)
            assert isinstance(res_h, str)


# =====================================================================
# 3. UTILITY ANALYTICS INVARIANTS
# =====================================================================

class TestUtilityAnalyticsInvariants:

    def test_curs_identical_datasets_must_be_100(self):
        """
        CURS score on identical datasets must be exactly or approximately 100.0%.
        """
        np.random.seed(42)
        df = pd.DataFrame({
            "age": np.random.randint(20, 70, size=200),
            "amount": np.random.uniform(10.0, 500.0, size=200),
            "city": np.random.choice(["Amman", "Zarqa", "Irbid", "Aqaba"], size=200),
            "category": np.random.choice(["Shopping", "Bills", "Transfer", "ATM"], size=200),
        })

        metrics = compute_utility_metrics(df, df.copy())
        assert metrics.composite_utility_score >= 99.9, (
            f"CURS for identical datasets must be ~100.0%, got {metrics.composite_utility_score}"
        )
        assert metrics.record_retention == 1.0
        assert metrics.numerical_distribution_fidelity == 1.0
        assert metrics.categorical_distribution_fidelity == 1.0
        assert metrics.correlation_retention == 1.0
        assert metrics.granularity_retention == 1.0
        assert metrics.suppressed_records == 0
        assert metrics.suppression_rate == 0.0

    def test_curs_100_percent_suppressed_dataset_must_be_zero(self):
        """
        CURS score on 100% suppressed dataset (anonymized_df is empty) must be 0.0%.
        """
        df = pd.DataFrame({
            "age": [25, 30, 35],
            "amount": [100.0, 200.0, 300.0],
            "city": ["Amman", "Zarqa", "Irbid"],
        })
        empty_anon = pd.DataFrame(columns=df.columns)

        metrics = compute_utility_metrics(df, empty_anon)
        assert metrics.composite_utility_score == 0.0, (
            f"CURS for 100% suppressed dataset must be 0.0%, got {metrics.composite_utility_score}"
        )
        assert metrics.record_retention == 0.0
        assert metrics.suppression_rate == 1.0
        assert metrics.suppressed_records == 3

    def test_correlation_delta_stability_under_zero_variance_columns(self):
        """
        Test correlation delta stability when one or more numeric columns have zero variance
        (e.g., constant column where standard deviation is zero, resulting in Pearson corr NaN).
        Engine must not throw ZeroDivisionError, NaN corruption, or crash.
        """
        # Case A: Constant column in both original and anonymized
        df_orig = pd.DataFrame({
            "const_col": [10.0] * 50,
            "variable_col": np.random.uniform(1.0, 100.0, size=50),
            "another_var": np.random.uniform(5.0, 50.0, size=50),
        })
        df_anon = df_orig.copy()

        metrics_a = compute_utility_metrics(df_orig, df_anon)
        assert not math.isnan(metrics_a.correlation_retention)
        assert not math.isnan(metrics_a.composite_utility_score)
        assert 0.0 <= metrics_a.composite_utility_score <= 100.0

        # Case B: Anonymized column collapsed to constant (zero variance) while original was variable
        df_orig_b = pd.DataFrame({
            "amount": [10.0, 20.0, 30.0, 40.0, 50.0] * 10,
            "age": [20, 25, 30, 35, 40] * 10,
        })
        df_anon_b = pd.DataFrame({
            "amount": [25.0] * 50,  # collapsed to constant mean
            "age": [30] * 50,       # collapsed to constant mean
        })
        metrics_b = compute_utility_metrics(df_orig_b, df_anon_b)
        assert not math.isnan(metrics_b.correlation_retention)
        assert not math.isnan(metrics_b.composite_utility_score)
        assert 0.0 <= metrics_b.composite_utility_score <= 100.0

    def test_ks_fidelity_degenerate_distributions(self):
        """
        Test Kolmogorov-Smirnov fidelity on constant and identical arrays.
        """
        s_const = pd.Series([5.0] * 100)
        s_ident = pd.Series([5.0] * 100)
        fidelity = compute_ks_fidelity(s_const, s_ident)
        assert fidelity == 1.0

        s_low = pd.Series([1.0] * 50)
        s_high = pd.Series([100.0] * 50)
        fidelity_disjoint = compute_ks_fidelity(s_low, s_high)
        assert fidelity_disjoint == 0.0

    def test_categorical_tvd_disjoint_and_identical(self):
        """
        Test Total Variation Distance on identical vs totally disjoint categories.
        Uses floating point tolerance for floating sum.
        """
        s1 = pd.Series(["Amman", "Zarqa", "Irbid"])
        tvd_ident = compute_categorical_tvd(s1, s1)
        assert tvd_ident == 0.0

        s2 = pd.Series(["Aqaba", "Salt", "Madaba"])
        tvd_disjoint = compute_categorical_tvd(s1, s2)
        assert math.isclose(tvd_disjoint, 1.0, abs_tol=1e-7)
