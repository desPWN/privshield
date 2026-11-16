"""
Unit tests for Jordanian Synthetic Financial Dataset Generator.
Verifies structure, fields, checksums (IBAN, Luhn), distributions, and labeling.
"""

from pathlib import Path
import re
import pandas as pd

from backend.app.engine.discovery import validate_iban_mod97, validate_luhn
from backend.scripts.generate_jordan_dataset import generate_dataset


def test_generate_dataset_shape_and_columns():
    df = generate_dataset(num_records=100, seed=123)
    assert len(df) == 100
    expected_columns = [
        "CustomerID", "FullName", "NationalID", "Email", "Phone",
        "IBAN", "CardNumber", "Age", "Gender", "City", "PostalCode",
        "Timestamp", "Merchant", "Channel", "TransactionAmount",
        "AccountBalance", "TransactionCategory", "RiskScore",
        "LoanStatus", "IsSynthetic"
    ]
    assert list(df.columns) == expected_columns
    assert bool(df["IsSynthetic"].all()) is True
    assert df.isna().sum().sum() == 0


def test_jordan_iban_checksum_validity():
    df = generate_dataset(num_records=50, seed=42)
    for iban in df["IBAN"]:
        assert iban.startswith("JO"), f"IBAN {iban} does not start with JO"
        assert len(iban) == 30, f"IBAN {iban} length is {len(iban)}, expected 30"
        assert validate_iban_mod97(iban) is True, f"IBAN {iban} failed ISO 7064 Mod 97-10 check"


def test_card_number_luhn_validity():
    df = generate_dataset(num_records=50, seed=42)
    for card in df["CardNumber"]:
        digits = re.sub(r"\D", "", card)
        assert len(digits) == 16, f"Card {card} has {len(digits)} digits"
        assert validate_luhn(card) is True, f"Card {card} failed Luhn checksum"


def test_national_id_format():
    df = generate_dataset(num_records=50, seed=42)
    for nat_id in df["NationalID"]:
        s = str(nat_id).zfill(10)
        assert len(s) == 10, f"National ID {nat_id} does not have 10 digits"
        assert s.isdigit(), f"National ID {nat_id} is not all digits"


def test_jordanian_cities_and_amounts():
    df = generate_dataset(num_records=100, seed=42)
    valid_cities = {"Amman", "Zarqa", "Irbid", "Aqaba", "Salt", "Madaba", "Jerash", "Mafraq"}
    assert set(df["City"]).issubset(valid_cities)

    # Log-normal transaction amount checks
    assert (df["TransactionAmount"] >= 0.50).all()
    assert (df["TransactionAmount"] <= 5000.00).all()
    # Check that median is lower than mean (characteristic right-skew of log-normal)
    assert df["TransactionAmount"].median() < df["TransactionAmount"].mean()


def test_pregenerated_csv_file_exists():
    csv_path = Path("backend/data/jordan_financial_transactions.csv")
    assert csv_path.exists(), "Benchmark dataset CSV file does not exist"
    df = pd.read_csv(csv_path)
    assert len(df) == 2500, f"Expected 2,500 records, got {len(df)}"
    assert len(df.columns) == 20
    assert bool(df["IsSynthetic"].all()) is True
