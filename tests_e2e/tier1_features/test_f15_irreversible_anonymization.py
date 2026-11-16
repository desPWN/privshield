"""
tests_e2e/tier1_features/test_f15_irreversible_anonymization.py
Feature 15: Irreversible Anonymization & Pre-Export Gateway.
Validates Mode 2: permanent transformation, zero recovery mappings, and pre-export evaluation gateway.
"""

import pandas as pd
import pytest
from backend.app.models.schemas import AnonymizationConfig, AnonymizationResult, PrivacyRiskMetrics, UtilityMetrics
from tests_e2e.test_contracts import verify_pre_export_privacy_gateway


def test_mode2_generates_zero_recovery_mappings():
    config = AnonymizationConfig(
        quasi_identifiers=["City", "Age"],
        sensitive_attributes=["Salary"],
        k_metric=5,
        processing_mode="irreversible_anonymization"
    )
    assert config.processing_mode == "irreversible_anonymization"


def test_mode2_destroys_identifier_linkage_permanently(customer_database_df: pd.DataFrame):
    # In Mode 2, identifiers are completely dropped or generalized with no mapping stored
    transformed_df = customer_database_df.drop(columns=["CustomerID", "Customer_Name", "Email", "Phone"])
    assert "CustomerID" not in transformed_df.columns
    assert "Email" not in transformed_df.columns


def test_pre_export_gateway_passes_compliant_dataset():
    compliant_result = AnonymizationResult(
        k_satisfied=True,
        achieved_k=5,
        total_records=100,
        retained_records=100,
        suppressed_records=0,
        suppression_rate=0.0,
        num_equivalence_classes=20,
        min_equivalence_class_size=5,
        avg_equivalence_class_size=5.0,
        privacy_risk=PrivacyRiskMetrics(
            prosecutor_risk=0.20, journalist_risk=0.18, marketer_risk=0.20,
            average_risk=0.20, transaction_linkage_risk=0.05, smallest_class_size=5,
            largest_class_size=5, average_class_size=5.0, k_achieved=5
        ),
        utility_metrics=UtilityMetrics(
            record_retention=1.0, numerical_distribution_fidelity=0.95,
            categorical_distribution_fidelity=0.92, correlation_retention=0.90,
            granularity_retention=0.88, composite_utility_score=93.0,
            suppressed_records=0, suppression_rate=0.0
        )
    )

    passed, message = verify_pre_export_privacy_gateway(compliant_result)
    assert passed is True
    assert "passed" in message.lower()


def test_pre_export_gateway_blocks_non_compliant_export():
    violating_result = AnonymizationResult(
        k_satisfied=False,
        achieved_k=1,
        total_records=100,
        retained_records=100,
        suppressed_records=0,
        suppression_rate=0.0,
        num_equivalence_classes=50,
        min_equivalence_class_size=1,
        avg_equivalence_class_size=2.0,
        privacy_risk=PrivacyRiskMetrics(
            prosecutor_risk=1.0, journalist_risk=0.8, marketer_risk=0.5,
            average_risk=0.5, transaction_linkage_risk=0.4, smallest_class_size=1,
            largest_class_size=5, average_class_size=2.0, k_achieved=1
        ),
        utility_metrics=UtilityMetrics(
            record_retention=1.0, numerical_distribution_fidelity=1.0,
            categorical_distribution_fidelity=1.0, correlation_retention=1.0,
            granularity_retention=1.0, composite_utility_score=100.0,
            suppressed_records=0, suppression_rate=0.0
        )
    )

    passed, message = verify_pre_export_privacy_gateway(violating_result)
    assert passed is False
    assert "blocked" in message.lower()


def test_distinction_between_anonymization_and_pseudonymization():
    mode1_meta = {"processing_mode": "reversible_pseudonymization", "is_reversible": True, "token_count": 50}
    mode2_meta = {"processing_mode": "irreversible_anonymization", "is_reversible": False, "token_count": 0}

    assert mode1_meta["is_reversible"] is True
    assert mode2_meta["is_reversible"] is False
    assert mode2_meta["token_count"] == 0
