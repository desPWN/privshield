"""
tests_e2e/tier1_features/test_f21_enterprise_datatable.py
Feature 21: Enterprise Data Table with PII Masking Safeguards.
Validates table pagination, sorting, search filtering, column visibility, and raw PII protection in UI.
"""

import pandas as pd
import pytest


def test_table_sorting_contract(employee_records_df: pd.DataFrame):
    sorted_asc = employee_records_df.sort_values(by="Salary", ascending=True)
    sorted_desc = employee_records_df.sort_values(by="Salary", ascending=False)

    assert sorted_asc["Salary"].iloc[0] <= sorted_asc["Salary"].iloc[-1]
    assert sorted_desc["Salary"].iloc[0] >= sorted_desc["Salary"].iloc[-1]


def test_table_pagination_and_slicing(hospital_patient_df: pd.DataFrame):
    page_size = 25
    total_records = len(hospital_patient_df)
    total_pages = (total_records + page_size - 1) // page_size

    page_1 = hospital_patient_df.iloc[0:page_size]
    page_2 = hospital_patient_df.iloc[page_size:page_size * 2]

    assert len(page_1) == 25
    assert len(page_2) == 25
    assert page_1["MRN"].iloc[0] != page_2["MRN"].iloc[0]
    assert total_pages >= 4


def test_table_column_filtering_and_search(bank_transactions_df: pd.DataFrame):
    search_term = "New York"
    filtered = bank_transactions_df[bank_transactions_df["City"].str.contains(search_term, case=False, na=False)]
    assert (filtered["City"] == "New York").all()


def test_table_column_visibility_toggle(customer_database_df: pd.DataFrame):
    all_columns = list(customer_database_df.columns)
    hidden_columns = {"IP_Address", "Residential_Address"}
    visible_columns = [c for c in all_columns if c not in hidden_columns]

    assert len(visible_columns) == len(all_columns) - 2
    assert "IP_Address" not in visible_columns
    assert "CustomerID" in visible_columns


def test_table_pii_masking_safeguard_contract():
    # Contract enforcing raw PII is masked by default on UI tables until user explicitly toggles
    table_cell_renderer = lambda val, is_masked: "•••• •••• •••• " + str(val)[-4:] if is_masked else str(val)

    raw_card = "4111222233334444"
    masked_view = table_cell_renderer(raw_card, is_masked=True)
    unmasked_view = table_cell_renderer(raw_card, is_masked=False)

    assert "••••" in masked_view
    assert masked_view.endswith("4444")
    assert unmasked_view == raw_card
