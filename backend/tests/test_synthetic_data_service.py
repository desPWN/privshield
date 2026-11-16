"""
Unit tests for PrivShield Multi-Industry Synthetic Dataset Generator.
Verifies realistic schemas, record counts, distributions, checksum validity,
and zero hardcoded column dependencies across:
1. Hospital Patient Records
2. Bank Transactions
3. University Student Records
4. Corporate Employee Records
5. Customer Database
"""

import re
import pandas as pd
from backend.app.engine.discovery import validate_iban_mod97, validate_luhn
from backend.app.services.synthetic_data_service import (
    generate_bank_transactions_dataset,
    generate_customer_database_dataset,
    generate_employee_records_dataset,
    generate_hospital_dataset,
    generate_industry_dataset,
    generate_university_students_dataset,
)


def test_hospital_patient_dataset():
    df = generate_hospital_dataset(n_rows=200, seed=42)
    assert len(df) == 200
    expected_cols = {
        "PatientID", "PatientName", "MRN", "SSN", "Phone", "Email",
        "StreetAddress", "Age", "Gender", "City", "PostalCode",
        "AdmissionDate", "DiagnosisCode", "DiagnosisDescription",
        "Treatment", "LabResultNumeric", "HospitalCharge", "IsSynthetic"
    }
    assert expected_cols.issubset(set(df.columns))
    assert bool(df["IsSynthetic"].all()) is True
    assert (df["HospitalCharge"] >= 100.0).all()
    # Log-normal right-skew: mean > median
    assert df["HospitalCharge"].mean() > df["HospitalCharge"].median()


def test_bank_transactions_dataset():
    df = generate_bank_transactions_dataset(n_rows=200, seed=42)
    assert len(df) == 200
    expected_cols = {
        "AccountID", "CustomerName", "NationalID", "Email", "Phone",
        "IBAN", "CardNumber", "CustomerAge", "Gender", "BranchCity",
        "PostalCode", "TransactionDate", "TransactionAmount",
        "AccountBalance", "CreditScore", "LoanStatus", "IsSynthetic"
    }
    assert expected_cols.issubset(set(df.columns))
    # Validate Luhn on first 20 cards
    for card in df["CardNumber"].iloc[:20]:
        assert validate_luhn(card) is True
    # Validate IBAN on first 20 IBANs
    for iban in df["IBAN"].iloc[:20]:
        assert validate_iban_mod97(iban) is True


def test_university_students_dataset():
    df = generate_university_students_dataset(n_rows=200, seed=42)
    assert len(df) == 200
    expected_cols = {
        "StudentID", "FullName", "PersonalEmail", "CampusPhone", "HomeAddress",
        "Age", "Gender", "HomeCity", "HomeState", "EnrollmentYear",
        "Major", "CumulativeGPA", "AcademicStanding", "FinancialAidAmount",
        "ScholarshipStatus", "IsSynthetic"
    }
    assert expected_cols.issubset(set(df.columns))
    # GPA range [1.5, 4.0]
    assert (df["CumulativeGPA"] >= 1.50).all()
    assert (df["CumulativeGPA"] <= 4.00).all()


def test_employee_records_dataset():
    df = generate_employee_records_dataset(n_rows=200, seed=42)
    assert len(df) == 200
    expected_cols = {
        "EmployeeID", "FullName", "WorkEmail", "PersonalPhone", "NationalID",
        "ResidentialAddress", "Age", "Gender", "OfficeLocation", "Department",
        "HireYear", "EducationLevel", "BaseSalary", "AnnualBonus",
        "PerformanceRating", "DisciplinaryAction", "IsSynthetic"
    }
    assert expected_cols.issubset(set(df.columns))
    assert (df["BaseSalary"] >= 30000).all()


def test_customer_database():
    df = generate_customer_database_dataset(n_rows=200, seed=42)
    assert len(df) == 200
    expected_cols = {
        "CustomerID", "FullName", "Email", "PhoneNumber", "BillingAddress",
        "IPAddress", "AgeGroup", "Gender", "City", "State", "PostalCode",
        "RegistrationDate", "AnnualIncome", "CreditLimit", "LifetimeValue",
        "ChurnRiskScore", "IsSynthetic"
    }
    assert expected_cols.issubset(set(df.columns))
    # IP address syntax verification
    ipv4_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    for ip in df["IPAddress"].iloc[:20]:
        assert ipv4_pattern.match(ip) is not None


def test_industry_dataset_dispatcher():
    df_h = generate_industry_dataset("healthcare", n_rows=50)
    assert "HospitalCharge" in df_h.columns

    df_b = generate_industry_dataset("finance", n_rows=50)
    assert "CardNumber" in df_b.columns

    df_u = generate_industry_dataset("education", n_rows=50)
    assert "CumulativeGPA" in df_u.columns

    df_e = generate_industry_dataset("hr", n_rows=50)
    assert "BaseSalary" in df_e.columns

    df_c = generate_industry_dataset("ecommerce", n_rows=50)
    assert "IPAddress" in df_c.columns

    df_g = generate_industry_dataset("government", n_rows=50)
    assert "Citizen_Name" in df_g.columns
    assert "Taxable_Income" in df_g.columns


def test_government_dataset():
    df = generate_industry_dataset("government", n_rows=200, seed=42)
    assert len(df) == 200
    expected_cols = {
        "Citizen_Name", "National_ID", "Passport_Number", "Tax_ID", "Residential_Address",
        "Phone", "Age", "Gender", "Municipality", "Postal_Code", "Marital_Status",
        "Household_Size", "Taxable_Income", "Benefit_Amount", "Disability_Status",
        "Property_Assessment", "Pension_Tier", "IsSynthetic"
    }
    assert expected_cols.issubset(set(df.columns))
    assert bool(df["IsSynthetic"].all()) is True
    assert (df["Taxable_Income"] >= 10000).all()
