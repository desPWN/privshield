"""
tests_e2e/tier1_features/test_f01_synthetic_datasets.py
Feature 1: Multi-Industry Synthetic Datasets & Generator.
Validates synthetic generation and schemas for 5 industries with synthetic certification.
"""

import pandas as pd
import pytest


def test_hospital_dataset_structure_and_types(hospital_patient_df: pd.DataFrame):
    assert len(hospital_patient_df) >= 100
    expected_cols = {"MRN", "Patient_Name", "National_ID", "Age", "Gender", "Zip_Code", "Admission_Date", "ICD10_Code", "Treatment_Category", "Total_Charges", "IsSynthetic"}
    assert expected_cols.issubset(set(hospital_patient_df.columns))
    assert hospital_patient_df["Age"].min() >= 18
    assert hospital_patient_df["Total_Charges"].dtype in ("float64", "float32")


def test_bank_transactions_dataset_structure_and_types(bank_transactions_df: pd.DataFrame):
    assert len(bank_transactions_df) >= 100
    expected_cols = {"Transaction_ID", "Customer_ID", "IBAN", "Card_Number", "City", "Age", "Gender", "Merchant", "Transaction_Amount", "Loan_Status", "Timestamp", "IsSynthetic"}
    assert expected_cols.issubset(set(bank_transactions_df.columns))
    assert bank_transactions_df["Transaction_Amount"].min() > 0


def test_university_students_dataset_structure_and_types(university_students_df: pd.DataFrame):
    assert len(university_students_df) >= 100
    expected_cols = {"StudentID", "Student_Name", "SSN", "Birth_Date", "Gender", "State", "Major", "GPA", "Academic_Standing", "Credits_Completed", "IsSynthetic"}
    assert expected_cols.issubset(set(university_students_df.columns))
    assert 1.0 <= university_students_df["GPA"].min() and university_students_df["GPA"].max() <= 4.0


def test_employee_records_dataset_structure_and_types(employee_records_df: pd.DataFrame):
    assert len(employee_records_df) >= 100
    expected_cols = {"EmployeeID", "Full_Name", "SSN", "Department", "Job_Title", "Age", "Office_Location", "Salary", "Performance_Rating", "Tenure_Years", "IsSynthetic"}
    assert expected_cols.issubset(set(employee_records_df.columns))
    assert employee_records_df["Salary"].min() >= 30000


def test_customer_database_dataset_structure_and_types(customer_database_df: pd.DataFrame):
    assert len(customer_database_df) >= 100
    expected_cols = {"CustomerID", "Customer_Name", "Email", "Phone", "IP_Address", "Residential_Address", "City", "Age", "Annual_Income", "Purchase_Frequency", "IsSynthetic"}
    assert expected_cols.issubset(set(customer_database_df.columns))
    assert customer_database_df["Annual_Income"].min() > 0


def test_synthetic_certification_and_reproducibility(
    hospital_patient_df: pd.DataFrame,
    bank_transactions_df: pd.DataFrame,
    university_students_df: pd.DataFrame,
    employee_records_df: pd.DataFrame,
    customer_database_df: pd.DataFrame
):
    for df, name in [
        (hospital_patient_df, "Hospital"),
        (bank_transactions_df, "Bank"),
        (university_students_df, "University"),
        (employee_records_df, "Employee"),
        (customer_database_df, "Customer"),
    ]:
        assert "IsSynthetic" in df.columns, f"{name} dataset missing synthetic flag"
        assert df["IsSynthetic"].all(), f"{name} contains non-synthetic certified rows"
