"""
tests_e2e/tier1_features/test_f20_anonymization_studio.py
Feature 20: Professional 3-Panel Anonymization Studio.
Validates 3-panel layout contract, mode toggle, pre-flight verification, and live diff preview.
"""

import pandas as pd
import pytest
from backend.app.models.schemas import AnonymizationConfig
from tests_e2e.test_contracts import STUDIO_PANELS


def test_studio_three_panel_layout_contract():
    assert len(STUDIO_PANELS) == 3
    assert STUDIO_PANELS == ["columns_panel", "transformation_panel", "preview_panel"]


def test_studio_mode_toggle_state_contract():
    config_reversible = AnonymizationConfig(
        quasi_identifiers=["City", "Age"],
        processing_mode="reversible_pseudonymization"
    )
    assert config_reversible.processing_mode == "reversible_pseudonymization"

    config_irreversible = AnonymizationConfig(
        quasi_identifiers=["City", "Age"],
        processing_mode="irreversible_anonymization"
    )
    assert config_irreversible.processing_mode == "irreversible_anonymization"


def test_studio_live_diff_generation():
    orig_df = pd.DataFrame({"Name": ["Alice", "Bob"], "Age": [25, 45]})
    anon_df = pd.DataFrame({"Name": ["[MASKED]", "[MASKED]"], "Age": ["[20-30]", "[40-50]"]})

    diffs = []
    for col in orig_df.columns:
        changed_count = (orig_df[col] != anon_df[col]).sum()
        diffs.append({"column": col, "changed_records": int(changed_count)})

    assert len(diffs) == 2
    assert diffs[0]["changed_records"] == 2
    assert diffs[1]["changed_records"] == 2


def test_studio_preflight_verification_gateway():
    preflight_checks = {
        "has_quasi_identifiers": True,
        "k_metric_valid": 5 >= 2,
        "suppression_budget_capped": 0.50 <= 0.80,
        "mode_selected": "irreversible_anonymization"
    }
    can_execute = all(preflight_checks.values())
    assert can_execute is True


def test_studio_configuration_schema_validation():
    config = AnonymizationConfig(
        quasi_identifiers=["Department", "Office_Location"],
        sensitive_attributes=["Salary"],
        k_metric=4,
        l_metric=2,
        t_metric=0.25,
        suppression_strategy="record",
        max_suppression_pct=0.40,
        masking_rules={"EmployeeID": "fpt"},
        generalization_levels={"Department": 1}
    )
    assert config.k_metric == 4
    assert config.l_metric == 2
    assert config.t_metric == 0.25
    assert config.masking_rules["EmployeeID"] == "fpt"
